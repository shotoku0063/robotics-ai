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

# 渡されたコマンドを実行（指定がなければ bash）
exec "$@"
