"""UR5e Pick & Place オーケストレーションノード.

joint_trajectory_controller/follow_joint_trajectory アクション経由でハードコード
キーフレームを実行し、Perception の検出 (x, y) から shoulder_pan を補正する。

「グリッパ」は Gazebo の /demo/set_entity_state サービスを使って対象キューブを
TF (world → tool0) に毎tickテレポートさせる擬似実装。リアルな vacuum plugin は
v2 で導入する想定で、現状はキューブが弾き飛ばされず把持されているように見せる。
"""

import json
import math
import threading
import time

import rclpy
from rclpy.action import ActionClient
from rclpy.node import Node
from builtin_interfaces.msg import Duration
from std_msgs.msg import String
from trajectory_msgs.msg import JointTrajectory, JointTrajectoryPoint
from control_msgs.action import FollowJointTrajectory
from gazebo_msgs.srv import SetEntityState
from gazebo_msgs.msg import EntityState
from tf2_ros import Buffer, TransformListener, TransformException


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


# home → pre-pick → pick → lift → pre-place → place → lift → home
# 単位: rad。Perception 検出があれば shoulder_pan_joint は実行時に補正する。
HOME = [_rad(0), _rad(-90), _rad(0), _rad(-90), _rad(0), _rad(0)]

# spawn 想定位置 (cube_red/blue/green.sdf と一致させること)
ASSUMED_CUBE_XY = {
    "red":   (0.40, -0.15),
    "blue":  (0.50, -0.05),
    "green": (0.60,  0.05),
}

# 各色の pick / place キーフレーム（shoulder_pan は ASSUMED_CUBE_XY からの atan2 で補正）
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

