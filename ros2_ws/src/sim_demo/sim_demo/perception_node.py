"""ML を組み込んだ Perception ノード.

/camera/image_raw（sensor_msgs/Image）を購読し、以下のパイプラインで
検出結果を /perception/detections に JSON 文字列でパブリッシュする。

  1. HSV 色空間で 3色（red / blue / green）をしきい値検出
  2. 各 contour のセントロイドを抽出
  3. 切り出したパッチを PyTorch の小型 CNN に通して「部品らしさ」スコアを得る
  4. 簡易ピンホール逆投影で画像座標 → ワールド座標 (z は平面仮定)
  5. JSON にまとめて publish

CNN は学習済みではなくランダム初期化のため、confidence 値はあくまでデモ用。
学習データは Phase C 以降に Gazebo の Domain Randomization で生成する想定。
"""

import json

import cv2
import numpy as np
import rclpy
import torch
from cv_bridge import CvBridge
from rclpy.node import Node
from sensor_msgs.msg import Image
from std_msgs.msg import String


class TinyClassifier(torch.nn.Module):
    """部品パッチを 1 次元スコアに落とすデモ用 CNN（3x3 conv → GAP → FC）."""

    def __init__(self):
        super().__init__()
        self.conv = torch.nn.Conv2d(3, 8, kernel_size=3, padding=1)
        self.relu = torch.nn.ReLU()
        self.pool = torch.nn.AdaptiveAvgPool2d(1)
        self.fc = torch.nn.Linear(8, 1)

    def forward(self, x):
        x = self.relu(self.conv(x))
        x = self.pool(x).flatten(1)
        return torch.sigmoid(self.fc(x))


# HSV しきい値 (low, high)。OpenCV の H は 0..179
COLOR_RANGES = {
    "red":   ((0, 120, 70),   (10, 255, 255)),
    "blue":  ((100, 150, 70), (130, 255, 255)),
    "green": ((40, 70, 70),   (80, 255, 255)),
}

# overhead_camera.sdf の姿勢を仮定したざっくり逆投影パラメータ
# 詳細キャリブは省略、画像中心 → world (約 0.4, 0) に着地する線形マッピング
ASSUMED_OBJECT_Z = 0.475


