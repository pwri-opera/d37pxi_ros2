import os
import xacro
import launch
from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch_ros.actions import Node, PushRosNamespace
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

def rewrite_nav_params(context, **kwargs):
    global configured_params
    d37pxi_navigation_dir = get_package_share_directory('d37pxi_navigation')
    navigation_parameters_sim_yaml_file = os.path.join(d37pxi_navigation_dir, 'params', 'navigation_parameters_sim.yaml')
    map_yaml_file = LaunchConfiguration('map', default=os.path.join(d37pxi_navigation_dir, 'map', 'map.yaml'))

    param_substitutions_nav = {
        'use_sim_time': str(use_sim_time),
        'yaml_filename': map_yaml_file,
        'robot_base_frame': robot_name_val + '/base_link',

        # amcl
        'amcl.ros__parameters.base_frame_id': robot_name_val+'/base_link',
        'amcl.ros__parameters.odom_frame_id': robot_name_val+'/odom',

        #component_container_isolated
        'component_container\isolated.ros__parameters.autostart': str(use_autostart),
        
        # bt_navigator
        'bt_navigator.ros__parameters.robot_base_frame': robot_name_val+'/base_link',
        'bt_navigator.ros__parameters.odom_topic': '/'+robot_name_val+'/fixed_odom_pose',
        'bt_navigator.ros__parameters.default_nav_through_poses_bt_xml': os.path.join(d37pxi_navigation_dir, 'params', 'd37pxi_navigate_through_poses_w_replanning_and_recovery.xml'),

        # controller_server
        'controller_server.ros__parameters.odom_topic': '/'+robot_name_val+'/fixed_odom_pose',
        'controller_server.ros__parameters.base_global_frame': robot_name_val+'/odom',

        # local costmap
        'local_costmap.local_costmap.ros__parameters.global_frame': robot_name_val+'/odom',
        'local_costmap.local_costmap.ros__parameters.robot_base_frame': robot_name_val+'/base_link',

        # global costmap                        
        'global_costmap.global_costmap.ros__parameters.robot_base_frame': robot_name_val+'/base_link',

        # behavior server
        'behavior_server.ros__parameters.local_frame': robot_name_val+'/odom',
        'behavior_server.ros__parameters.local_costmap.global_frame': robot_name_val+'/odom',
        'behavior_server.ros__parameters.robot_base_frame': robot_name_val+'/base_link',

        # velocity smoother
        'velocity_smoother.odom_topic': '/'+robot_name_val+'/fixed_odom_pose',
    }
    configured_params=RewrittenYaml(
        source_file=navigation_parameters_sim_yaml_file,
        root_key=robot_name_val,
        param_rewrites=param_substitutions_nav,
        convert_types=True
    )


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

def process_xacro(context, *args, **kwargs):
    global params
    d37pxi_description_dir = get_package_share_directory("d37pxi_description")
    d37pxi_xacro_file = os.path.join(d37pxi_description_dir, "urdf", "d37pxi24.xacro")
    with open(d37pxi_xacro_file, 'r') as file:
        filedata = file.read()
    filedata = filedata.replace('<xacro:property name="tf_prefix" value=""/>', f'<xacro:property name="tf_prefix" value="{robot_name_val}"/>')
    with tempfile.NamedTemporaryFile('w+', delete=False) as temp_file:
        temp_file.write(filedata)
        temp_file_path = temp_file.name
    doc = xacro.parse(open(temp_file_path))
    xacro.process_doc(doc)
    params = {'robot_description': doc.toxml()}
    return []


