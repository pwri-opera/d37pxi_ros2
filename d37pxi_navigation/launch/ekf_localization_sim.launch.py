import os
import xacro
from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch_ros.actions import Node
from launch.actions import GroupAction, OpaqueFunction, DeclareLaunchArgument
from launch.substitutions import LaunchConfiguration, TextSubstitution
from nav2_common.launch import RewrittenYaml
from launch.conditions import IfCondition
from threading import Event
import tempfile

robot_name = "d37pxi"
use_autostart = True
use_sim_time = True
use_respawn = True
use_namespace = True
robot_name_val = ""

opaque_function_complete_event = Event()

def retrieve_values(context, *args, **kwargs):
    global robot_name_val
    robot_name_val = LaunchConfiguration('robot_name').perform(context)
    opaque_function_complete_event.set()
    return []

def wait_for_opaque_function(context):
    opaque_function_complete_event.wait()
    return []


def rewrite_ekf_params(context, **kwargs):
    global configured_ekf_params
    d37pxi_navigation_dir = get_package_share_directory('d37pxi_navigation')
    d37pxi_ekf_yaml_file = LaunchConfiguration('ekf_yaml_file', default=os.path.join(d37pxi_navigation_dir, 'config', 'd37pxi_ekf.yaml'))
    configured_ekf_params=RewrittenYaml(
        source_file=d37pxi_ekf_yaml_file,
        root_key=robot_name_val,
        param_rewrites={'use_sim_time': str(use_sim_time)},
        convert_types=True
    )


def generate_nodes(context, *args, **kwargs):
    opaque_function_complete_event.wait()

    return [
        Node(
            package='tf2_ros',
            executable='static_transform_publisher',
            namespace=robot_name_val,
            name='world_to_map',
            arguments=['--x', '0', 
                        '--y', '0', 
                        '--z', '0', 
                        '--roll', '0', 
                        '--pitch', '0', 
                        '--yaw', '0', 
                        '--frame-id', 'world',
                        '--child-frame-id', 'map']),

        
        #########################
        # Localization packages #
        #########################

        Node(
            package='robot_localization',
            executable='ekf_node',
            namespace=robot_name_val,
            name="ekf_global",
            output="screen",
            parameters=[configured_ekf_params,
                        {'map_frame': "map",
                            'world_frame': "map",
                            'odom_frame': [robot_name_val, TextSubstitution(text='/odom')],
                            'base_link_frame': [robot_name_val, TextSubstitution(text='/base_link')],
                            'use_sim_time': use_sim_time,
                            'odom0': 'fixed_odom_pose',
                            'odom1': 'fixed_global_pose'}]),

        Node(
            package='d37pxi_navigation',
            executable='odom_broadcaster',
            namespace=robot_name_val,
            output='screen',
            parameters=[{'odom_topic': "fixed_odom_pose",
                            'odom_frame': [robot_name_val, TextSubstitution(text='/odom')],
                            'base_link_frame': [robot_name_val, TextSubstitution(text='/base_link')],
                            'use_sim_time': use_sim_time}]
        ),
        
        Node(
            package = 'd37pxi_navigation',
            executable = 'message_converter_odom',
            namespace=robot_name_val,
            name = "message_converter_odom",
            output = "screen",
            parameters=[{'input_topic': "odom_pose",
                         'output_topic': 'fixed_odom_pose'}],
        ),
        Node(
            package = 'd37pxi_navigation',
            executable = 'message_converter_gnss',
            namespace=robot_name_val,
            name = "message_converter_gnss",
            output = "screen",
            parameters=[{'input_topic': 'global_pose',
                         'output_topic': 'fixed_global_pose'}],
        ),
        
    ]


def generate_launch_description():
    robot_name_arg = DeclareLaunchArgument('robot_name',default_value='d37pxi')

    return LaunchDescription([
        robot_name_arg,
        OpaqueFunction(function=retrieve_values),
        OpaqueFunction(function=wait_for_opaque_function),
        OpaqueFunction(function=rewrite_ekf_params),
        # OpaqueFunction(function=process_xacro),
        GroupAction([
            OpaqueFunction(function=generate_nodes),
        ])
    ])
