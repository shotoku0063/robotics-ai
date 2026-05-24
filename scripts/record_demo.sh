#!/usr/bin/env bash
# UR5e Pick & Place デモを 1コマンドで実行 → MP4 出力
# 使い方:
#   ./scripts/record_demo.sh
# 出力:
#   output/demo.mp4

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "${ROOT_DIR}"

mkdir -p output

echo "==> [1/4] Dockerイメージをビルド（初回のみ約10分）..."
docker compose -f docker/docker-compose.yml --profile sim-demo build sim-demo

echo "==> [2/4] コンテナ内でワークスペースをビルド..."
docker compose -f docker/docker-compose.yml --profile sim-demo run --rm sim-demo \
    bash -c "cd /workspace/ros2_ws && colcon build --symlink-install --packages-select sim_demo"

echo "==> [3/4] シミュレーション起動 + 動画録画（約60秒）..."
docker compose -f docker/docker-compose.yml --profile sim-demo run --rm sim-demo \
    bash -c "source /workspace/ros2_ws/install/setup.bash && \
             timeout 90 ros2 launch sim_demo ur5e_demo.launch.py || true"

echo "==> [4/4] 完了確認..."
if [[ -f output/demo.mp4 ]]; then
    echo "✅ 成功: $(ls -lh output/demo.mp4 | awk '{print $5}') の MP4 が生成されました"
    echo "   → ${ROOT_DIR}/output/demo.mp4"
else
    echo "❌ MP4 が生成されませんでした。logs/ や docker compose logs を確認してください"
    exit 1
fi