def generate_nodes(context, *args, **kwargs):
    opaque_function_complete_event.wait()
    d37pxi_unity_dir = get_package_share_directory("d37pxi_unity")
    d37pxi_standby_rviz_file = os.path.join(d37pxi_unity_dir, "rviz2", "d37pxi_standby.rviz")

    lifecycle_nodes_localization = [
        'map_server'
    ]
    lifecycle_nodes_navigation = [
        'controller_server',
        'smoother_server',
        'planner_server',
        'behavior_server',
        'velocity_smoother',
        # 'collision_monitor',
        'bt_navigator',
        'waypoint_follower',
        'velocity_smoother',
    ]    
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
        Node(
            package='robot_state_publisher',
            executable='robot_state_publisher',
            namespace=robot_name_val,
            output="screen",
            parameters=[params, {'use_sim_time': use_sim_time}],
            remappings=[('joint_states', 'joint_state')]
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
        
        #########################
        # Localization packages #
        #########################
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
                            'odom1': 'fixed_global_pose'}]
        ),

        #######################
        # Navigation packages #
        #######################
        Node(
            package='nav2_map_server',
            executable='map_server',
            namespace=robot_name_val,
            name='map_server',
            output='screen',
            respawn=use_respawn,
            respawn_delay=2.0,
            parameters=[configured_params]
        ),
        Node(
            package='nav2_controller',
            executable='controller_server',
            namespace=robot_name_val,
            output='screen',
            respawn=use_respawn,
            respawn_delay=2.0,
            parameters=[configured_params],
            remappings=[('cmd_vel', 'cmd_vel_nav')]
        ),
        Node(
            package='nav2_smoother',
            executable='smoother_server',
            namespace=robot_name_val,
            name='smoother_server',
            output='screen',
            respawn=use_respawn,
            respawn_delay=2.0,
            parameters=[configured_params]
        ),
        Node(
            package='nav2_planner',
            executable='planner_server',
            namespace=robot_name_val,
            name='planner_server',
            output='screen',
            respawn=use_respawn,
            respawn_delay=2.0,
            parameters=[configured_params]
        ),
        Node(
            package='nav2_behaviors',
            executable='behavior_server',
            namespace=robot_name_val,
            name='behavior_server',
            output='screen',
            respawn=use_respawn,
            respawn_delay=2.0,
            parameters=[configured_params],
            remappings=[('cmd_vel', 'tracks/cmd_vel')]
        ),
        Node(
            package='nav2_bt_navigator',
            executable='bt_navigator',
            namespace=robot_name_val,
            name='bt_navigator',
            output='screen',
            respawn=use_respawn,
            respawn_delay=2.0,
            parameters=[configured_params],
            remappings=[(robot_name_val+'/goal_pose', 'goal_pose')]
        ),
        Node(
            package='nav2_waypoint_follower',
            executable='waypoint_follower',
            namespace=robot_name_val,
            name='waypoint_follower',
            output='screen',
            respawn=use_respawn,
            respawn_delay=2.0,
            parameters=[configured_params]
        ),
        Node(
            package='nav2_velocity_smoother',
            executable='velocity_smoother',
            namespace=robot_name_val,
            name='velocity_smoother',
            output='screen',
            respawn=use_respawn,
            respawn_delay=2.0,
            parameters=[configured_params],
            remappings=[('cmd_vel', 'cmd_vel_nav'), 
                        ('cmd_vel_smoothed', 'tracks/cmd_vel')]
        ),
        Node(
            package='nav2_lifecycle_manager',
            executable='lifecycle_manager',
            namespace=robot_name_val,
            name='lifecycle_manager_navigation',
            output='screen',
            parameters=[{'use_sim_time': use_sim_time},
                        {'autostart': use_autostart},
                        {'node_names': lifecycle_nodes_navigation}]
        ),
        Node(
            condition=IfCondition(LaunchConfiguration('use_rviz')),
            package="rviz2",
            executable="rviz2",
            namespace=robot_name_val,
            name="rviz",
            parameters=[{'use_sim_time': use_sim_time}],
            arguments=["--display-config", d37pxi_standby_rviz_file]
        ),
        Node(
            package='nav2_lifecycle_manager',
            executable='lifecycle_manager',
            namespace=robot_name_val,
            name='lifecycle_manager_localization',
            output='screen',
            parameters=[{'use_sim_time': use_sim_time},
                        {'autostart': use_autostart},
                        {'node_names': lifecycle_nodes_localization}]
        ),
        Node(
            condition=IfCondition('true'),
            name='nav2_container',
            package='rclcpp_components',
            executable='component_container_isolated',
            namespace=robot_name_val,
            parameters=[configured_params],
            output='screen'
        ),
        
    ]


def generate_launch_description():
    robot_name_arg = DeclareLaunchArgument('robot_name',default_value='d37pxi')
    use_rviz_arg = DeclareLaunchArgument('use_rviz', default_value='true')

    return LaunchDescription([
        robot_name_arg,
        use_rviz_arg,
        OpaqueFunction(function=retrieve_values),
        OpaqueFunction(function=wait_for_opaque_function),
        OpaqueFunction(function=rewrite_nav_params),
        OpaqueFunction(function=rewrite_ekf_params),
        OpaqueFunction(function=process_xacro),
        GroupAction([
            OpaqueFunction(function=generate_nodes),
        ])
    ])
