import os
import xacro
import launch
from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch_ros.actions import Node, PushRosNamespace
from launch.actions import GroupAction, OpaqueFunction, DeclareLaunchArgument
from launch.substitutions import LaunchConfiguration
from nav2_common.launch import RewrittenYaml
from launch.conditions import IfCondition
from threading import Event
import tempfile

robot_name = "d37pxi"
use_autostart = True
use_sim_time = False
use_respawn = True
use_namespace = True
common_prefix_val = ""
tf_prefix_val = ""

opaque_function_complete_event = Event()

def retrieve_values(context, *args, **kwargs):
    global common_prefix_val, tf_prefix_val
    common_prefix_val = LaunchConfiguration('common_prefix').perform(context)
    tf_prefix_val = common_prefix_val + '_tf'
    opaque_function_complete_event.set()
    return []

def wait_for_opaque_function(context):
    opaque_function_complete_event.wait()
    return []

def rewrite_nav_params(context, **kwargs):
    global configured_params
    d37pxi_navigation_dir = get_package_share_directory('d37pxi_navigation')
    navigation_parameters_sim_yaml_file = os.path.join(d37pxi_navigation_dir, 'params', 'navigation_mppi.yaml')
    map_yaml_file = LaunchConfiguration('map', default=os.path.join(d37pxi_navigation_dir, 'map', 'map.yaml'))

    param_substitutions_nav = {
        'use_sim_time': str(use_sim_time),
        'yaml_filename': map_yaml_file,
        'robot_base_frame': tf_prefix_val + '/base_link',

        # amcl
        'amcl.ros__parameters.base_frame_id': tf_prefix_val+'/base_link',
        'amcl.ros__parameters.odom_frame_id': tf_prefix_val+'/odom',

        #component_container_isolated
        # 'component_container\isolated.ros__parameters.autostart': str(use_autostart),
        
        # bt_navigator
        'bt_navigator.ros__parameters.robot_base_frame': tf_prefix_val+'/base_link',
        'bt_navigator.ros__parameters.odom_topic': '/'+common_prefix_val+'/odom_pose',
        'bt_navigator.ros__parameters.default_nav_through_poses_bt_xml': os.path.join(d37pxi_navigation_dir, 'params', 'd37pxi_navigate_through_poses_w_replanning_and_recovery.xml'),
        'bt_navigator.ros__parameters.default_nav_to_pose_bt_xml': os.path.join(d37pxi_navigation_dir, 'params', 'd37pxi_navigate_to_pose.xml'),


        # controller_server
        'controller_server.ros__parameters.odom_topic': '/'+common_prefix_val+'/odom_pose',
        'controller_server.ros__parameters.base_global_frame': tf_prefix_val+'/odom',

        # local costmap
        'local_costmap.local_costmap.ros__parameters.global_frame': tf_prefix_val+'/odom',
        'local_costmap.local_costmap.ros__parameters.robot_base_frame': tf_prefix_val+'/base_link',

        # global costmap                        
        'global_costmap.global_costmap.ros__parameters.robot_base_frame': tf_prefix_val+'/base_link',

        # behavior server
        'behavior_server.ros__parameters.local_frame': tf_prefix_val+'/odom',
        'behavior_server.ros__parameters.local_costmap.global_frame': tf_prefix_val+'/odom',
        'behavior_server.ros__parameters.robot_base_frame': tf_prefix_val+'/base_link',

        # velocity smoother
        'velocity_smoother.odom_topic': '/'+common_prefix_val+'/odom_pose',
    }
    configured_params=RewrittenYaml(
        source_file=navigation_parameters_sim_yaml_file,
        root_key=common_prefix_val,
        param_rewrites=param_substitutions_nav,
        convert_types=True
    )


def rewrite_ekf_params(context, **kwargs):
    global configured_ekf_params
    d37pxi_navigation_dir = get_package_share_directory('d37pxi_navigation')
    d37pxi_ekf_yaml_file = LaunchConfiguration('ekf_yaml_file', default=os.path.join(d37pxi_navigation_dir, 'config', 'd37pxi_ekf.yaml'))
    configured_ekf_params=RewrittenYaml(
        source_file=d37pxi_ekf_yaml_file,
        root_key=common_prefix_val,
        param_rewrites={'use_sim_time': str(use_sim_time)},
        convert_types=True
    )

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



