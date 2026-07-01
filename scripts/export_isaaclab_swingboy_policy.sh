#!/usr/bin/env bash
set -euo pipefail

if [[ $# -lt 1 && -z "${CHECKPOINT:-}" ]]; then
  echo "Usage: $0 /path/to/model_*.pt" >&2
  echo "Or set CHECKPOINT=/path/to/model_*.pt" >&2
  exit 2
fi

CHECKPOINT="${1:-${CHECKPOINT}}"
ISAACLAB_DIR="${ISAACLAB_DIR:-/home/lsy/桌面/RL/IsaacLab}"
ISAACLAB_CMD="${ISAACLAB_CMD:-/home/lsy/桌面/RL/env_isaaclab/bin/isaaclab}"
TASK="${TASK:-Isaac-Velocity-RoughMixed-Swingboy-Play-v0}"
DEVICE="${DEVICE:-cuda:0}"
NUM_ENVS="${NUM_ENVS:-16}"
EXPORT_TIMEOUT_SEC="${EXPORT_TIMEOUT_SEC:-90}"

SCRIPT_DIR=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
REPO_ROOT=$(cd -- "${SCRIPT_DIR}/.." && pwd)
POLICY_OUT="${POLICY_OUT:-${REPO_ROOT}/policies/swingboy_rough_latest.onnx}"

if [[ ! -f "${CHECKPOINT}" ]]; then
  echo "Checkpoint does not exist: ${CHECKPOINT}" >&2
  exit 2
fi

mkdir -p "$(dirname "${POLICY_OUT}")"

cd "${ISAACLAB_DIR}"
set +e
PYTHONUNBUFFERED=1 TERM=xterm timeout -s INT "${EXPORT_TIMEOUT_SEC}" "${ISAACLAB_CMD}" \
  -p scripts/reinforcement_learning/rsl_rl/play.py \
  --task "${TASK}" \
  --checkpoint "${CHECKPOINT}" \
  --num_envs "${NUM_ENVS}" \
  --headless \
  --device "${DEVICE}"
PLAY_STATUS=$?
set -e

if [[ "${PLAY_STATUS}" -ne 0 && "${PLAY_STATUS}" -ne 124 && "${PLAY_STATUS}" -ne 130 ]]; then
  echo "IsaacLab play/export failed with exit code ${PLAY_STATUS}" >&2
  exit "${PLAY_STATUS}"
fi

EXPORTED_ONNX="$(dirname "${CHECKPOINT}")/exported/policy.onnx"
if [[ ! -f "${EXPORTED_ONNX}" ]]; then
  echo "Expected exported ONNX was not found: ${EXPORTED_ONNX}" >&2
  exit 1
fi

cp "${EXPORTED_ONNX}" "${POLICY_OUT}"
echo "Copied policy to ${POLICY_OUT}"
