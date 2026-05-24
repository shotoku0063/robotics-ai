"""Gazebo 仮想カメラの映像を FFmpeg subprocess 経由で MP4 化するノード.

/camera/image_raw（sensor_msgs/Image, BGR8）を購読し、
ffmpeg の stdin に raw frame を書き込んで H.264 / MP4 に圧縮する。
"""

import subprocess
import rclpy
from rclpy.node import Node
from sensor_msgs.msg import Image
from cv_bridge import CvBridge


class VideoRecorderNode(Node):
    def __init__(self):
        super().__init__("video_recorder_node")

        self.declare_parameter("output_path", "/workspace/output/demo.mp4")
        self.declare_parameter("fps", 30)
        self.declare_parameter("duration_sec", 30)
        self.declare_parameter("width", 1280)
        self.declare_parameter("height", 720)
        self.declare_parameter("topic", "/camera/image_raw")

        self.output = self.get_parameter("output_path").value
        self.fps = self.get_parameter("fps").value
        self.duration = self.get_parameter("duration_sec").value
        self.width = self.get_parameter("width").value
        self.height = self.get_parameter("height").value
        topic = self.get_parameter("topic").value

        self.bridge = CvBridge()
        self.frames_written = 0
        self.max_frames = self.fps * self.duration

        # FFmpeg を subprocess で起動（stdin に raw BGR フレームを流し込む）
        self.ffmpeg = subprocess.Popen(
            [
                "ffmpeg", "-y",
                "-f", "rawvideo",
                "-vcodec", "rawvideo",
                "-pix_fmt", "bgr24",
                "-s", f"{self.width}x{self.height}",
                "-r", str(self.fps),
                "-i", "-",
                "-c:v", "libx264",
                "-preset", "ultrafast",
                "-pix_fmt", "yuv420p",
                self.output,
            ],
            stdin=subprocess.PIPE,
        )

        self.sub = self.create_subscription(Image, topic, self._on_image, 10)
        self.get_logger().info(
            f"録画開始: {self.output} ({self.duration}秒 @ {self.fps}fps, トピック {topic})"
        )

    def _on_image(self, msg):
        if self.frames_written >= self.max_frames:
            return

        frame = self.bridge.imgmsg_to_cv2(msg, desired_encoding="bgr8")
        try:
            self.ffmpeg.stdin.write(frame.tobytes())
            self.frames_written += 1
        except BrokenPipeError:
            self.get_logger().error("FFmpeg pipe broken, recording stopped")
            self.max_frames = 0
            return

        if self.frames_written == self.max_frames:
            self.get_logger().info(
                f"録画完了: {self.frames_written} frames → {self.output}"
            )
            self._finalize()

    def _finalize(self):
        try:
            self.ffmpeg.stdin.close()
            self.ffmpeg.wait(timeout=10)
        except subprocess.TimeoutExpired:
            self.ffmpeg.kill()

    def destroy_node(self):
        self._finalize()
        super().destroy_node()


def main(args=None):
    rclpy.init(args=args)
    node = VideoRecorderNode()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == "__main__":
    main()
