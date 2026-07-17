import math
import os
import time
from typing import Dict, Iterable, List, Optional, Sequence, Tuple

import numpy as np
import rclpy
from geometry_msgs.msg import Twist
from nav_msgs.msg import Odometry
from rclpy._rclpy_pybind11 import RCLError
from rclpy.executors import ExternalShutdownException
from rclpy.node import Node
from sensor_msgs.msg import Imu, JointState
from std_msgs.msg import Float32MultiArray, Float64MultiArray


HIP_LOWER_LIMIT = 0.0
HIP_UPPER_LIMIT = math.radians(130.0)
HIP_COMMAND_UPPER_LIMIT = HIP_UPPER_LIMIT - 1.0e-4
KNEE_LOWER_LIMIT = math.radians(5.0)
KNEE_UPPER_LIMIT = math.radians(290.0)
STAND_KNEE_POSITION = math.radians(35.3)
DEFAULT_LEG_POSITIONS = [HIP_UPPER_LIMIT, KNEE_LOWER_LIMIT, HIP_UPPER_LIMIT, KNEE_LOWER_LIMIT]
ACTION_LEG_POSITIONS = [HIP_COMMAND_UPPER_LIMIT, STAND_KNEE_POSITION, HIP_COMMAND_UPPER_LIMIT, STAND_KNEE_POSITION]
LEG_ACTION_SCALES = [0.18, 1.0, 0.18, 1.0]
WHEEL_ACTION_SCALES = [12.0, -12.0]
LEG_JOINT_LOWER_LIMITS = [HIP_LOWER_LIMIT, KNEE_LOWER_LIMIT, HIP_LOWER_LIMIT, KNEE_LOWER_LIMIT]
LEG_JOINT_UPPER_LIMITS = [HIP_COMMAND_UPPER_LIMIT, KNEE_UPPER_LIMIT, HIP_COMMAND_UPPER_LIMIT, KNEE_UPPER_LIMIT]


def quat_conjugate(q: Sequence[float]) -> np.ndarray:
    return np.array([q[0], -q[1], -q[2], -q[3]], dtype=np.float32)


def quat_rotate(q: Sequence[float], v: Sequence[float]) -> np.ndarray:
    w, x, y, z = q
    qv = np.array([x, y, z], dtype=np.float32)
    vec = np.array(v, dtype=np.float32)
    uv = np.cross(qv, vec)
    uuv = np.cross(qv, uv)
    return vec + 2.0 * (w * uv + uuv)


def normalize_quat_xyzw(x: float, y: float, z: float, w: float) -> np.ndarray:
    q = np.array([w, x, y, z], dtype=np.float32)
    norm = float(np.linalg.norm(q))
    if norm < 1.0e-6:
        return np.array([1.0, 0.0, 0.0, 0.0], dtype=np.float32)
    return q / norm


class SuppressNativeStderr:
    """Temporarily silences native library writes to stderr during ONNX Runtime startup."""

    def __enter__(self):
        self._stderr_fd = os.dup(2)
        self._devnull_fd = os.open(os.devnull, os.O_WRONLY)
        os.dup2(self._devnull_fd, 2)
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        os.dup2(self._stderr_fd, 2)
        os.close(self._stderr_fd)
        os.close(self._devnull_fd)
        return False


