#!/usr/bin/env bash
set -eo pipefail

SCRIPT_DIR=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
if [[ -n "${SWINGBOY_ROS2_WS:-}" ]]; then
  ROS2_WS="${SWINGBOY_ROS2_WS}"
elif [[ -f "${SCRIPT_DIR}/../../../install/setup.bash" ]]; then
  ROS2_WS=$(cd -- "${SCRIPT_DIR}/../../.." && pwd)
elif [[ -f "${SCRIPT_DIR}/../../../../install/setup.bash" ]]; then
  ROS2_WS=$(cd -- "${SCRIPT_DIR}/../../../.." && pwd)
else
  echo "Could not locate ros2_ws. Set SWINGBOY_ROS2_WS=/path/to/ros2_ws." >&2
  exit 2
fi

REPO_ROOT=$(cd -- "${ROS2_WS}/.." && pwd)
POLICY_PATH="${SWINGBOY_POLICY_PATH:-${REPO_ROOT}/policies/v0.1.0-legacy/swingboy_track_latest.onnx}"
if [[ ! -f "${POLICY_PATH}" ]]; then
    echo "Missing policy: ${POLICY_PATH}" >&2
    echo "Export the IsaacLab policy to policies/v0.1.0-legacy/swingboy_track_latest.onnx or set SWINGBOY_POLICY_PATH." >&2
  exit 2
fi

source /opt/ros/lyrical/setup.bash
source "${ROS2_WS}/install/setup.bash"
set -u

TIMEOUT_SEC="${TIMEOUT_SEC:-90}"
LOG_FILE="${LOG_FILE:-${ROS2_WS}/log/swingboy_gazebo_rl_test.log}"
mkdir -p "$(dirname "${LOG_FILE}")"

setsid ros2 launch swingboy_bringup gazebo_rl.launch.py \
  headless:=true \
  use_rl:=true \
  use_height_scan:=false \
  policy_path:="${POLICY_PATH}" >"${LOG_FILE}" 2>&1 &
launch_pid=$!

cleanup() {
  if [[ -n "${launch_pid:-}" ]] && kill -0 "${launch_pid}" 2>/dev/null; then
    kill -TERM "-${launch_pid}" 2>/dev/null || kill -TERM "${launch_pid}" 2>/dev/null || true
    for _ in {1..10}; do
      if ! kill -0 "${launch_pid}" 2>/dev/null; then
        break
      fi
      sleep 0.5
    done
    if kill -0 "${launch_pid}" 2>/dev/null; then
      kill -KILL "-${launch_pid}" 2>/dev/null || kill -KILL "${launch_pid}" 2>/dev/null || true
    fi
    wait "${launch_pid}" 2>/dev/null || true
  fi
}
trap cleanup EXIT

controllers_active() {
  local output
  output=$(ros2 control list_controllers -c /controller_manager --spin-time 1.0 2>/dev/null) || return 1
  grep -Eq '^joint_state_broadcaster[[:space:]].*[[:space:]]active' <<<"${output}" || return 1
  grep -Eq '^swingboy_leg_controller[[:space:]].*[[:space:]]active' <<<"${output}" || return 1
  grep -Eq '^swingboy_wheel_controller[[:space:]].*[[:space:]]active' <<<"${output}" || return 1
}

rl_controller_ready() {
  ros2 node list 2>/dev/null | grep -q '^/swingboy_rl_controller$'
}

deadline=$((SECONDS + TIMEOUT_SEC))
while (( SECONDS < deadline )); do
  if ! kill -0 "${launch_pid}" 2>/dev/null; then
    echo "Gazebo launch exited before RL test became ready. Log tail:" >&2
    tail -160 "${LOG_FILE}" >&2 || true
    exit 1
  fi
  if controllers_active && rl_controller_ready; then
    break
  fi
  sleep 1
done

if (( SECONDS >= deadline )); then
  echo "Timed out waiting for controllers and RL controller. Log tail:" >&2
  tail -160 "${LOG_FILE}" >&2 || true
  exit 1
fi

publish_cmd() {
  local lin_x="$1"
  local yaw="$2"
  ros2 topic pub --once /cmd_vel geometry_msgs/msg/Twist \
    "{linear: {x: ${lin_x}, y: 0.0, z: 0.0}, angular: {x: 0.0, y: 0.0, z: ${yaw}}}" >/dev/null
}

publish_cmd 0.25 0.0
sleep 6
publish_cmd 0.20 0.35
sleep 6
publish_cmd 0.0 0.0
sleep 2

echo "Gazebo RL command test completed."
