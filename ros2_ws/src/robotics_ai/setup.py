from setuptools import setup, find_packages
import os
from glob import glob

package_name = 'robotics_ai'

setup(
    name=package_name,
    version='0.1.0',
    packages=find_packages(exclude=['test']),
    data_files=[
        ('share/ament_index/resource_index/packages', ['resource/' + package_name]),
        ('share/' + package_name, ['package.xml']),
        (os.path.join('share', package_name, 'launch'), glob('launch/*.py')),
        (os.path.join('share', package_name, 'config'), glob('config/*.yaml')),
    ],
    install_requires=['setuptools'],
    zip_safe=True,
    maintainer='tokuda',
    maintainer_email='sho24.noubeau@gmail.com',
    description='Robotics AI package with deep learning and computer vision',
    license='MIT',
    tests_require=['pytest'],
    entry_points={
        'console_scripts': [
            'perception_node = robotics_ai.nodes.perception_node:main',
            'planning_node = robotics_ai.nodes.planning_node:main',
            'control_node = robotics_ai.nodes.control_node:main',
        ],
    },
)
