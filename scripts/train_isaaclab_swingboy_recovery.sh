#!/usr/bin/env bash
set -euo pipefail

ISAACLAB_DIR="${ISAACLAB_DIR:-/home/lsy/桌面/RL/IsaacLab}"
ISAACLAB_CMD="${ISAACLAB_CMD:-/home/lsy/桌面/RL/env_isaaclab/bin/isaaclab}"
TASK="${TASK:-Isaac-Velocity-Recovery-Swingboy-v0}"
DEVICE="${DEVICE:-cuda:0}"
NUM_ENVS="${NUM_ENVS:-2048}"
MAX_ITERATIONS="${MAX_ITERATIONS:-1800}"
RUN_NAME="${RUN_NAME:-recovery_zero_joints_noscan_nobaselin}"

cd "${ISAACLAB_DIR}"
PYTHONUNBUFFERED=1 TERM=xterm "${ISAACLAB_CMD}" \
  -p scripts/reinforcement_learning/rsl_rl/train.py \
  --task "${TASK}" \
  --num_envs "${NUM_ENVS}" \
  --max_iterations "${MAX_ITERATIONS}" \
  --device "${DEVICE}" \
  --headless \
  --run_name "${RUN_NAME}"
