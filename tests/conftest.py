import sys
from unittest.mock import MagicMock


class _MockNode:
    """Minimal stand-in for rclpy.node.Node so PerceptionNode can be subclassed."""

    def __init__(self, node_name, **kwargs):
        self._node_name = node_name

    def get_logger(self):
        return MagicMock()

    def create_subscription(self, *args, **kwargs):
        return MagicMock()

    def create_publisher(self, *args, **kwargs):
        return MagicMock()

    def get_clock(self):
        clock = MagicMock()
        clock.now.return_value.nanoseconds = 0
        return clock


_mock_rclpy = MagicMock()
_mock_rclpy_node = MagicMock()
_mock_rclpy_node.Node = _MockNode

sys.modules.setdefault("rclpy", _mock_rclpy)
sys.modules.setdefault("rclpy.node", _mock_rclpy_node)
sys.modules.setdefault("sensor_msgs", MagicMock())
sys.modules.setdefault("sensor_msgs.msg", MagicMock())
sys.modules.setdefault("std_msgs", MagicMock())
sys.modules.setdefault("std_msgs.msg", MagicMock())
sys.modules.setdefault("cv_bridge", MagicMock())
sys.modules.setdefault("cv2", MagicMock())
sys.modules.setdefault("torch", MagicMock())
sys.modules.setdefault("torch.nn", MagicMock())
sys.modules.setdefault("torch.utils", MagicMock())
sys.modules.setdefault("torch.utils.data", MagicMock())
sys.modules.setdefault("torchvision", MagicMock())
sys.modules.setdefault("numpy", MagicMock())
