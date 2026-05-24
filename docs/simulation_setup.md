# UR5e Pick & Place シミュレーション

実機なし・初期費用 0 円で UR5e の Pick & Place 動作を Gazebo で再現し、MP4 動画を出力するセットアップ。

## クイックスタート

```bash
./scripts/record_demo.sh
```

これだけで以下が自動実行され、`output/demo.mp4` が生成される：

1. Dockerイメージビルド（初回 ~10分）
2. ROS 2 ワークスペースビルド
3. Gazebo ヘッドレス起動 + UR5e + Pick & Place 実行
4. 仮想カメラの映像を FFmpeg 経由で MP4 化

## 構成

```
docker/
├── Dockerfile.simulation        # ros:humble-desktop + MoveIt 2 + UR + FFmpeg
├── entrypoint_sim.sh            # Xvfb 起動でヘッドレス対応
└── docker-compose.yml           # --profile sim-demo で起動

ros2_ws/src/sim_demo/
├── package.xml
├── setup.py
├── worlds/
│   └── semiconductor_workbench.world   # 作業台 + 部品3個 + トレー + 俯瞰カメラ
├── launch/
│   └── ur5e_demo.launch.py             # 統合 launch
└── sim_demo/
    ├── pick_and_place_node.py          # Pick & Place オーケストレーション
    └── video_recorder_node.py          # FFmpeg pipe で MP4 出力

scripts/
└── record_demo.sh                       # 1コマンド全自動実行
output/
└── demo.mp4                             # 生成される動画
```

## 個別操作

### Docker イメージのみビルド

```bash
docker compose -f docker/docker-compose.yml --profile sim-demo build
```

### コンテナに入って手動操作

```bash
docker compose -f docker/docker-compose.yml --profile sim-demo run --rm sim-demo bash
# 内部で:
source /workspace/ros2_ws/install/setup.bash
ros2 launch sim_demo ur5e_demo.launch.py headless:=true
```

### GUI で確認したい場合（Linux のみ、Mac は XQuartz 必要）

`docker-compose.yml` の `sim-demo` サービスから `QT_QPA_PLATFORM=offscreen` を外し、`DISPLAY=${DISPLAY}` と X11 socket マウントを追加した上で：

```bash
xhost +local:docker
docker compose -f docker/docker-compose.yml --profile sim-demo run --rm sim-demo \
    bash -c "ros2 launch sim_demo ur5e_demo.launch.py headless:=false"
```

## 注意事項

- **本実装は雛形**。`pick_and_place_node.py` の `_move_to` / `_close_gripper` は MoveIt 2 / GripperCommand 未統合のスケルトン。実動作させるには `moveit_msgs/MoveGroup` Action client を実装する必要あり
- **MoveIt 2 設定ファイル** (SRDF / kinematics.yaml) はこの雛形では UR 公式の `ur_moveit_config` をそのまま利用する想定
- **Mac M1/M2 環境**では Docker Desktop の仮想化レイヤで Gazebo が遅い可能性あり。CI 環境（GitHub Actions Ubuntu runner）の方が安定する場合がある
- 初回ビルドは数十分かかる場合あり。CI 用にイメージをキャッシュすると良い

## 拡張ロードマップ

- **v1**: 本構成（3部品の Pick & Place、MP4 出力）
- **v2**: ベルトコンベア追加、不良品検出シーン、多サイズ部品対応
- **v3**: 把持位置推定の学習モデル統合、Domain Randomization、Sim-to-Real 実機転用

詳細は [`docs/simulation_demo.html`](simulation_demo.html) のスライド資料を参照。
