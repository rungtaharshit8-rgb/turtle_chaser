from launch import LaunchDescription
from launch_ros.actions import Node
from launch.actions import TimerAction
 
 
def generate_launch_description():
    """
    Launch order:
      t=0.0s  turtlesim_node starts  (creates turtle1)
      t=1.5s  spawner starts         (waits for /spawn service, then spawns target)
      t=2.0s  chaser starts          (subscribes to poses, begins chasing)
    
    The delay ensures turtlesim is fully up before spawner tries /spawn.
    """
 
    turtlesim = Node(
        package='turtlesim',
        executable='turtlesim_node',
        name='turtlesim',
        output='screen',
    )
 
    spawner = Node(
        package='turtle_chaser',
        executable='spawner',
        name='spawner',
        output='screen',
    )
 
    chaser = Node(
        package='turtle_chaser',
        executable='chaser',
        name='chaser',
        output='screen',
    )
 
    return LaunchDescription([
        turtlesim,
        # Give turtlesim 1.5 s to start before spawner calls /spawn
        TimerAction(period=1.5, actions=[spawner]),
        # Give spawner 0.5 s to publish the first /target/pose
        TimerAction(period=2.0, actions=[chaser]),
    ])
 
