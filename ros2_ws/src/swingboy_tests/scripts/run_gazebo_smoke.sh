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

source /opt/ros/lyrical/setup.bash
source "${ROS2_WS}/install/setup.bash"
set -u

TIMEOUT_SEC="${TIMEOUT_SEC:-45}"
LOG_FILE="${LOG_FILE:-${ROS2_WS}/log/swingboy_gazebo_smoke.log}"
mkdir -p "$(dirname "${LOG_FILE}")"

setsid ros2 launch swingboy_bringup gazebo_rl.launch.py \
  headless:=true \
  use_rl:=false >"${LOG_FILE}" 2>&1 &
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

deadline=$((SECONDS + TIMEOUT_SEC))
while (( SECONDS < deadline )); do
  if ! kill -0 "${launch_pid}" 2>/dev/null; then
    echo "Gazebo launch exited before controllers became active. Log tail:" >&2
    tail -120 "${LOG_FILE}" >&2 || true
    exit 1
  fi
  if controllers_active; then
    echo "Gazebo smoke passed: controllers are active."
    exit 0
  fi
  sleep 1
done

echo "Timed out waiting for Gazebo controllers. Log tail:" >&2
tail -120 "${LOG_FILE}" >&2 || true
exit 1
