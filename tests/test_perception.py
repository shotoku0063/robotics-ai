import sys
import os
from unittest.mock import MagicMock

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "ros2_ws", "src", "robotics_ai"))

from robotics_ai.nodes.perception_node import PerceptionNode  # noqa: E402


def _make_node():
    return PerceptionNode()


def test_node_name():
    node = _make_node()
    assert node._node_name == "perception_node"


def test_run_inference_returns_detections_key():
    node = _make_node()
    result = node.run_inference(MagicMock())
    assert "detections" in result
    assert result["detections"] == []


def test_run_inference_returns_timestamp_key():
    node = _make_node()
    result = node.run_inference(MagicMock())
    assert "timestamp" in result


def test_image_callback_publishes():
    node = _make_node()
    node.bridge = MagicMock()
    node.bridge.imgmsg_to_cv2.return_value = MagicMock()
    node.detection_pub = MagicMock()

    fake_msg = MagicMock()
    node.image_callback(fake_msg)

    node.detection_pub.publish.assert_called_once()
