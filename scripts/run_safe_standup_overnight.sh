#!/usr/bin/env bash

set -uo pipefail

SCRIPT_DIR=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
REPO_ROOT=$(cd -- "${SCRIPT_DIR}/.." && pwd)
RL_ROOT="${RL_ROOT:-$(dirname "${REPO_ROOT}")}"
ISAACLAB_ROOT="${ISAACLAB_DIR:-${RL_ROOT}/IsaacLab}"
ISAACLAB="${ISAACLAB_CMD:-${RL_ROOT}/env_isaaclab/bin/isaaclab}"
PYTHON="${ISAACLAB_PYTHON:-${RL_ROOT}/env_isaaclab/bin/python}"
LOG_ROOT="$ISAACLAB_ROOT/logs/rsl_rl/swingboy_safe_standup"
RUN_NAME="${1:-safe_standup_4096_10k_$(date +%Y%m%d_%H%M%S)}"
RENDER_MODE="${2:-headless}"
TRAIN_LOG="$REPO_ROOT/logs/${RUN_NAME}.log"
POST_LOG="$REPO_ROOT/logs/${RUN_NAME}_milestones.log"

mkdir -p "$REPO_ROOT/logs"
printf '%s\n' "$RUN_NAME" > "$REPO_ROOT/logs/latest_safe_standup_run.txt"

cd "$ISAACLAB_ROOT" || exit 1
render_args=(--headless)
if [[ "$RENDER_MODE" == "gui" ]]; then
    render_args=()
fi
ISAACLAB_DISABLE_RANDOM_EP_LEN=1 TERM=xterm "$ISAACLAB" -p scripts/reinforcement_learning/rsl_rl/train.py \
    --task Isaac-Safe-Standup-Swingboy-v0 \
    --num_envs 4096 \
    --max_iterations 10000 \
    --logger tensorboard \
    --run_name "$RUN_NAME" \
    --device cuda:0 \
    "${render_args[@]}" 2>&1 | tee "$TRAIN_LOG"
train_status=${PIPESTATUS[0]}

run_dir=$(find "$LOG_ROOT" -mindepth 1 -maxdepth 1 -type d -name "*_${RUN_NAME}" -print | sort | tail -n 1)
if [[ -n "$run_dir" ]]; then
    printf '%s\n' "$run_dir" > "$REPO_ROOT/logs/latest_safe_standup_run_dir.txt"
fi

if [[ $train_status -ne 0 ]]; then
    printf 'Training exited with status %d; milestone recording skipped.\n' "$train_status" | tee -a "$POST_LOG"
    exit "$train_status"
fi
if [[ -z "$run_dir" ]]; then
    printf 'Could not locate completed run directory for %s.\n' "$RUN_NAME" | tee -a "$POST_LOG"
    exit 2
fi

"$PYTHON" "$REPO_ROOT/scripts/analyze_safe_standup_milestones.py" "$run_dir" 2>&1 | tee "$POST_LOG"
