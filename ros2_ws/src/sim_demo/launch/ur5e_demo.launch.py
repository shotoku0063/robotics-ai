"""UR5e Pick & Place デモ統合 launch ファイル.

UR Gazebo Simulation launch を include し、その上に Pick & Place ノードと
動画録画ノードを乗せる。Gazebo 自体は UR launch 内で起動するので二重起動しない。
"""

from launch import LaunchDescription
from launch.actions import IncludeLaunchDescription
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import PathJoinSubstitution
from launch_ros.actions import Node
from launch_ros.substitutions import FindPackageShare


def generate_launch_description():
    # UR5e + Gazebo + ros2_control は UR 公式 launch に任せる
    # (前回 ExecuteProcess(gazebo) を独自に起動して port 11345 が衝突したため削除)
    ur_sim = IncludeLaunchDescription(
        PythonLaunchDescriptionSource([
            PathJoinSubstitution([
                FindPackageShare("ur_simulation_gazebo"),
                "launch", "ur_sim_control.launch.py",
            ])
        ]),
        launch_arguments={
            "ur_type": "ur5e",
            "launch_rviz": "false",
        }.items(),
    )

    # Pick & Place オーケストレーション
    pick_place = Node(
        package="sim_demo",
        executable="pick_and_place",
        name="pick_and_place_node",
        output="screen",
        parameters=[{
            "startup_delay_sec": 12.0,   # gzserver + コントローラ起動を待つ
            "step_duration_sec": 2.5,
        }],
    )

    # MP4 録画ノード（Pick & Place 約 50秒 + 余裕 5秒 = 55秒）
    # UR の default world はカメラなしなので、現状は黒画面の動画が出る。
    # セマンティックな世界はあとで spawn_entity で個別に追加する予定。
    recorder = Node(
        package="sim_demo",
        executable="video_recorder",
        name="video_recorder_node",
        output="screen",
        parameters=[{
            "output_path": "/workspace/output/demo.mp4",
            "fps": 30,
            "duration_sec": 55,
        }],
    )

    return LaunchDescription([
        ur_sim,
        pick_place,
        recorder,
    ])
