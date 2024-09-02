import os
import tempfile
import xacro
from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.conditions import IfCondition, UnlessCondition
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node
from threading import Event
from ament_index_python.packages import get_package_share_directory
from ament_index_python.packages import get_package_share_path

common_prefix_val = ""
tf_prefix_val = ""
opaque_function_complete_event = Event()

def retrieve_values(context, *args, **kwargs):
    global common_prefix_val, tf_prefix_val
    common_prefix_val = LaunchConfiguration('common_prefix').perform(context)
    tf_prefix_val = common_prefix_val + '_tf'
    # print(f'common_prefix: {common_prefix_val}')
    # print(f'tf_prefix: {tf_prefix_val}')
    opaque_function_complete_event.set()
    return []

def wait_for_opaque_function(context):
    opaque_function_complete_event.wait()
    return []

def process_xacro(context, *args, **kwargs):
    global params
    d37pxi_description_dir = get_package_share_directory("d37pxi_description")
    d37pxi_xacro_file = os.path.join(d37pxi_description_dir, "urdf", "d37pxi24.xacro")
    with open(d37pxi_xacro_file, 'r') as file:
        filedata = file.read()
    filedata = filedata.replace('<xacro:property name="tf_prefix" value=""/>', f'<xacro:property name="tf_prefix" value="{tf_prefix_val}"/>')
    with tempfile.NamedTemporaryFile('w+', delete=False) as temp_file:
        temp_file.write(filedata)
        temp_file_path = temp_file.name
    doc = xacro.parse(open(temp_file_path))
    xacro.process_doc(doc)
    params = {'robot_description': doc.toxml()}
    return []


def generate_launch_description():
    rviz_config = os.path.join(
        get_package_share_directory(
            "d37pxi_description"), "rviz2", "urdf.rviz")

    xacro_model = os.path.join(get_package_share_directory("d37pxi_description"), "urdf", "d37pxi24.xacro")

    doc = xacro.parse(open(xacro_model))
    xacro.process_doc(doc)
    params = {'robot_description': doc.toxml()}

    return LaunchDescription([

        DeclareLaunchArgument('gui',  default_value="true",),
        Node(
            package='tf2_ros',
            executable='static_transform_publisher',
            arguments=['0', '0', '0', '0', '0', '0', 'map', f'{tf_prefix_val}/base_link']
        ),
        Node(
            package='joint_state_publisher_gui',
            executable='joint_state_publisher_gui',
            name='joint_state_publisher_gui',
            condition=IfCondition(LaunchConfiguration('gui')),
        ),
        Node(
            package='joint_state_publisher',
            executable='joint_state_publisher',
            name='joint_state_publisher',
            condition=UnlessCondition(LaunchConfiguration('gui')),
        ),
        Node(
            package='robot_state_publisher',
            executable='robot_state_publisher',
            name='robot_state_publisher',
            parameters=[params]
        ),
        Node(
            package="rviz2",
            executable="rviz2",
            name="rviz",
            arguments=["--display-config", rviz_config],
        ),
    ])