class SwingboyRlController(Node):
    """Runs an IsaacLab-exported ONNX policy and publishes ros2_control commands."""

    def __init__(self):
        super().__init__("swingboy_rl_controller")

        self.declare_parameter("policy_path", "")
        self.declare_parameter("publish_rate_hz", 50.0)
        self.declare_parameter("leg_action_scale", LEG_ACTION_SCALES)
        self.declare_parameter("wheel_action_scale", WHEEL_ACTION_SCALES)
        self.declare_parameter("leg_action_clip", 1.0)
        self.declare_parameter("wheel_action_clip", 1.0)
        self.declare_parameter("action_filter_alpha", 0.35)
        self.declare_parameter("leg_target_rate_limit", 4.0)
        self.declare_parameter("height_scan_size", 176)
        self.declare_parameter("height_scan_value", -0.2)
        self.declare_parameter("cmd_lin_x_limit", 0.65)
        self.declare_parameter("cmd_yaw_limit", 0.8)
        self.declare_parameter("warmup_duration_s", 3.0)
        self.declare_parameter("leg_joint_order", ["left_hip", "left_knee", "right_hip", "right_knee"])
        self.declare_parameter("wheel_joint_order", ["left_wheel", "right_wheel"])
        self.declare_parameter(
            "observation_joint_order",
            ["left_hip", "right_hip", "left_knee", "right_knee", "left_wheel", "right_wheel"],
        )
        self.declare_parameter("default_leg_positions", DEFAULT_LEG_POSITIONS)
        self.declare_parameter("action_leg_positions", ACTION_LEG_POSITIONS)
        self.declare_parameter("leg_joint_lower_limits", LEG_JOINT_LOWER_LIMITS)
        self.declare_parameter("leg_joint_upper_limits", LEG_JOINT_UPPER_LIMITS)
        self.declare_parameter("leg_command_topic", "/swingboy_leg_controller/commands")
        self.declare_parameter("wheel_command_topic", "/swingboy_wheel_controller/commands")

        self.policy_path = self.get_parameter("policy_path").value
        self.rate_hz = float(self.get_parameter("publish_rate_hz").value)
        self.leg_action_clip = max(0.0, float(self.get_parameter("leg_action_clip").value))
        self.wheel_action_clip = max(0.0, float(self.get_parameter("wheel_action_clip").value))
        self.action_filter_alpha = float(np.clip(float(self.get_parameter("action_filter_alpha").value), 0.0, 1.0))
        self.leg_target_rate_limit = max(0.0, float(self.get_parameter("leg_target_rate_limit").value))
        self.height_scan_size = int(self.get_parameter("height_scan_size").value)
        self.height_scan_value = float(self.get_parameter("height_scan_value").value)
        self.cmd_lin_x_limit = float(self.get_parameter("cmd_lin_x_limit").value)
        self.cmd_yaw_limit = float(self.get_parameter("cmd_yaw_limit").value)
        self.warmup_duration_s = max(0.0, float(self.get_parameter("warmup_duration_s").value))
        self.leg_joint_order = list(self.get_parameter("leg_joint_order").value)
        self.wheel_joint_order = list(self.get_parameter("wheel_joint_order").value)
        self.observation_joint_order = list(self.get_parameter("observation_joint_order").value)
        self.leg_action_scale = self._float_array_or_scalar_parameter("leg_action_scale", len(self.leg_joint_order))
        self.wheel_action_scale = self._float_array_or_scalar_parameter(
            "wheel_action_scale", len(self.wheel_joint_order)
        )
        self.default_leg_positions = self._float_array_parameter("default_leg_positions", len(self.leg_joint_order))
        self.action_leg_positions = self._float_array_parameter("action_leg_positions", len(self.leg_joint_order))
        self.leg_joint_lower_limits = self._float_array_parameter("leg_joint_lower_limits", len(self.leg_joint_order))
        self.leg_joint_upper_limits = self._float_array_parameter("leg_joint_upper_limits", len(self.leg_joint_order))
        self.default_joint_positions = self._default_joint_position_map()

        self.leg_pub = self.create_publisher(
            Float64MultiArray,
            self.get_parameter("leg_command_topic").value,
            10,
        )
        self.wheel_pub = self.create_publisher(
            Float64MultiArray,
            self.get_parameter("wheel_command_topic").value,
            10,
        )

        self.create_subscription(JointState, "/joint_states", self.on_joint_state, 20)
        self.create_subscription(Twist, "/cmd_vel", self.on_cmd_vel, 10)
        self.create_subscription(Odometry, "/swingboy/odom", self.on_odom, 10)
        self.create_subscription(Imu, "/swingboy/imu", self.on_imu, 10)
        self.create_subscription(Float32MultiArray, "/swingboy/height_scan", self.on_height_scan, 10)

        self.joint_pos: Dict[str, float] = {}
        self.joint_vel: Dict[str, float] = {}
        self.cmd = np.zeros(3, dtype=np.float32)
        self.base_quat_wxyz = np.array([1.0, 0.0, 0.0, 0.0], dtype=np.float32)
        self.base_lin_vel_body = np.zeros(3, dtype=np.float32)
        self.base_ang_vel_body = np.zeros(3, dtype=np.float32)
        self.projected_gravity = np.array([0.0, 0.0, -1.0], dtype=np.float32)
        self.previous_action = np.zeros(6, dtype=np.float32)
        self.height_scan = np.full(self.height_scan_size, self.height_scan_value, dtype=np.float32)
        self.start_monotonic = time.monotonic()
        self.warmup_start_leg_positions: Optional[np.ndarray] = None
        self.last_leg_targets: Optional[np.ndarray] = None
        self.last_command_monotonic: Optional[float] = None

        self.session = None
        self.input_name = None
        self.output_name = None
        self.expected_observation_size = 206
        self._load_policy()
        self.observation_history = None

        period = 1.0 / max(self.rate_hz, 1.0)
        self.timer = self.create_timer(period, self.update)

    def _float_array_parameter(self, name: str, expected_size: int) -> np.ndarray:
        values = np.array(self.get_parameter(name).value, dtype=np.float32)
        if values.size != expected_size:
            raise ValueError(f"{name} must contain {expected_size} values, got {values.size}")
        return values

    def _float_array_or_scalar_parameter(self, name: str, expected_size: int) -> np.ndarray:
        values = np.array(self.get_parameter(name).value, dtype=np.float32).reshape(-1)
        if values.size == 1:
            return np.full(expected_size, float(values[0]), dtype=np.float32)
        if values.size != expected_size:
            raise ValueError(f"{name} must contain either 1 or {expected_size} values, got {values.size}")
        return values

    def _default_joint_position_map(self) -> Dict[str, float]:
        defaults = {
            self.leg_joint_order[0]: float(self.default_leg_positions[0]),
            self.leg_joint_order[1]: float(self.default_leg_positions[1]),
            self.leg_joint_order[2]: float(self.default_leg_positions[2]),
            self.leg_joint_order[3]: float(self.default_leg_positions[3]),
            self.wheel_joint_order[0]: 0.0,
            self.wheel_joint_order[1]: 0.0,
        }
        return defaults

    def _resolve_policy_path(self) -> str:
        if not self.policy_path:
            return ""
        policy_path = os.path.expanduser(str(self.policy_path))
        if os.path.isdir(policy_path):
            for name in (
                "v0.1.0-legacy/swingboy_track_latest.onnx",
                "v0.1.0-legacy/swingboy_rough_latest.onnx",
                "swingboy_track_latest.onnx",
                "swingboy_rough_latest.onnx",
                "policy.onnx",
            ):
                candidate = os.path.join(policy_path, name)
                if os.path.isfile(candidate):
                    self.get_logger().info(f"Resolved policy directory to ONNX file: {candidate}")
                    return candidate
        return policy_path

    def _load_policy(self):
        self.policy_path = self._resolve_policy_path()
        if not self.policy_path:
            self.get_logger().warning("No policy_path set; holding default stand pose with zero wheel velocity.")
            return
        if not os.path.isfile(self.policy_path):
            self.get_logger().error(f"Policy path does not exist: {self.policy_path}")
            return
        try:
            with SuppressNativeStderr():
                import onnxruntime as ort

                self.session = ort.InferenceSession(self.policy_path, providers=["CPUExecutionProvider"])
        except ImportError:
            self.get_logger().error(
                "onnxruntime is not installed for the ROS Python environment. "
                "Install it with: python3 -m pip install --user onnxruntime"
            )
            return
        except Exception as exc:
            self.get_logger().error(f"Failed to load ONNX policy {self.policy_path}: {exc}")
            return

        self.input_name = self.session.get_inputs()[0].name
        self.output_name = self.session.get_outputs()[0].name
        self.expected_observation_size = self._policy_observation_size()
        self.get_logger().info(f"Loaded ONNX policy: {self.policy_path}")
        self.get_logger().info(
            f"Policy observation size: {self.expected_observation_size} ({self._observation_layout_name()})"
        )

    def _policy_observation_size(self) -> int:
        input_shape = self.session.get_inputs()[0].shape
        for dim in reversed(input_shape):
            if isinstance(dim, int) and dim > 1:
                return dim
        self.get_logger().warning(
            f"Could not infer ONNX observation size from input shape {input_shape}; using 206-dim layout."
        )
        return 206

    def _observation_layout_name(self) -> str:
        if self.expected_observation_size == 206:
            return "base linear velocity + height scan"
        if self.expected_observation_size == 30:
            return "base linear velocity, no height scan"
        if self.expected_observation_size == 27:
            return "no base linear velocity, no height scan"
        if self.expected_observation_size == 108:
            return "4-frame history, no base linear velocity, no height scan"
        return "unknown layout"

    def on_joint_state(self, msg: JointState):
        for index, name in enumerate(msg.name):
            if index < len(msg.position):
                self.joint_pos[name] = msg.position[index]
            if index < len(msg.velocity):
                self.joint_vel[name] = msg.velocity[index]
        if self.warmup_start_leg_positions is None and all(name in self.joint_pos for name in self.leg_joint_order):
            # Gazebo may publish one stale all-zero joint-state frame while applying ros2_control initial values.
            # Deployment starts from the calibrated pose, so warmup must hold that pose instead of replaying it.
            self.warmup_start_leg_positions = self.default_leg_positions.copy()
            self.start_monotonic = time.monotonic()

    def on_cmd_vel(self, msg: Twist):
        self.cmd[0] = float(np.clip(msg.linear.x, -self.cmd_lin_x_limit, self.cmd_lin_x_limit))
        self.cmd[1] = 0.0
        self.cmd[2] = float(np.clip(msg.angular.z, -self.cmd_yaw_limit, self.cmd_yaw_limit))

    def on_odom(self, msg: Odometry):
        q = msg.pose.pose.orientation
        self.base_quat_wxyz = normalize_quat_xyzw(q.x, q.y, q.z, q.w)
        inv_q = quat_conjugate(self.base_quat_wxyz)
        lin_world = [msg.twist.twist.linear.x, msg.twist.twist.linear.y, msg.twist.twist.linear.z]
        ang_world = [msg.twist.twist.angular.x, msg.twist.twist.angular.y, msg.twist.twist.angular.z]
        self.base_lin_vel_body = quat_rotate(inv_q, lin_world)
        self.base_ang_vel_body = quat_rotate(inv_q, ang_world)
        self.projected_gravity = quat_rotate(inv_q, [0.0, 0.0, -1.0])

    def on_imu(self, msg: Imu):
        q = msg.orientation
        if not any(math.isnan(v) for v in [q.x, q.y, q.z, q.w]) and abs(q.w) + abs(q.x) + abs(q.y) + abs(q.z) > 0.0:
            self.base_quat_wxyz = normalize_quat_xyzw(q.x, q.y, q.z, q.w)
            inv_q = quat_conjugate(self.base_quat_wxyz)
            self.projected_gravity = quat_rotate(inv_q, [0.0, 0.0, -1.0])
        self.base_ang_vel_body = np.array(
            [msg.angular_velocity.x, msg.angular_velocity.y, msg.angular_velocity.z],
            dtype=np.float32,
        )

    def on_height_scan(self, msg: Float32MultiArray):
        data = np.array(msg.data, dtype=np.float32)
        if data.size >= self.height_scan_size:
            self.height_scan = data[: self.height_scan_size]
        else:
            padded = np.full(self.height_scan_size, self.height_scan_value, dtype=np.float32)
            padded[: data.size] = data
            self.height_scan = padded

    def joint_vector(self, source: Dict[str, float], default_value: float = 0.0) -> np.ndarray:
        return np.array([source.get(name, default_value) for name in self.observation_joint_order], dtype=np.float32)

    def default_joint_vector(self) -> np.ndarray:
        return np.array([self.default_joint_positions.get(name, 0.0) for name in self.observation_joint_order], dtype=np.float32)

    def build_observation(self) -> np.ndarray:
        joint_pos = self.joint_vector(self.joint_pos) - self.default_joint_vector()
        joint_vel = self.joint_vector(self.joint_vel)
        if self.expected_observation_size in (27, 108):
            terms = [
                self.base_ang_vel_body,
                self.projected_gravity,
                self.cmd,
                joint_pos,
                joint_vel,
                self.previous_action,
            ]
        elif self.expected_observation_size == 30:
            terms = [
                self.base_lin_vel_body,
                self.base_ang_vel_body,
                self.projected_gravity,
                self.cmd,
                joint_pos,
                joint_vel,
                self.previous_action,
            ]
        else:
            terms = [
                self.base_lin_vel_body,
                self.base_ang_vel_body,
                self.projected_gravity,
                self.cmd,
                joint_pos,
                joint_vel,
                self.previous_action,
                self.height_scan,
            ]
        if self.expected_observation_size == 108:
            if self.observation_history is None:
                self.observation_history = [
                    [np.array(term, dtype=np.float32, copy=True) for _ in range(4)] for term in terms
                ]
            else:
                for history, term in zip(self.observation_history, terms):
                    history.pop(0)
                    history.append(np.array(term, dtype=np.float32, copy=True))
            obs = np.concatenate(
                [np.concatenate(history) for history in self.observation_history]
            ).astype(np.float32)
        else:
            obs = np.concatenate(terms).astype(np.float32)
        if obs.shape[0] != self.expected_observation_size:
            raise RuntimeError(
                f"Unexpected observation size {obs.shape[0]}, expected {self.expected_observation_size} "
                f"for {self._observation_layout_name()}"
            )
        return obs

    def infer_action(self, obs: np.ndarray) -> np.ndarray:
        if self.session is None:
            return np.zeros(6, dtype=np.float32)
        action = self.session.run([self.output_name], {self.input_name: obs.reshape(1, -1)})[0]
        action = np.asarray(action, dtype=np.float32).reshape(-1)
        if action.shape[0] != 6:
            self.get_logger().error(f"Policy returned {action.shape[0]} actions, expected 6")
            return np.zeros(6, dtype=np.float32)
        return np.clip(action, -10.0, 10.0)

    def filter_action(self, action: np.ndarray) -> np.ndarray:
        clipped = action.copy()
        clipped[:4] = np.clip(clipped[:4], -self.leg_action_clip, self.leg_action_clip)
        clipped[4:6] = np.clip(clipped[4:6], -self.wheel_action_clip, self.wheel_action_clip)
        return (1.0 - self.action_filter_alpha) * self.previous_action + self.action_filter_alpha * clipped

    def publish_raw_commands(self, leg_targets: np.ndarray, wheel_targets: np.ndarray):
        leg_targets = np.clip(leg_targets, self.leg_joint_lower_limits, self.leg_joint_upper_limits)
        wheel_targets = np.clip(wheel_targets, -40.0, 40.0)
        leg_targets = self.limit_leg_target_rate(leg_targets)

        leg_msg = Float64MultiArray()
        leg_msg.data = [float(v) for v in leg_targets]
        wheel_msg = Float64MultiArray()
        wheel_msg.data = [float(v) for v in wheel_targets]
        self.leg_pub.publish(leg_msg)
        self.wheel_pub.publish(wheel_msg)

    def limit_leg_target_rate(self, leg_targets: np.ndarray) -> np.ndarray:
        if self.leg_target_rate_limit <= 0.0:
            return leg_targets

        now = time.monotonic()
        if self.last_leg_targets is None:
            self.last_leg_targets = np.array(
                [self.joint_pos.get(name, leg_targets[index]) for index, name in enumerate(self.leg_joint_order)],
                dtype=np.float32,
            )
            self.last_command_monotonic = now

        dt = max(now - float(self.last_command_monotonic), 1.0 / max(self.rate_hz, 1.0))
        max_step = self.leg_target_rate_limit * dt
        limited = self.last_leg_targets + np.clip(leg_targets - self.last_leg_targets, -max_step, max_step)
        self.last_leg_targets = limited.astype(np.float32)
        self.last_command_monotonic = now
        return limited

    def publish_commands(self, action: np.ndarray):
        leg_targets = self.action_leg_positions + action[:4] * self.leg_action_scale
        wheel_targets = action[4:6] * self.wheel_action_scale
        self.publish_raw_commands(leg_targets, wheel_targets)

    def publish_warmup_commands(self):
        # Hold the measured calibration pose until the RL policy is enabled.
        leg_targets = self.default_leg_positions
        wheel_targets = np.zeros(2, dtype=np.float32)
        self.publish_raw_commands(leg_targets, wheel_targets)
        self.previous_action = np.zeros(6, dtype=np.float32)

    def update(self):
        if time.monotonic() - self.start_monotonic < self.warmup_duration_s:
            self.publish_warmup_commands()
            return

        try:
            obs = self.build_observation()
            action = self.infer_action(obs)
        except Exception as exc:
            self.get_logger().error(f"Controller update failed: {exc}")
            action = np.zeros(6, dtype=np.float32)
        action = self.filter_action(action)
        self.publish_commands(action)
        self.previous_action = action


def main(args: Optional[List[str]] = None):
    rclpy.init(args=args)
    node = SwingboyRlController()
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
