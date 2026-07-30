#!/usr/bin/env python3
import math
import rclpy
from rclpy.node import Node
from turtlesim.msg import Pose
from geometry_msgs.msg import Twist
from std_msgs.msg import Bool
 
 
class Chaser(Node):
    def __init__(self):
        super().__init__('chaser')
        self.turtle_pose = None
        self.target_pose = None
        self.reached = False  # prevents sending the signal multiple times
 
        self.cmd_pub = self.create_publisher(Twist, '/turtle1/cmd_vel', 10)
 
        # Tell the spawner we arrived — spawner will kill old and spawn new
        self.reached_pub = self.create_publisher(Bool, '/reached', 10)
 
        self.create_subscription(Pose, '/turtle1/pose', self.main_pose_cb, 10)
        self.create_subscription(Pose, '/target/pose', self.target_pose_cb, 10)
 
        self.create_timer(0.05, self.control_loop)
        self.get_logger().info('Chaser node started')
 
    def main_pose_cb(self, msg):
        self.turtle_pose = msg
 
    def target_pose_cb(self, msg):
        # New target arrived from spawner — reset the reached flag
        if self.target_pose is None or (
            abs(msg.x - self.target_pose.x) > 0.01 or
            abs(msg.y - self.target_pose.y) > 0.01
        ):
            self.reached = False
        self.target_pose = msg
 
    def control_loop(self):
        if self.turtle_pose is None or self.target_pose is None:
            return
 
        dx = self.target_pose.x - self.turtle_pose.x
        dy = self.target_pose.y - self.turtle_pose.y
        distance = math.sqrt(dx * dx + dy * dy)
 
        cmd = Twist()
 
        if distance < 0.6:
            # Stop the turtle
            cmd.linear.x = 0.0
            cmd.angular.z = 0.0
            self.cmd_pub.publish(cmd)
 
            # Signal the spawner only once per target
            if not self.reached:
                self.reached = True
                self.get_logger().info(
                    f'Reached target at ({self.target_pose.x:.1f}, {self.target_pose.y:.1f})'
                )
                msg = Bool()
                msg.data = True
                self.reached_pub.publish(msg)
            return
 
        # Proportional controller
        desired_angle = math.atan2(dy, dx)
        angle_error = desired_angle - self.turtle_pose.theta
 
        # Normalize to [-pi, pi]
        while angle_error > math.pi:
            angle_error -= 2.0 * math.pi
        while angle_error < -math.pi:
            angle_error += 2.0 * math.pi
 
        cmd.linear.x = min(2.0 * distance, 3.0)
        cmd.angular.z = 6.0 * angle_error
        self.cmd_pub.publish(cmd)
 
 
def main(args=None):
    rclpy.init(args=args)
    node = Chaser()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    node.destroy_node()
    rclpy.shutdown()
