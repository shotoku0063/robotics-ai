"""UR5e Pick & Place オーケストレーションノード.

MoveIt 2 経由で 3 個の部品を順次把持しトレーに配置する。
本ファイルは「動作シーケンスの骨格」を示すスケルトン実装で、
実 IK・把持指令は moveit2_py の MoveGroupCommander などで実装する。
"""

import rclpy
from rclpy.node import Node
from geometry_msgs.msg import Pose


# 部品の初期座標（world ファイルと一致）と配置先トレー座標
COMPONENTS = [
    {"name": "red",   "pick": (0.40, -0.15, 0.46), "place": (0.65, 0.18, 0.46)},
    {"name": "blue",  "pick": (0.50, -0.05, 0.46), "place": (0.70, 0.20, 0.46)},
    {"name": "green", "pick": (0.60,  0.05, 0.46), "place": (0.75, 0.22, 0.46)},
]


class PickAndPlaceNode(Node):
    def __init__(self):
        super().__init__("pick_and_place_node")
        self.get_logger().info("UR5e Pick & Place デモ開始")
        self.timer = self.create_timer(2.0, self._step)
        self.index = 0

    def _step(self):
        if self.index >= len(COMPONENTS):
            self.get_logger().info("すべての部品の Pick & Place が完了しました")
            self.timer.cancel()
            return

        target = COMPONENTS[self.index]
        self.get_logger().info(
            f"[{self.index + 1}/{len(COMPONENTS)}] {target['name']} 部品を把持 → トレーへ配置"
        )
        self._move_to(target["pick"])
        self._close_gripper()
        self._move_to(target["place"])
        self._open_gripper()
        self.index += 1

    def _move_to(self, xyz):
        # NOTE: 実装時は MoveIt 2 (moveit_msgs/MoveGroup) で IK 解いて軌道送信
        pose = Pose()
        pose.position.x, pose.position.y, pose.position.z = xyz
        self.get_logger().info(f"  → {xyz} へ移動指令（MoveIt 2 統合 TODO）")

    def _close_gripper(self):
        self.get_logger().info("  → グリッパ把持（GripperCommand TODO）")

    def _open_gripper(self):
        self.get_logger().info("  → グリッパ開放（GripperCommand TODO）")


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
