"""UR5e Pick & Place デモ統合 launch ファイル.

Gazebo (ヘッドレス) + UR5e + 俯瞰カメラ + 動画記録ノードを起動する。
"""

from launch import LaunchDescription
from launch.actions import IncludeLaunchDescription, ExecuteProcess, DeclareLaunchArgument
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration, PathJoinSubstitution
from launch_ros.actions import Node
from launch_ros.substitutions import FindPackageShare


def generate_launch_description():
    headless = LaunchConfiguration("headless", default="true")
    world_file = PathJoinSubstitution([
        FindPackageShare("sim_demo"), "worlds", "semiconductor_workbench.world"
    ])

    gazebo = ExecuteProcess(
        cmd=[
            "gazebo",
            "--verbose",
            "-s", "libgazebo_ros_init.so",
            "-s", "libgazebo_ros_factory.so",
            world_file,
        ],
        additional_env={"GAZEBO_PLUGIN_PATH": "/opt/ros/humble/lib"},
        output="screen",
    )

    # UR5e は ur_simulation_gazebo パッケージの公式 launch を流用
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
    )

    # MP4 録画ノード
    recorder = Node(
        package="sim_demo",
        executable="video_recorder",
        name="video_recorder_node",
        output="screen",
        parameters=[{
            "output_path": "/workspace/output/demo.mp4",
            "fps": 30,
            "duration_sec": 30,
        }],
    )

    return LaunchDescription([
        DeclareLaunchArgument("headless", default_value="true"),
        gazebo,
        ur_sim,
        pick_place,
        recorder,
    ])