def generate_nodes(context, *args, **kwargs):
    opaque_function_complete_event.wait()
    d37pxi_bringup_dir = get_package_share_directory("d37pxi_bringup")
    d37pxi_standby_rviz_file = os.path.join(d37pxi_bringup_dir, "rviz2", "d37pxi_standby.rviz")

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
            namespace=common_prefix_val,
            name='world_to_map',
            # map origin in world; map coordinates = world coordinates - offset.
            # Keep d37pxi_navigation/map/map.yaml origin aligned with this offset.
            arguments=['--x', '21395.178',
                        '--y', '14034.450',
                        '--z', '28.552',
                        '--roll', '0', 
                        '--pitch', '0', 
                        '--yaw', '0', 
                        '--frame-id', 'world',
                        '--child-frame-id', 'map']),
        Node(
            package='d37pxi_navigation',
            executable='odom_broadcaster',
            namespace=common_prefix_val,
            name='odom_broadcaster',
            output="screen",
            parameters=[{'odom_topic': '/'+common_prefix_val+'/odom_pose'},
                        {'odom_frame': tf_prefix_val+ "/odom"},
                        {'base_link_frame': tf_prefix_val + "/base_link"},
                        {'use_sim_time': use_sim_time}]
        ),
        Node(
            package='d37pxi_navigation',
            executable='poseStamped2Odometry',
            namespace=common_prefix_val,
            name='poseStamped2ground_truth_odom',
            output="screen",
            parameters=[{'odom_header_frame': "world",
                            'odom_child_frame': tf_prefix_val+"/base_link",
                            'poseStamped_topic_name': '/'+common_prefix_val+"/global_pose",
                            'odom_topic_name': '/'+common_prefix_val+"/gnss_odom",
                            'use_sim_time': use_sim_time}]
        ),
        # 擬似的なオドメトリをGNSS測位データより取得
        Node(
            package="d37pxi_navigation",
            executable="odom_pose",
            namespace=common_prefix_val,
            name="odom_pose",
            parameters=[{'use_sim_time': use_sim_time}],
            remappings=[('global_pose', '/'+common_prefix_val+'/gnss_odom')],
            output="screen",
        ),            
        Node(
            package='robot_state_publisher',
            executable='robot_state_publisher',
            namespace=common_prefix_val,
            output="screen",
            parameters=[params, {'use_sim_time': use_sim_time}],
            remappings=[('joint_states', 'joint_state')]
        ),
        Node(
            condition=IfCondition('true'),
            name='nav2_container',
            package='rclcpp_components',
            executable='component_container_isolated',
            namespace=common_prefix_val,
            parameters=[configured_params],
            output='screen'),
        
        #########################
        # Localization packages #
        #########################

        Node(
            package='nav2_map_server',
            executable='map_server',
            namespace=common_prefix_val,
            name='map_server',
            output='screen',
            respawn=use_respawn,
            respawn_delay=2.0,
            parameters=[configured_params]),
        Node(
            package='robot_localization',
            executable='ekf_node',
            namespace=common_prefix_val,
            name="ekf_global",
            output="screen",
            remappings=[('odometry/filtered', '/'+common_prefix_val+'/odometry/global'),
                        ('odom0', '/'+common_prefix_val+'/odom_pose'),
                        ('odom1','/'+common_prefix_val+"/gnss_odom")],
            parameters=[configured_ekf_params,
                        {'map_frame': "map",
                            'world_frame': "map",
                            'odom_frame': tf_prefix_val+"/odom",
                            'base_link_frame': tf_prefix_val+"/base_link",
                            'use_sim_time': use_sim_time}]),
        Node(
            package='nav2_lifecycle_manager',
            executable='lifecycle_manager',
            namespace=common_prefix_val,
            name='lifecycle_manager_localization',
            output='screen',
            parameters=[{'use_sim_time': use_sim_time},
                        {'autostart': use_autostart},
                        {'node_names': lifecycle_nodes_localization}]),

        #######################
        # Navigation packages #
        #######################
        Node(
            package='nav2_controller',
            executable='controller_server',
            namespace=common_prefix_val,
            output='screen',
            respawn=use_respawn,
            respawn_delay=2.0,
            parameters=[configured_params],
            remappings=[('cmd_vel', 'cmd_vel_nav')]),
        Node(
            package='nav2_smoother',
            executable='smoother_server',
            namespace=common_prefix_val,
            name='smoother_server',
            output='screen',
            respawn=use_respawn,
            respawn_delay=2.0,
            parameters=[configured_params]),
        Node(
            package='nav2_planner',
            executable='planner_server',
            namespace=common_prefix_val,
            name='planner_server',
            output='screen',
            respawn=use_respawn,
            respawn_delay=2.0,
            parameters=[configured_params]),
        Node(
            package='nav2_behaviors',
            executable='behavior_server',
            namespace=common_prefix_val,
            name='behavior_server',
            output='screen',
            respawn=use_respawn,
            respawn_delay=2.0,
            parameters=[configured_params],
            # remappings=[('cmd_vel', 'tracks/cmd_vel')]
            ),
        Node(
            package='nav2_bt_navigator',
            executable='bt_navigator',
            namespace=common_prefix_val,
            name='bt_navigator',
            output='screen',
            respawn=use_respawn,
            respawn_delay=2.0,
            parameters=[configured_params],
            remappings=[(common_prefix_val+'/goal_pose', 'goal_pose')]),
        Node(
            package='nav2_waypoint_follower',
            executable='waypoint_follower',
            namespace=common_prefix_val,
            name='waypoint_follower',
            output='screen',
            respawn=use_respawn,
            respawn_delay=2.0,
            parameters=[configured_params]),
        Node(
            package='nav2_velocity_smoother',
            executable='velocity_smoother',
            namespace=common_prefix_val,
            name='velocity_smoother',
            output='screen',
            respawn=use_respawn,
            respawn_delay=2.0,
            parameters=[configured_params],
            remappings=[('cmd_vel', 'cmd_vel_nav'), 
                        ('cmd_vel_smoothed', 'cmd_vel')]),
        Node(
            package='nav2_lifecycle_manager',
            executable='lifecycle_manager',
            namespace=common_prefix_val,
            name='lifecycle_manager_navigation',
            output='screen',
            parameters=[{'use_sim_time': use_sim_time},
                        {'autostart': use_autostart},
                        {'node_names': lifecycle_nodes_navigation}]),
        Node(
            condition=IfCondition(LaunchConfiguration('use_rviz')),
            package="rviz2",
            executable="rviz2",
            namespace=common_prefix_val,
            name="rviz",
            parameters=[{'use_sim_time': use_sim_time}],
            arguments=["--display-config", d37pxi_standby_rviz_file]),
        
    ]


def generate_launch_description():
    common_prefix = LaunchConfiguration('common_prefix')
    use_rviz = LaunchConfiguration('use_rviz')
    common_prefix_arg = DeclareLaunchArgument('common_prefix',default_value='d37pxi')
    use_rviz_arg = DeclareLaunchArgument('use_rviz', default_value='true')

    return LaunchDescription([
        common_prefix_arg,
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