# release 後にキューブをトレー上へ最終配置する世界座標
# (scene_workbench.sdf: tray=(0.7, 0.2, 0.43), 天板厚 0.01 / cube 0.04)
TRAY_DROP_XYZ = {
    "red":   (0.65, 0.20, 0.455),
    "blue":  (0.70, 0.20, 0.455),
    "green": (0.75, 0.20, 0.455),
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
        self.declare_parameter("gripper_tick_hz", 60.0)
        self.startup_delay = self.get_parameter("startup_delay_sec").value
        self.step_duration = self.get_parameter("step_duration_sec").value
        self.gripper_tick_hz = self.get_parameter("gripper_tick_hz").value

        action_topic = "/joint_trajectory_controller/follow_joint_trajectory"
        self.client = ActionClient(self, FollowJointTrajectory, action_topic)
        self.get_logger().info(f"Action client: {action_topic}")
        self.get_logger().info(
            f"起動から {self.startup_delay:.0f} 秒待機後にシーケンスを開始します"
        )

        self.tf_buffer = Buffer()
        self.tf_listener = TransformListener(self.tf_buffer, self)

        # gazebo_ros_state プラグインが提供する set_entity_state サービスを探す
        # （ワールドファイルによって namespace が異なるので候補リストから自動選択）
        self._set_state_candidates = [
            "/demo/set_entity_state",
            "/gazebo/set_entity_state",
            "/set_entity_state",
        ]
        self.set_state_cli = None

        self._detected_objects = {}
        self._first_detection_logged = False
        self.detection_sub = self.create_subscription(
            String, "/perception/detections", self._on_detection, 10
        )

        # 擬似グリッパの carry スレッド制御
        self._carry_target = None  # 把持中のキューブ名
        self._carry_stop = threading.Event()
        self._carry_thread = None

        self._thread = threading.Thread(target=self._orchestrate, daemon=True)
        self._thread.start()

    def _on_detection(self, msg):
        try:
            data = json.loads(msg.data)
            for det in data.get("detections", []):
                self._detected_objects[det["label"]] = (
                    det["x"], det["y"], det["z"]
                )
            if self._detected_objects and not self._first_detection_logged:
                self.get_logger().info(
                    f"Perception 受信: {list(self._detected_objects.keys())}"
                )
                self._first_detection_logged = True
        except (json.JSONDecodeError, KeyError, TypeError) as exc:
            self.get_logger().warn(f"detections パース失敗: {exc}")

    def _pan_correction(self, color):
        """検出された (x, y) と spawn 想定位置の base 角度差を返す (rad)."""
        det = self._detected_objects.get(color)
        if det is None:
            return 0.0
        ax, ay = ASSUMED_CUBE_XY[color]
        dx, dy, _ = det
        assumed_angle = math.atan2(ay, ax)
        detected_angle = math.atan2(dy, dx)
        delta = detected_angle - assumed_angle
        # 大きすぎる補正は誤検出の可能性が高いのでクリップ
        return max(-_rad(15), min(_rad(15), delta))

    def _corrected_pose(self, base_pose, color):
        corrected = list(base_pose)
        corrected[0] += self._pan_correction(color)
        return corrected

    def _carry_loop(self):
        period = 1.0 / max(1.0, self.gripper_tick_hz)
        tf_fail_count = 0
        tick = 0
        while not self._carry_stop.is_set():
            target = self._carry_target
            if target is not None and self.set_state_cli is not None:
                try:
                    tf = self.tf_buffer.lookup_transform(
                        "world", "tool0", rclpy.time.Time()
                    )
                    # Gazebo のエンティティ名は spawn 時に "cube_<color>" にしている
                    # kinematic link を直接動かすため "model::link" 形式を使う
                    entity_name = f"cube_{target}::link"
                    state = EntityState()
                    state.name = entity_name
                    state.reference_frame = "world"
                    state.pose.position.x = tf.transform.translation.x
                    state.pose.position.y = tf.transform.translation.y
                    # tool0 直下に少しオフセット（キューブが空中に浮いている見た目に）
                    state.pose.position.z = tf.transform.translation.z - 0.02
                    state.pose.orientation.w = 1.0
                    req = SetEntityState.Request()
                    req.state = state
                    self.set_state_cli.call_async(req)
                    tick += 1
                    # 30 tick (約0.5秒) ごとに進捗ログ：carry が実際に走っていることを可視化
                    if tick in (1, 30, 120, 300, 600):
                        self.get_logger().info(
                            f"[carry tick={tick}] target={entity_name} → "
                            f"tool0=({tf.transform.translation.x:.3f}, "
                            f"{tf.transform.translation.y:.3f}, "
                            f"{tf.transform.translation.z:.3f})"
                        )
                except TransformException as exc:
                    tf_fail_count += 1
                    if tf_fail_count in (1, 30, 300):
                        self.get_logger().warn(
                            f"[carry] TF lookup 失敗 ({tf_fail_count}回目): {exc}"
                        )
            time.sleep(period)

    def _grip(self, cube_name):
        self._carry_target = cube_name
        if self._carry_thread is None or not self._carry_thread.is_alive():
            self._carry_stop.clear()
            self._carry_thread = threading.Thread(
                target=self._carry_loop, daemon=True
            )
            self._carry_thread.start()

    def _release(self):
        self._carry_target = None  # carry スレッドは生かしたまま、次の grip で再利用

    def _drop_on_tray(self, cube_name):
        """release 後にトレー上の固定位置へキューブをワープさせる."""
        if self.set_state_cli is None or cube_name not in TRAY_DROP_XYZ:
            return
        x, y, z = TRAY_DROP_XYZ[cube_name]
        state = EntityState()
        state.name = f"cube_{cube_name}::link"
        state.reference_frame = "world"
        state.pose.position.x = x
        state.pose.position.y = y
        state.pose.position.z = z
        state.pose.orientation.w = 1.0
        req = SetEntityState.Request()
        req.state = state
        self.set_state_cli.call_async(req)

    def _orchestrate(self):
        time.sleep(self.startup_delay)

        if not self.client.wait_for_server(timeout_sec=10.0):
            self.get_logger().error(
                "Action server に接続できませんでした。controllers の起動を確認してください"
            )
            return

        # set_entity_state サービスを候補リストから検出
        for name in self._set_state_candidates:
            cli = self.create_client(SetEntityState, name)
            if cli.wait_for_service(timeout_sec=2.0):
                self.set_state_cli = cli
                self.get_logger().info(f"擬似グリッパ用 service 検出: {name}")
                break
        if self.set_state_cli is None:
            self.get_logger().warn(
                f"set_entity_state が {self._set_state_candidates} のどこにも見つかりません。"
                "擬似グリッパは無効（キューブは弾かれる挙動になります）"
            )

        self.get_logger().info("Pick & Place シーケンス開始")
        self._send(HOME, label="home (起点)")

        for name in ["red", "blue", "green"]:
            pan_corr = self._pan_correction(name)
            if abs(pan_corr) > 1e-3:
                self.get_logger().info(
                    f"  {name}: 検出ベース pan 補正 {math.degrees(pan_corr):+.1f}°"
                )
            pick = self._corrected_pose(PICK_POSES[name], name)
            place = self._corrected_pose(PLACE_POSES[name], name)
            pre_pick = _lift_offset(pick)
            pre_place = _lift_offset(place)

            self._send(pre_pick, label=f"{name} 上方へ移動 (pre-pick)")
            # 降下前に grip を活性化することで、衝突でキューブが弾かれる前に
            # carry スレッドが tool0 へ追従させる
            self._grip(name)
            self.get_logger().info(f"  ✦ {name} を把持 (carry on)")
            self._send(pick, label=f"{name} を把持位置へ降下 (carry中)")
            self._send(pre_pick, label=f"{name} を持ち上げ")

            self._send(pre_place, label=f"{name} をトレー上方へ移動")
            self._send(place, label=f"{name} をトレーに降下")
            self._release()
            self._drop_on_tray(name)
            self.get_logger().info(f"  ✦ {name} をトレーに配置 (carry off + drop)")
            self._send(pre_place, label=f"{name} 配置後に上昇")

        self._send(HOME, label="home (終端)")
        self._carry_stop.set()
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
