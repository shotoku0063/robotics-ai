# Robotics AI

ROS 2 + PyTorch + OpenCV を使ったロボティクスAIプロジェクト。

## 構成

```
robotics-ai/
├── ros2_ws/src/robotics_ai/   # ROS 2 パッケージ
│   └── robotics_ai/
│       ├── nodes/             # ROS 2 ノード
│       ├── perception/        # 認識モジュール
│       ├── planning/          # 計画モジュール
│       └── control/           # 制御モジュール
├── models/                    # 学習済みモデル
├── scripts/                   # 学習・評価スクリプト
├── config/                    # 設定ファイル
├── data/                      # データセット
├── docker/                    # Docker 環境
├── tests/                     # テスト
└── docs/                      # ドキュメント
```

## セットアップ

### Docker を使う場合（推奨）

```bash
cd docker
docker-compose up -d
docker-compose exec robotics-ai bash
```

### ローカル環境（ROS 2 Humble インストール済みの場合）

```bash
# Python 依存関係
pip install -r requirements.txt

# ROS 2 ワークスペースをビルド
cd ros2_ws
source /opt/ros/humble/setup.bash
colcon build --symlink-install
source install/setup.bash
```

## 使い方

### ROS 2 ノードを起動

```bash
source ros2_ws/install/setup.bash
ros2 run robotics_ai perception_node
```

### モデルの学習

```bash
python scripts/train.py --data data/processed --epochs 100
```

### シミュレーター（Gazebo）付きで起動

```bash
docker-compose --profile simulation up
```

## 技術スタック

- **ROS 2 Humble** — ロボット制御フレームワーク
- **PyTorch** — 深層学習
- **OpenCV** — コンピュータビジョン
- **Gazebo** — ロボットシミュレーター
