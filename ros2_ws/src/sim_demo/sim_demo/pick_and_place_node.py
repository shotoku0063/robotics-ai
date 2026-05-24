"""UR5e Pick & Place オーケストレーションノード.

scaled_joint_trajectory_controller/follow_joint_trajectory アクション経由で
事前定義したジョイント角キーフレームを順次実行する。

MoveIt 2 IK ソルバを介さず直接ジョイント角を指定することで、
シミュレーション環境の依存を最小化している（実機転用時は MoveIt 2 統合に
差し替え推奨）。
"""

import math
import threading
import time

import rclpy
from rclpy.action import ActionClient
from rclpy.node import Node
from builtin_interfaces.msg import Duration
from trajectory_msgs.msg import JointTrajectory, JointTrajectoryPoint
from control_msgs.action import FollowJointTrajectory


UR5E_JOINTS = [
    "shoulder_pan_joint",
    "shoulder_lift_joint",
    "elbow_joint",
    "wrist_1_joint",
    "wrist_2_joint",
    "wrist_3_joint",
]


def _rad(deg):
    return deg * math.pi / 180.0


# 半導体ワークベンチ上のキーフレーム（ラフな目視推定値、要キャリブレーション）
# home → pre-pick → pick → lift → pre-place → place → lift → home
# 単位: rad
HOME = [_rad(0), _rad(-90), _rad(0), _rad(-90), _rad(0), _rad(0)]

PICK_POSES = {
    "red":   [_rad( 20), _rad(-60), _rad(95), _rad(-125), _rad(-90), _rad(0)],
    "blue":  [_rad(  0), _rad(-55), _rad(100), _rad(-135), _rad(-90), _rad(0)],
    "green": [_rad(-15), _rad(-60), _rad(95), _rad(-125), _rad(-90), _rad(0)],
}

PLACE_POSES = {
    "red":   [_rad(-25), _rad(-55), _rad(85), _rad(-120), _rad(-90), _rad(0)],
    "blue":  [_rad(-30), _rad(-55), _rad(85), _rad(-120), _rad(-90), _rad(0)],
    "green": [_rad(-35), _rad(-55), _rad(85), _rad(-120), _rad(-90), _rad(0)],
}


def _lift_offset(pose, lift_rad=-0.3):
    """shoulder_lift_joint を上方向に少し回転させた“ホバー”姿勢."""
    hovered = list(pose)
    hovered[1] += lift_rad
    return hovered


class PickAndPlaceNode(Node):
    def __init__(self):
        super().__init__("pick_and_place_node")
        self.declare_parameter("startup_delay_sec", 10.0)
        self.declare_parameter("step_duration_sec", 2.5)
        self.startup_delay = self.get_parameter("startup_delay_sec").value
        self.step_duration = self.get_parameter("step_duration_sec").value

        # ur_simulation_gazebo は scaled_ 接頭辞なしの joint_trajectory_controller を spawn する
        # （実機 ur_robot_driver は scaled_joint_trajectory_controller を使用）
        action_topic = "/joint_trajectory_controller/follow_joint_trajectory"
        self.client = ActionClient(self, FollowJointTrajectory, action_topic)
        self.get_logger().info(f"Action client: {action_topic}")
        self.get_logger().info(
            f"起動から {self.startup_delay:.0f} 秒待機後にシーケンスを開始します"
        )

        # オーケストレーションはバックグラウンドスレッドで実行
        # （Executor を塞がないため、ROS 2 のコールバックは並行して捌ける）
        self._thread = threading.Thread(target=self._orchestrate, daemon=True)
        self._thread.start()

    def _orchestrate(self):
        time.sleep(self.startup_delay)

        if not self.client.wait_for_server(timeout_sec=10.0):
            self.get_logger().error(
                "Action server に接続できませんでした。controllers の起動を確認してください"
            )
            return

        self.get_logger().info("Pick & Place シーケンス開始")
        self._send(HOME, label="home (起点)")

        for name in ["red", "blue", "green"]:
            pre = _lift_offset(PICK_POSES[name])
            self._send(pre, label=f"{name} 上方へ移動 (pre-pick)")
            self._send(PICK_POSES[name], label=f"{name} を把持位置へ降下")
            # gripper close 相当: ここではログのみ（gripper plugin 統合は v2 で）
            self.get_logger().info(f"  ✦ {name} を把持（gripper close 相当）")
            self._send(pre, label=f"{name} を持ち上げ")

            pre_place = _lift_offset(PLACE_POSES[name])
            self._send(pre_place, label=f"{name} をトレー上方へ移動")
            self._send(PLACE_POSES[name], label=f"{name} をトレーに降下")
            self.get_logger().info(f"  ✦ {name} を配置（gripper open 相当）")
            self._send(pre_place, label=f"{name} 配置後に上昇")

        self._send(HOME, label="home (終端)")
        self.get_logger().info("Pick & Place シーケンス完了")

    def _send(self, joint_positions, label=""):
        traj = JointTrajectory()
        traj.joint_names = UR5E_JOINTS

        point = JointTrajectoryPoint()
        point.positions = joint_positions
        sec = int(self.step_duration)
        nsec = int((self.step_duration - sec) * 1e9)
        point.time_from_start = Duration(sec=sec, nanosec=nsec)
        traj.points = [point]

        goal = FollowJointTrajectory.Goal()
        goal.trajectory = traj

        if label:
            self.get_logger().info(f"→ {label}")
        # Fire-and-forget: 軌道の time_from_start でコントローラが動作完了タイミングを管理する
        # 結果取得を待たず、step_duration + 余裕分だけ Python 側で wait
        self.client.send_goal_async(goal)
        time.sleep(self.step_duration + 0.3)


def main(args=None):
    rclpy.init(args=args)
    node = PickAndPlaceNode()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == "__main__":
    main()