class PerceptionNode(Node):
    def __init__(self):
        super().__init__("perception_node")
        self.bridge = CvBridge()
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        self.get_logger().info(f"Perception using device: {self.device}")

        self.model = TinyClassifier().to(self.device).eval()
        # 学習済み重みがあればここで torch.load → load_state_dict
        # 現状はランダム初期化（推論経路の疎通確認用途）

        self.image_sub = self.create_subscription(
            Image, "/camera/image_raw", self._on_image, 10
        )
        self.detection_pub = self.create_publisher(
            String, "/perception/detections", 10
        )
        # bbox / label / confidence を描画したフレームを publish する
        # （video_recorder が拾って MP4 に焼くので、Perception の働きが映像で見える）
        self.annotated_pub = self.create_publisher(
            Image, "/perception/annotated_image", 10
        )
        self._frame_count = 0
        self._announced_first_hit = False

    def _on_image(self, msg: Image):
        try:
            cv_image = self.bridge.imgmsg_to_cv2(msg, desired_encoding="bgr8")
        except Exception as exc:
            self.get_logger().warn(f"cv_bridge 失敗: {exc}")
            return

        detections = self._run_inference(cv_image)

        out = String()
        out.data = json.dumps({
            "detections": detections,
            "frame": self._frame_count,
            "timestamp": self.get_clock().now().nanoseconds,
        })
        self.detection_pub.publish(out)

        # 注釈付き画像 (bbox + label + 信頼度 + ヘッダ) を別トピックへ
        annotated = self._annotate(cv_image, detections)
        try:
            ann_msg = self.bridge.cv2_to_imgmsg(annotated, encoding="bgr8")
            ann_msg.header = msg.header  # 元フレームのタイムスタンプ・座標系を継承
            self.annotated_pub.publish(ann_msg)
        except Exception as exc:
            self.get_logger().warn(f"annotated publish 失敗: {exc}")

        self._frame_count += 1
        if detections and not self._announced_first_hit:
            labels = ", ".join(d["label"] for d in detections)
            self.get_logger().info(f"初検出 (frame {self._frame_count}): {labels}")
            self._announced_first_hit = True
        elif self._frame_count == 30 and not self._announced_first_hit:
            self.get_logger().info("30 フレーム経過、検出ゼロ（world に対象物体なし？）")

    def _run_inference(self, image: np.ndarray) -> list:
        hsv = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)
        h, w = image.shape[:2]
        detections = []

        for label, (low, high) in COLOR_RANGES.items():
            mask = cv2.inRange(hsv, np.array(low), np.array(high))
            contours, _ = cv2.findContours(
                mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE
            )
            for c in contours:
                area = float(cv2.contourArea(c))
                if area < 100:
                    continue
                M = cv2.moments(c)
                if M["m00"] == 0:
                    continue
                cx = int(M["m10"] / M["m00"])
                cy = int(M["m01"] / M["m00"])

                patch = self._extract_patch(image, cx, cy, size=32)
                confidence = self._classify(patch)
                wx, wy = self._project_to_world(cx, cy, w, h)

                detections.append({
                    "label": label,
                    "u": cx, "v": cy,
                    "x": wx, "y": wy, "z": ASSUMED_OBJECT_Z,
                    "area": area,
                    "confidence": confidence,
                })
        return detections

    def _extract_patch(self, image: np.ndarray, cx: int, cy: int, size: int = 32) -> np.ndarray:
        h, w = image.shape[:2]
        half = size // 2
        x0 = max(0, cx - half)
        y0 = max(0, cy - half)
        x1 = min(w, x0 + size)
        y1 = min(h, y0 + size)
        patch = image[y0:y1, x0:x1]
        if patch.shape[0] != size or patch.shape[1] != size:
            patch = cv2.resize(patch, (size, size))
        return patch

    def _classify(self, patch: np.ndarray) -> float:
        with torch.no_grad():
            tensor = (
                torch.from_numpy(patch)
                .permute(2, 0, 1)
                .unsqueeze(0)
                .float()
                / 255.0
            ).to(self.device)
            score = self.model(tensor).item()
        return float(score)

    def _annotate(self, image: np.ndarray, detections: list) -> np.ndarray:
        """検出結果を画像にオーバーレイ. bbox / label / confidence + ヘッダ."""
        canvas = image.copy()
        color_bgr = {
            "red":   (60,  60,  240),   # BGR (赤)
            "blue":  (240, 100, 60),    # BGR (青)
            "green": (60,  200, 60),    # BGR (緑)
        }
        for det in detections:
            u, v = int(det["u"]), int(det["v"])
            color = color_bgr.get(det["label"], (255, 255, 255))
            # area から bbox 半径を推定 (面積 = πr² と仮定)
            radius = max(28, int((det["area"] / 3.14159) ** 0.5) + 8)
            cv2.rectangle(canvas, (u - radius, v - radius),
                          (u + radius, v + radius), color, 2)
            # ラベルテキスト
            label_text = f"{det['label']} {det['confidence']:.2f}"
            (tw, th), _ = cv2.getTextSize(
                label_text, cv2.FONT_HERSHEY_SIMPLEX, 0.55, 1
            )
            cv2.rectangle(canvas,
                          (u - radius, v - radius - th - 8),
                          (u - radius + tw + 8, v - radius),
                          color, -1)
            cv2.putText(canvas, label_text,
                        (u - radius + 4, v - radius - 4),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.55, (255, 255, 255), 1,
                        cv2.LINE_AA)
            # 中心マーカー
            cv2.circle(canvas, (u, v), 3, color, -1)

        # 上部ヘッダ
        h, w = canvas.shape[:2]
        cv2.rectangle(canvas, (0, 0), (w, 36), (20, 20, 20), -1)
        cv2.putText(canvas,
                    "AI Perception: OpenCV HSV + PyTorch CNN inference",
                    (12, 24), cv2.FONT_HERSHEY_SIMPLEX, 0.55,
                    (240, 240, 240), 1, cv2.LINE_AA)
        # 下部ステータス
        cv2.rectangle(canvas, (0, h - 28), (w, h), (20, 20, 20), -1)
        status = (
            f"frame {self._frame_count:04d}  |  detections: "
            f"{len(detections)}  |  device: {self.device}"
        )
        cv2.putText(canvas, status, (12, h - 9),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.45,
                    (220, 220, 220), 1, cv2.LINE_AA)
        return canvas

    def _project_to_world(self, u: int, v: int, w: int, h: int) -> tuple:
        # 簡易マッピング: 画像中心を world (0.4, 0) に置き、視野を線形に展開
        # 真面目には camera intrinsics + 平面交差で解く
        x_world = 0.4 + (0.5 - v / h) * 0.6   # 縦方向（v）→ 前後 x
        y_world = (u / w - 0.5) * 0.5         # 横方向（u）→ 左右 y
        return (float(x_world), float(y_world))


def main(args=None):
    rclpy.init(args=args)
    node = PerceptionNode()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == "__main__":
    main()
