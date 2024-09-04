import os

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node, PushRosNamespace
from launch.actions import DeclareLaunchArgument, GroupAction
from launch.conditions import IfCondition

robot_name="d37pxi"
use_namespace=True

def generate_launch_description():

    d37pxi_description_dir=get_package_share_directory("d37pxi_description")
    d37pxi_navigation_dir=get_package_share_directory("d37pxi_navigation")

    d37pxi_ekf_yaml_file = LaunchConfiguration('ekf_yaml_file', default=os.path.join(d37pxi_navigation_dir, 'config', 'd37pxi_ekf.yaml'))

    return LaunchDescription([

        DeclareLaunchArgument('robot_name', default_value='d37pxi'),

        GroupAction([
            PushRosNamespace(
                condition=IfCondition(str(use_namespace)),
                namespace=robot_name),
            Node(
                package="d37pxi_navigation",
                executable="poseStamped2Odometry",
                name="poseStamped2Odometry",
                parameters=[{'poseStamped_topic_name':'/d37pxi/global_pose',
                             'odom_topic_name':'/d37pxi/gnss_odom',
                             'odom_child_frame':'gnss',
                             'odom_header_frame':'world'}],
            ),
            Node(
                package='robot_localization',
                executable='ekf_node',
                name='ekf_global',
                output="screen",
                remappings=[('odometry/filtered','/d37pxi/odometry/global'),
                            ('odom0','/d37pxi/odom_pose'),
                            ('odom1','/d37pxi/gnss_odom')], # GNSSのトピック名を確認すること
                parameters=[d37pxi_ekf_yaml_file,
                            {'map_frame' : 'map',
                            'odom_frame' : robot_name + '_tf/odom',
                            'base_link_frame' : robot_name + '_tf/base_link',
                            'world_frame' : 'map',
                            'use_sim_time' : False}]),
        ])
    ])
