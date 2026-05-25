#!/bin/bash
# シミュレーション用エントリーポイント
# Xvfb（仮想 X server）を起動してヘッドレス環境でも Gazebo を動かす
set -e

# Xvfb 起動（GUI 表示なしでも OpenGL レンダリングを可能にする）
Xvfb :99 -screen 0 1280x720x24 +extension RANDR &
export DISPLAY=:99

# ROS 2 環境を有効化
source /opt/ros/humble/setup.bash
if [ -f /workspace/ros2_ws/install/setup.bash ]; then
  source /workspace/ros2_ws/install/setup.bash
fi

# Gazebo 用環境変数
export GAZEBO_PLUGIN_PATH=/opt/ros/humble/lib:${GAZEBO_PLUGIN_PATH}
export QT_QPA_PLATFORM=offscreen

# UR5e sim が使う empty.world に gazebo_ros_state プラグインを注入
# （/demo/set_entity_state サービスを提供し、擬似グリッパが動くようにする）
EMPTY_WORLD="/opt/ros/humble/share/gazebo_ros/worlds/empty.world"
if [ -f "${EMPTY_WORLD}" ] && ! grep -q "gazebo_ros_state" "${EMPTY_WORLD}"; then
  python3 - "${EMPTY_WORLD}" <<'PY'
import sys, pathlib
p = pathlib.Path(sys.argv[1])
text = p.read_text()
plugin = (
  '    <plugin name="gazebo_ros_state" filename="libgazebo_ros_state.so">\n'
  '      <ros><namespace>/demo</namespace></ros>\n'
  '      <update_rate>30.0</update_rate>\n'
  '    </plugin>\n'
)
patched = text.replace('</world>', plugin + '  </world>', 1)
p.write_text(patched)
print(f"[entrypoint_sim] Injected gazebo_ros_state plugin into {p}")
PY
fi

# 渡されたコマンドを実行（指定がなければ bash）
exec "$@"
