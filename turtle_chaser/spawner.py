#!/usr/bin/env python3

import random
import rclpy
from rclpy.node import Node
from turtlesim.msg import Pose
from turtlesim.srv import Spawn, Kill
from std_msgs.msg import Bool
 
 
class Spawner(Node):
    def __init__(self):
        super().__init__('spawner')
 
        self.current_target_name = None  # name of the turtle we spawned last
        self.is_spawning = False          # guard against double-spawns
 
        # Publish target pose so chaser knows where to go
        self.target_pub = self.create_publisher(Pose, '/target/pose', 10)
 
        # Listen for the chaser's "I arrived" signal
        self.create_subscription(Bool, '/reached', self.on_reached, 10)
 
        # Service clients
        self.spawn_client = self.create_client(Spawn, '/spawn')
        self.kill_client = self.create_client(Kill, '/kill')
 
        # Wait for turtlesim to be ready
        self.get_logger().info('Waiting for turtlesim services...')
        self.spawn_client.wait_for_service()
        self.kill_client.wait_for_service()
 
        # Spawn the first target immediately
        self.spawn_new_turtle()
 
    # ── called by chaser when it reaches the target ──────────────────────────
    def on_reached(self, msg: Bool):
        if msg.data and not self.is_spawning:
            self.get_logger().info('Chaser reached target — killing old, spawning new...')
            self.kill_then_spawn()
 
    # ── kill old turtle, then spawn a new one ────────────────────────────────
    def kill_then_spawn(self):
        self.is_spawning = True
 
        if self.current_target_name is not None:
            req = Kill.Request()
            req.name = self.current_target_name
            future = self.kill_client.call_async(req)
            future.add_done_callback(self._on_kill_done)
        else:
            self.spawn_new_turtle()
 
    def _on_kill_done(self, future):
        try:
            future.result()
            self.get_logger().info(f'Killed {self.current_target_name}')
        except Exception as e:
            self.get_logger().warn(f'Kill failed (continuing anyway): {e}')
        self.spawn_new_turtle()
 
    # ── do the actual spawn ───────────────────────────────────────────────────
    def spawn_new_turtle(self):
        x = random.uniform(1.0, 10.0)
        y = random.uniform(1.0, 10.0)
        theta = random.uniform(-3.14, 3.14)
 
        req = Spawn.Request()
        req.x = x
        req.y = y
        req.theta = theta
        req.name = 'target'  # always named 'target' so /target/pose works cleanly
 
        future = self.spawn_client.call_async(req)
        future.add_done_callback(lambda f: self._on_spawn_done(f, x, y, theta))
 
    def _on_spawn_done(self, future, x, y, theta):
        try:
            result = future.result()
            self.current_target_name = result.name
            self.get_logger().info(
                f'Spawned "{result.name}" at ({x:.2f}, {y:.2f})'
            )
 
            # Publish the target pose so the chaser starts moving
            pose = Pose()
            pose.x = x
            pose.y = y
            pose.theta = theta
            self.target_pub.publish(pose)
 
            # Keep publishing so the chaser always has the latest pose
            # (one-shot publish can be missed if chaser sub isn't ready yet)
            self.create_timer(0.1, lambda: self.target_pub.publish(pose))
 
        except Exception as e:
            self.get_logger().error(f'Spawn failed: {e}')
        finally:
            self.is_spawning = False
 
 
def main(args=None):
    rclpy.init(args=args)
    node = Spawner()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    node.destroy_node()
    rclpy.shutdown()
 
 
if __name__ == '__main__':
    main()
