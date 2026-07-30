from launch import LaunchDescription
from launch_ros.actions import Node
from launch.actions import TimerAction
import random
number_of_spawn = random.randint(1, 5)


def generate_launch_description():

    turtlesim=Node(
        package='turtlesim',
        executable='turtlesim_node',
        name='turtlesim',
        output='screen',
    )
    multi_spawner = Node(
        package='turtle_chaser',
        executable='multi_spawner',
        name='multi_spawner',
        output='screen',
        parameters=[{'turtle_count': number_of_spawn }]
    )
 
    nearest_chaser = Node(
        package='turtle_chaser',
        executable='nearest_chaser',
        name='nearest_chaser',
        output='screen',
    )
 
    return LaunchDescription([
        turtlesim,
        # Give turtlesim 1.5 s to start before spawner calls /spawn
        TimerAction(period=1.5, actions=[multi_spawner]),
        # Give spawner 0.5 s to publish the first /target/pose
        TimerAction(period=2.0, actions=[nearest_chaser]),
    ])
 