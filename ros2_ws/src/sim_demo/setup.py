from setuptools import setup
from glob import glob

package_name = "sim_demo"

setup(
    name=package_name,
    version="0.1.0",
    packages=[package_name],
    data_files=[
        ("share/ament_index/resource_index/packages", ["resource/" + package_name]),
        ("share/" + package_name, ["package.xml"]),
        ("share/" + package_name + "/launch", glob("launch/*.py")),
        ("share/" + package_name + "/worlds", glob("worlds/*.world") + glob("worlds/*.sdf")),
        ("share/" + package_name + "/config", glob("config/*.yaml")),
    ],
    install_requires=["setuptools"],
    zip_safe=True,
    maintainer="Robotics AI Team",
    maintainer_email="dev@example.com",
    description="UR5e pick & place simulation demo",
    license="MIT",
    entry_points={
        "console_scripts": [
            "pick_and_place = sim_demo.pick_and_place_node:main",
            "video_recorder = sim_demo.video_recorder_node:main",
        ],
    },
)
