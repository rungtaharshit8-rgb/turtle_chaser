#!/usr/bin/env python3
import json
import random
import rclpy
from rclpy.node import Node
from turtlesim.msg import Pose
from turtlesim.srv import Spawn, Kill
from std_msgs.msg import String  # ← Changed from Bool to String

number_of_spawn = random.randint(1, 5)

class multi_spawner(Node):
    def __init__(self):
        super().__init__('multi_spawner')  # Fixed spelling: 'multi_sawner' -> 'multi_spawner'

        # ── Config ────────────────────────────────────────────
        self.declare_parameter('turtle_count', number_of_spawn)  
        self.turtle_count = self.get_parameter('turtle_count').value

        # ── State ─────────────────────────────────────────────
        self.targets = {}               # { name: (x, y, theta) }
        self.is_spawning = False        # guard against double-spawns
        self.name_counter = 0           # always increasing, ensures unique names

        # ── Publishers ────────────────────────────────────────
        # Send all active targets as a serialized JSON dictionary string
        self.all_targets_pub = self.create_publisher(String, '/all_targets', 10)

        # ── Subscribers ───────────────────────────────────────
        # Listen for the specific NAME string of the reached turtle
        self.create_subscription(String, '/reached', self.on_reached, 10)

        # ── Service clients ───────────────────────────────────
        self.spawn_client = self.create_client(Spawn, '/spawn')
        self.kill_client = self.create_client(Kill, '/kill')

        self.get_logger().info('Waiting for turtlesim services...')
        self.spawn_client.wait_for_service()
        self.kill_client.wait_for_service()
        self.get_logger().info('Services ready!')

        # ── Spawn initial batch ───────────────────────────────
        self.spawn_initial_batch()

        # ── Keep publishing active targets matrix ─────────────
        self.create_timer(0.1, self.publish_all_targets)

    # ─────────────────────────────────────────────────────────────────────────
    def spawn_initial_batch(self):
        self.get_logger().info(f'Spawning {self.turtle_count} targets...')
        for _ in range(self.turtle_count):
            self._do_spawn()

    # ─────────────────────────────────────────────────────────────────────────
    def on_reached(self, msg: String):
        """Processes the exact name of the target caught by the chaser."""
        name_to_kill = msg.data
        if not name_to_kill or self.is_spawning:
            return

        if name_to_kill in self.targets:
            self.is_spawning = True
            del self.targets[name_to_kill]  # Erase immediately from local state

            self.get_logger().info(f'Chaser reached "{name_to_kill}" — killing it!')
            
            req = Kill.Request()
            req.name = name_to_kill
            future = self.kill_client.call_async(req)
            future.add_done_callback(self._on_kill_done)

    # ─────────────────────────────────────────────────────────────────────────
    def _on_kill_done(self, future):
        try:
            future.result()
            self.get_logger().info('Kill successful')
        except Exception as e:
            self.get_logger().warn(f'Kill failed: {e}')

        # Spawn a brand new turtle elsewhere to replace the dead one
        self._do_spawn()

    # ─────────────────────────────────────────────────────────────────────────
    def _do_spawn(self):
        x = random.uniform(1.0, 10.0)
        y = random.uniform(1.0, 10.0)
        theta = random.uniform(-3.14, 3.14)

        name = f'target_{self.name_counter}'
        self.name_counter += 1

        req = Spawn.Request(x=x, y=y, theta=theta, name=name)
        future = self.spawn_client.call_async(req)
        future.add_done_callback(
            lambda f, sx=x, sy=y, st=theta: self._on_spawn_done(f, sx, sy, st)
        )

    def _on_spawn_done(self, future, x, y, theta):
        try:
            result = future.result()
            self.targets[result.name] = (x, y, theta)
            self.get_logger().info(f'Spawned "{result.name}" at ({x:.2f}, {y:.2f})')
        except Exception as e:
            self.get_logger().error(f'Spawn failed: {e}')
        finally:
            self.is_spawning = False

    # ─────────────────────────────────────────────────────────────────────────
    def publish_all_targets(self):
        """Dumps dictionary tracking maps directly into JSON string packets"""
        if not self.targets:
            return
        
        msg = String()
        msg.data = json.dumps(self.targets)
        self.all_targets_pub.publish(msg)


def main(args=None):
    rclpy.init(args=args)
    node = multi_spawner()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    node.destroy_node()
    rclpy.shutdown()


if __name__ == '__main__':
    main()