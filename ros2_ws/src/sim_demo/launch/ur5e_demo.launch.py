"""UR5e Pick & Place デモ統合 launch ファイル.

UR Gazebo Simulation launch を include し、その上に Pick & Place ノードと
動画録画ノードを乗せる。Gazebo 起動後に観測用カメラを spawn_entity で追加し、
/camera/image_raw に画像を流して video_recorder に拾わせる。
"""

from launch import LaunchDescription
from launch.actions import IncludeLaunchDescription, TimerAction
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import PathJoinSubstitution
from launch_ros.actions import Node
from launch_ros.substitutions import FindPackageShare


def generate_launch_description():
    # UR5e + Gazebo + ros2_control は UR 公式 launch に任せる
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

    # オブザーバーカメラを Gazebo 起動後に動的 spawn
    # /spawn_entity が立ち上がるのが ~7 秒後なので少し余裕をもって 9 秒待つ
    def _sdf(name):
        return PathJoinSubstitution([
            FindPackageShare("sim_demo"), "worlds", f"{name}.sdf"
        ])

    def _spawn(entity_name, sdf_name, pose=None):
        args = ["-entity", entity_name, "-file", _sdf(sdf_name)]
        if pose is not None:
            x, y, z = pose
            args += ["-x", str(x), "-y", str(y), "-z", str(z)]
        return Node(
            package="gazebo_ros",
            executable="spawn_entity.py",
            name=f"spawn_{entity_name}",
            arguments=args,
            output="screen",
        )

    spawn_camera = TimerAction(
        period=9.0,
        actions=[_spawn("overhead_camera", "overhead_camera")],
    )

    # ワークベンチ（テーブル + トレー）とカラフルな部品 3 個を spawn
    # 検出対象が world に存在することで Perception が実検出を出力するようになる
    spawn_scene = TimerAction(
        period=10.5,
        actions=[_spawn("scene_workbench", "scene_workbench")],
    )
    spawn_cubes = TimerAction(
        period=11.5,
        actions=[
            _spawn("cube_red",   "cube_red",   pose=(0.40, -0.15, 0.45)),
            _spawn("cube_blue",  "cube_blue",  pose=(0.50, -0.05, 0.45)),
            _spawn("cube_green", "cube_green", pose=(0.60,  0.05, 0.45)),
        ],
    )

    # Perception ノード（OpenCV 色検出 + PyTorch CNN 推論）
    perception = Node(
        package="sim_demo",
        executable="perception",
        name="perception_node",
        output="screen",
    )

    # Pick & Place オーケストレーション
    pick_place = Node(
        package="sim_demo",
        executable="pick_and_place",
        name="pick_and_place_node",
        output="screen",
        parameters=[{
            "startup_delay_sec": 14.0,   # gzserver + コントローラ + カメラ起動を待つ
            "step_duration_sec": 2.5,
        }],
    )

    # MP4 録画ノード（カメラ起動 t=10 〜 pick_and_place 終了 t=70 + 余裕 = 75秒）
    recorder = Node(
        package="sim_demo",
        executable="video_recorder",
        name="video_recorder_node",
        output="screen",
        parameters=[{
            "output_path": "/workspace/output/demo.mp4",
            "fps": 30,
            "duration_sec": 75,
        }],
    )

    return LaunchDescription([
        ur_sim,
        spawn_camera,
        spawn_scene,
        spawn_cubes,
        perception,
        pick_place,
        recorder,
    ])
