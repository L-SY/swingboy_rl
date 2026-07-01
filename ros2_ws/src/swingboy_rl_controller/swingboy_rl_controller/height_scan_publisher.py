import math
from dataclasses import dataclass
from typing import List, Optional, Sequence

import numpy as np
import rclpy
from nav_msgs.msg import Odometry
from rclpy._rclpy_pybind11 import RCLError
from rclpy.executors import ExternalShutdownException
from rclpy.node import Node
from std_msgs.msg import Float32MultiArray


def rotation_matrix(roll: float, pitch: float, yaw: float) -> np.ndarray:
    cr, sr = math.cos(roll), math.sin(roll)
    cp, sp = math.cos(pitch), math.sin(pitch)
    cy, sy = math.cos(yaw), math.sin(yaw)
    rx = np.array([[1.0, 0.0, 0.0], [0.0, cr, -sr], [0.0, sr, cr]], dtype=np.float64)
    ry = np.array([[cp, 0.0, sp], [0.0, 1.0, 0.0], [-sp, 0.0, cp]], dtype=np.float64)
    rz = np.array([[cy, -sy, 0.0], [sy, cy, 0.0], [0.0, 0.0, 1.0]], dtype=np.float64)
    return rz @ ry @ rx


def yaw_from_quat_xyzw(x: float, y: float, z: float, w: float) -> float:
    return math.atan2(2.0 * (w * z + x * y), 1.0 - 2.0 * (y * y + z * z))


@dataclass
class TerrainBox:
    center: np.ndarray
    size: np.ndarray
    rotation: np.ndarray

    @classmethod
    def from_pose(cls, pose: Sequence[float], size: Sequence[float]):
        x, y, z, roll, pitch, yaw = pose
        return cls(
            center=np.array([x, y, z], dtype=np.float64),
            size=np.array(size, dtype=np.float64),
            rotation=rotation_matrix(roll, pitch, yaw),
        )

    def top_height_at(self, x: float, y: float) -> Optional[float]:
        top_center = self.center + self.rotation @ np.array([0.0, 0.0, self.size[2] * 0.5])
        normal = self.rotation @ np.array([0.0, 0.0, 1.0])
        if abs(normal[2]) < 1.0e-6:
            return None

        z = top_center[2] - (normal[0] * (x - top_center[0]) + normal[1] * (y - top_center[1])) / normal[2]
        local = self.rotation.T @ (np.array([x, y, z], dtype=np.float64) - self.center)
        margin = 1.0e-6
        if abs(local[0]) <= self.size[0] * 0.5 + margin and abs(local[1]) <= self.size[1] * 0.5 + margin:
            return float(z)
        return None


def rough_test_terrain() -> List[TerrainBox]:
    return [
        TerrainBox.from_pose((3.0, 0.0, -0.04, 0.0, 0.0, 0.0), (14.0, 8.0, 0.08)),
        TerrainBox.from_pose((1.2, 0.0, 0.05, 0.0, 0.12, 0.0), (1.4, 2.5, 0.04)),
        TerrainBox.from_pose((2.7, 0.0, 0.05, 0.0, -0.12, 0.0), (1.4, 2.5, 0.04)),
        TerrainBox.from_pose((4.3, 0.0, 0.02, 0.0, 0.0, 0.0), (0.18, 0.55, 0.025)),
        TerrainBox.from_pose((4.62, 0.45, 0.032, 0.0, 0.0, 0.1), (0.22, 0.38, 0.045)),
        TerrainBox.from_pose((5.0, -0.35, 0.03, 0.0, 0.0, -0.2), (0.28, 0.30, 0.035)),
        TerrainBox.from_pose((6.0, 0.0, 0.12, 0.0, 0.20, 0.0), (1.8, 3.0, 0.05)),
    ]


class SwingboyHeightScanPublisher(Node):
    """Publishes IsaacLab-style height scan observations for the rough Gazebo test world."""

    def __init__(self):
        super().__init__("swingboy_height_scan_publisher")

        self.declare_parameter("odom_topic", "/swingboy/odom")
        self.declare_parameter("height_scan_topic", "/swingboy/height_scan")
        self.declare_parameter("publish_rate_hz", 50.0)
        self.declare_parameter("grid_size_x", 1.2)
        self.declare_parameter("grid_size_y", 0.8)
        self.declare_parameter("resolution", 0.08)
        self.declare_parameter("scan_offset", 0.5)
        self.declare_parameter("clip_min", -1.0)
        self.declare_parameter("clip_max", 1.0)

        self.scan_offset = float(self.get_parameter("scan_offset").value)
        self.clip_min = float(self.get_parameter("clip_min").value)
        self.clip_max = float(self.get_parameter("clip_max").value)
        self.terrain = rough_test_terrain()
        self.base_position: Optional[np.ndarray] = None
        self.base_yaw = 0.0

        self.scan_points = self._make_scan_points(
            float(self.get_parameter("grid_size_x").value),
            float(self.get_parameter("grid_size_y").value),
            float(self.get_parameter("resolution").value),
        )

        self.publisher = self.create_publisher(
            Float32MultiArray,
            self.get_parameter("height_scan_topic").value,
            10,
        )
        self.create_subscription(Odometry, self.get_parameter("odom_topic").value, self.on_odom, 10)

        period = 1.0 / max(float(self.get_parameter("publish_rate_hz").value), 1.0)
        self.timer = self.create_timer(period, self.publish_scan)
        self.get_logger().info(f"Publishing {self.scan_points.shape[0]} height-scan points for rough_test.sdf")

    def _make_scan_points(self, size_x: float, size_y: float, resolution: float) -> np.ndarray:
        count_x = int(round(size_x / resolution)) + 1
        count_y = int(round(size_y / resolution)) + 1
        xs = np.linspace(-size_x * 0.5, size_x * 0.5, count_x)
        ys = np.linspace(-size_y * 0.5, size_y * 0.5, count_y)
        return np.array([[x, y] for y in ys for x in xs], dtype=np.float64)

    def on_odom(self, msg: Odometry):
        p = msg.pose.pose.position
        q = msg.pose.pose.orientation
        self.base_position = np.array([p.x, p.y, p.z], dtype=np.float64)
        self.base_yaw = yaw_from_quat_xyzw(q.x, q.y, q.z, q.w)

    def terrain_height(self, x: float, y: float) -> float:
        height = 0.0
        for terrain_box in self.terrain:
            box_height = terrain_box.top_height_at(x, y)
            if box_height is not None:
                height = max(height, box_height)
        return height

    def publish_scan(self):
        if self.base_position is None:
            return

        cy = math.cos(self.base_yaw)
        sy = math.sin(self.base_yaw)
        rot2 = np.array([[cy, -sy], [sy, cy]], dtype=np.float64)
        world_xy = self.scan_points @ rot2.T + self.base_position[:2]
        values = [
            self.base_position[2] - self.terrain_height(float(x), float(y)) - self.scan_offset
            for x, y in world_xy
        ]
        msg = Float32MultiArray()
        msg.data = [float(v) for v in np.clip(values, self.clip_min, self.clip_max)]
        self.publisher.publish(msg)


def main(args: Optional[List[str]] = None):
    rclpy.init(args=args)
    node = SwingboyHeightScanPublisher()
    try:
        rclpy.spin(node)
    except (KeyboardInterrupt, ExternalShutdownException, RCLError):
        pass
    finally:
        node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()


if __name__ == "__main__":
    main()
