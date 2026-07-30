#!/usr/bin/env python3
"""
nearest_chaser.py
=================
Subscribes to /all_targets (JSON from multi_spawner).
Always drives turtle1 to the NEAREST turtle using Euclidean distance.
When reached, publishes the turtle NAME on /reached (String).
"""
import json
import math
import rclpy
from rclpy.node import Node
from turtlesim.msg import Pose
from geometry_msgs.msg import Twist
from std_msgs.msg import String


class nearest_chaser(Node):
    def __init__(self):
        super().__init__('chaser')

        # ── Parameters ────────────────────────────────────────
        self.declare_parameter('linear_kp',      2.0)
        self.declare_parameter('angular_kp',     6.0)
        self.declare_parameter('goal_tolerance', 0.6)

        # ── State ─────────────────────────────────────────────
        self.turtle_pose   = None   # turtle1 current pose
        self.targets       = {}     # {name: (x, y, theta)}  from spawner
        self.current_name  = None   # name of turtle we are chasing right now
        self.reached       = False  # prevent duplicate signals

        # ── Subscribers ───────────────────────────────────────
        self.create_subscription(
            Pose,   '/turtle1/pose',  self._pose_cb,    10)
        self.create_subscription(
            String, '/all_targets',   self._targets_cb, 10)

        # ── Publishers ────────────────────────────────────────
        self.cmd_pub     = self.create_publisher(Twist,  '/turtle1/cmd_vel', 10)
        self.reached_pub = self.create_publisher(String, '/reached',         10)

        # ── Control loop 20 Hz ────────────────────────────────
        self.create_timer(0.05, self._control_loop)
        self.get_logger().info('Nearest_Chaser started!')

    # ─────────────────────────────────────────────────────────────────────────
    def _pose_cb(self, msg: Pose):
        self.turtle_pose = msg

    def _targets_cb(self, msg: String):
        try:
            data = json.loads(msg.data)
            self.targets = {k: tuple(v) for k, v in data.items()}

            # If current target was killed by spawner, pick a new nearest
            if self.current_name not in self.targets:
                self.current_name = None
                self.reached = False

        except Exception as e:
            self.get_logger().error(f'Bad /all_targets msg: {e}')

    # ─────────────────────────────────────────────────────────────────────────
    def _nearest_target(self):
        """Return name of the closest turtle to turtle1."""
        if not self.targets or self.turtle_pose is None:
            return None

        return min(
            self.targets,
            key=lambda n: math.dist(
                (self.turtle_pose.x, self.turtle_pose.y),
                (self.targets[n][0], self.targets[n][1])
            )
        )

    # ─────────────────────────────────────────────────────────────────────────
    def _control_loop(self):
        if self.turtle_pose is None or not self.targets:
            return

        # Always re-evaluate nearest (targets can change after a kill+spawn)
        nearest = self._nearest_target()

        # Switch target if a closer one appeared
        if nearest != self.current_name:
            self.current_name = nearest
            self.reached = False
            self.get_logger().info(f'Nearest target → "{self.current_name}"')

        if self.current_name is None:
            return

        tx, ty, _ = self.targets[self.current_name]
        dx = tx - self.turtle_pose.x
        dy = ty - self.turtle_pose.y
        distance = math.sqrt(dx * dx + dy * dy)

        tolerance  = self.get_parameter('goal_tolerance').value
        kp_lin     = self.get_parameter('linear_kp').value
        kp_ang     = self.get_parameter('angular_kp').value

        cmd = Twist()

        if distance < tolerance:
            # ── Reached! ──────────────────────────────────────
            cmd.linear.x  = 0.0
            cmd.angular.z = 0.0
            self.cmd_pub.publish(cmd)

            if not self.reached:
                self.reached = True
                self.get_logger().info(
                    f'Reached "{self.current_name}" at ({tx:.1f}, {ty:.1f})'
                )
                # Tell spawner the NAME of the turtle to kill
                out = String()
                out.data = self.current_name
                self.reached_pub.publish(out)

                # Clear so next loop picks a new nearest
                self.current_name = None

        else:
            # ── Drive toward target ───────────────────────────
            self.reached = False

            desired_angle = math.atan2(dy, dx)
            angle_error   = desired_angle - self.turtle_pose.theta
            # Normalize to [-π, π]
            angle_error   = math.atan2(math.sin(angle_error), math.cos(angle_error))

            cmd.linear.x  = min(kp_lin * distance, 3.0)
            cmd.angular.z = max(min(kp_ang * angle_error, 3.0), -3.0)
            self.cmd_pub.publish(cmd)


def main(args=None):
    rclpy.init(args=args)
    node = nearest_chaser()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    node.destroy_node()
    rclpy.shutdown()


if __name__ == '__main__':
    main()