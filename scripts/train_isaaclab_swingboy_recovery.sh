#!/usr/bin/env bash
set -euo pipefail

ISAACLAB_DIR="${ISAACLAB_DIR:-/home/lsy/桌面/RL/IsaacLab}"
ISAACLAB_CMD="${ISAACLAB_CMD:-/home/lsy/桌面/RL/env_isaaclab/bin/isaaclab}"
TASK="${TASK:-Isaac-Velocity-Recovery-Swingboy-v0}"
DEVICE="${DEVICE:-cuda:0}"
NUM_ENVS="${NUM_ENVS:-2048}"
MAX_ITERATIONS="${MAX_ITERATIONS:-1800}"
RUN_NAME="${RUN_NAME:-recovery_zero_joints_noscan_nobaselin}"
HEADLESS="${HEADLESS:-true}"
RENDERING_MODE="${RENDERING_MODE:-performance}"
RESUME="${RESUME:-false}"
LOAD_RUN="${LOAD_RUN:-}"
CHECKPOINT="${CHECKPOINT:-}"

args=(
  -p scripts/reinforcement_learning/rsl_rl/train.py
  --task "${TASK}"
  --num_envs "${NUM_ENVS}"
  --max_iterations "${MAX_ITERATIONS}"
  --device "${DEVICE}"
  --rendering_mode "${RENDERING_MODE}"
  --run_name "${RUN_NAME}"
)

case "${HEADLESS,,}" in
  1|true|yes|on)
    args+=(--headless)
    ;;
esac

case "${RESUME,,}" in
  1|true|yes|on)
    args+=(--resume)
    if [[ -n "${LOAD_RUN}" ]]; then
      args+=(--load_run "${LOAD_RUN}")
    fi
    if [[ -n "${CHECKPOINT}" ]]; then
      args+=(--checkpoint "${CHECKPOINT}")
    fi
    ;;
esac

cd "${ISAACLAB_DIR}"
PYTHONUNBUFFERED=1 TERM=xterm "${ISAACLAB_CMD}" "${args[@]}"
