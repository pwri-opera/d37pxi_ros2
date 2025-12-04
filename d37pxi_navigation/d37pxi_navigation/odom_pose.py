#!/usr/bin/env python3

import rclpy
from rclpy.node import Node
from nav_msgs.msg import Odometry


class LocalPoseNodePy(Node):
    def __init__(self):
        super().__init__('odom_pose')

        # サブスクライバ (Odometry の購読)
        self.subscription = self.create_subscription(
            Odometry,
            'global_pose',
            self.global_pose_callback,
            10
        )

        # パブリッシャ (ローカル座標系の Odometry を配信)
        self.publisher = self.create_publisher(
            Odometry,
            'odom_pose',
            10
        )

        # 初期位置がセット済みかどうかのフラグと保存用変数
        self.have_initial_pose = False
        self.initial_odom = Odometry()

    def global_pose_callback(self, msg: Odometry):
        """グローバル座標 Odometry メッセージを受け取るコールバック関数"""
        # 初めて受信したときに初期姿勢を保存する
        if not self.have_initial_pose:
            self.initial_odom = msg
            self.have_initial_pose = True

            init_pos = msg.pose.pose.position
            self.get_logger().info(
                f'Initial pose set to x={init_pos.x:.3f}, '
                f'y={init_pos.y:.3f}, z={init_pos.z:.3f}'
            )
            return

        # 2回目以降は相対座標を計算してパブリッシュする
        local_odom = Odometry()

        # ヘッダ等をコピー（必要に応じて frame_id などを変更）
        local_odom.header = msg.header
        local_odom.header.frame_id = "d37pxi_tf/odom"
        local_odom.child_frame_id = msg.child_frame_id

        # 相対位置の計算
        local_odom.pose = msg.pose  # まず丸ごとコピーしてから位置だけ差分にする
        local_odom.pose.pose.position.x = (
            msg.pose.pose.position.x - self.initial_odom.pose.pose.position.x
        )
        local_odom.pose.pose.position.y = (
            msg.pose.pose.position.y - self.initial_odom.pose.pose.position.y
        )
        local_odom.pose.pose.position.z = (
            msg.pose.pose.position.z - self.initial_odom.pose.pose.position.z
        )

        # orientation はここではグローバルのままコピー（相対角にしたければ別途計算）
        # local_odom.pose.pose.orientation = msg.pose.pose.orientation  # すでにコピー済み

        # twist もそのままコピー（必要なら相対速度にする処理をここに追加）
        local_odom.twist = msg.twist

        self.publisher.publish(local_odom)


def main(args=None):
    rclpy.init(args=args)
    node = LocalPoseNodePy()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()