import select
import sys
import termios
import tty
from typing import Optional

import rclpy
from geometry_msgs.msg import Twist
from rclpy._rclpy_pybind11 import RCLError
from rclpy.executors import ExternalShutdownException
from rclpy.node import Node


HELP = """
Swingboy keyboard teleop

  W/S : increase/decrease forward speed
  A/D : increase/decrease yaw rate
  X or Space : stop command
  Q or Ctrl-C : quit
"""


class SwingboyKeyboardTeleop(Node):
    def __init__(self):
        super().__init__("swingboy_keyboard_teleop")
        self.declare_parameter("cmd_vel_topic", "/cmd_vel")
        self.declare_parameter("publish_rate_hz", 20.0)
        self.declare_parameter("max_vx", 0.65)
        self.declare_parameter("max_wz", 0.8)
        self.declare_parameter("step_vx", 0.05)
        self.declare_parameter("step_wz", 0.10)

        self.max_vx = float(self.get_parameter("max_vx").value)
        self.max_wz = float(self.get_parameter("max_wz").value)
        self.step_vx = float(self.get_parameter("step_vx").value)
        self.step_wz = float(self.get_parameter("step_wz").value)
        self.vx = 0.0
        self.wz = 0.0
        self._last_status = ""

        self.publisher = self.create_publisher(Twist, self.get_parameter("cmd_vel_topic").value, 10)
        period = 1.0 / max(float(self.get_parameter("publish_rate_hz").value), 1.0)
        self.timer = self.create_timer(period, self.publish_command)

    def apply_key(self, key: str) -> bool:
        key = key.lower()
        if key == "w":
            self.vx = min(self.max_vx, self.vx + self.step_vx)
        elif key == "s":
            self.vx = max(-self.max_vx, self.vx - self.step_vx)
        elif key == "a":
            self.wz = min(self.max_wz, self.wz + self.step_wz)
        elif key == "d":
            self.wz = max(-self.max_wz, self.wz - self.step_wz)
        elif key in ("x", " "):
            self.vx = 0.0
            self.wz = 0.0
        elif key in ("q", "\x03"):
            return False
        self.print_status()
        return True

    def publish_command(self):
        msg = Twist()
        msg.linear.x = self.vx
        msg.angular.z = self.wz
        self.publisher.publish(msg)

    def print_status(self):
        status = f"cmd_vel: vx={self.vx:+.2f} m/s, wz={self.wz:+.2f} rad/s"
        if status != self._last_status:
            print(status)
            self._last_status = status

    def stop(self):
        self.vx = 0.0
        self.wz = 0.0
        for _ in range(3):
            self.publish_command()


def read_key(timeout_s: float) -> Optional[str]:
    ready, _, _ = select.select([sys.stdin], [], [], timeout_s)
    if not ready:
        return None
    return sys.stdin.read(1)


def main(args=None):
    rclpy.init(args=args)
    node = SwingboyKeyboardTeleop()
    old_settings = termios.tcgetattr(sys.stdin)
    print(HELP)
    node.print_status()
    try:
        tty.setcbreak(sys.stdin.fileno())
        while rclpy.ok():
            rclpy.spin_once(node, timeout_sec=0.0)
            key = read_key(0.05)
            if key is not None and not node.apply_key(key):
                break
    except (KeyboardInterrupt, ExternalShutdownException, RCLError):
        pass
    finally:
        termios.tcsetattr(sys.stdin, termios.TCSADRAIN, old_settings)
        node.stop()
        node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()


if __name__ == "__main__":
    main()
