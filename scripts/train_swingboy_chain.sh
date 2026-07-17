#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
REPO_ROOT=$(cd -- "${SCRIPT_DIR}/.." && pwd)
cd "${REPO_ROOT}/sim/mujoco"

: "${UV:=uv}"
: "${CONSOLE_LOG:=${REPO_ROOT}/logs/swingboy_train_$(date +%Y%m%d-%H%M%S).out}"
: "${USE_TB:=true}"

: "${FLAT_STEPS:=5000000}"
: "${FLAT_IMPL:=warp}"
: "${FLAT_NUM_ENVS:=128}"
: "${FLAT_NUM_EVAL_ENVS:=32}"
: "${FLAT_EPISODE_LENGTH:=500}"
: "${FLAT_SUFFIX:=swingboy-flat-long}"

: "${ROUGH_STEPS:=5000000}"
: "${ROUGH_NUM_ENVS:=32}"
: "${ROUGH_NUM_EVAL_ENVS:=8}"
: "${ROUGH_EPISODE_LENGTH:=500}"
: "${ROUGH_SUFFIX:=swingboy-rough-long}"

mkdir -p "$(dirname "$CONSOLE_LOG")"
exec > >(tee -a "$CONSOLE_LOG") 2>&1

tb_args=()
case "${USE_TB,,}" in
  1|true|yes|on)
    tb_args=(--use_tb)
    ;;
esac

unset LD_LIBRARY_PATH
export JAX_DEFAULT_MATMUL_PRECISION="${JAX_DEFAULT_MATMUL_PRECISION:-highest}"
export XLA_PYTHON_CLIENT_PREALLOCATE="${XLA_PYTHON_CLIENT_PREALLOCATE:-false}"
export PYTHONUNBUFFERED=1

echo "[$(date --iso-8601=seconds)] starting Swingboy flat training"
"$UV" --no-config run train-jax-ppo \
  --env_name=SwingboyJoystickFlatTerrain \
  --impl="$FLAT_IMPL" \
  --num_timesteps="$FLAT_STEPS" \
  --num_evals=10 \
  --num_envs="$FLAT_NUM_ENVS" \
  --num_eval_envs="$FLAT_NUM_EVAL_ENVS" \
  --episode_length="$FLAT_EPISODE_LENGTH" \
  --batch_size=256 \
  --num_minibatches=8 \
  --num_updates_per_batch=2 \
  --unroll_length=10 \
  --num_videos=1 \
  --suffix="$FLAT_SUFFIX" \
  "${tb_args[@]}"

echo "[$(date --iso-8601=seconds)] flat training finished; locating checkpoint"
flat_ckpt="$(
  find logs -maxdepth 2 -type d \
    -path "logs/SwingboyJoystickFlatTerrain-*-${FLAT_SUFFIX}/checkpoints" \
    -printf "%T@ %p\n" \
    | sort -n \
    | tail -1 \
    | cut -d" " -f2-
)"

if [[ -z "$flat_ckpt" ]]; then
  echo "No flat checkpoint directory found for suffix: $FLAT_SUFFIX" >&2
  exit 1
fi

echo "[$(date --iso-8601=seconds)] using flat checkpoint: $flat_ckpt"
echo "[$(date --iso-8601=seconds)] starting Swingboy rough training"
"$UV" --no-config run train-jax-ppo \
  --env_name=SwingboyJoystickRoughTerrain \
  --impl=warp \
  --load_checkpoint_path="$flat_ckpt" \
  --num_timesteps="$ROUGH_STEPS" \
  --num_evals=10 \
  --num_envs="$ROUGH_NUM_ENVS" \
  --num_eval_envs="$ROUGH_NUM_EVAL_ENVS" \
  --episode_length="$ROUGH_EPISODE_LENGTH" \
  --batch_size=128 \
  --num_minibatches=4 \
  --num_updates_per_batch=1 \
  --unroll_length=10 \
  --num_videos=1 \
  --suffix="$ROUGH_SUFFIX" \
  "${tb_args[@]}"

echo "[$(date --iso-8601=seconds)] Swingboy training chain finished"
