#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
REPO_ROOT=$(cd -- "${SCRIPT_DIR}/.." && pwd)
RL_ROOT="${RL_ROOT:-$(dirname "${REPO_ROOT}")}"
ISAACLAB_DIR="${ISAACLAB_DIR:-${RL_ROOT}/IsaacLab}"
ISAACLAB_CMD="${ISAACLAB_CMD:-${RL_ROOT}/env_isaaclab/bin/isaaclab}"
TASK="${TASK:-Isaac-Velocity-Track-Swingboy-v0}"
DEVICE="${DEVICE:-cuda:0}"
NUM_ENVS="${NUM_ENVS:-2048}"
MAX_ITERATIONS="${MAX_ITERATIONS:-10000}"
RUN_NAME="${RUN_NAME:-track_velocity_curriculum}"
REQUESTED_HEADLESS="${HEADLESS:-true}"
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

case "${REQUESTED_HEADLESS,,}" in
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
unset HEADLESS
PYTHONUNBUFFERED=1 TERM=xterm "${ISAACLAB_CMD}" "${args[@]}"
