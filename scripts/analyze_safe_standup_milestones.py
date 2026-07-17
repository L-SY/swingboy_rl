#!/usr/bin/env python3

import argparse
import json
import re
import shutil
import subprocess
from pathlib import Path

from tensorboard.backend.event_processing.event_accumulator import EventAccumulator


def scalar_map(accumulator, tag):
    return {event.step: float(event.value) for event in accumulator.Scalars(tag)}


def nearest_value(values, step):
    if not values:
        return None
    key = min(values, key=lambda candidate: abs(candidate - step))
    return values[key]


def select_milestones(rewards, window, count, min_spacing):
    steps = sorted(rewards)
    candidates = []
    for index in range(window, len(steps)):
        step = steps[index]
        old_step = steps[index - window]
        candidates.append((rewards[step] - rewards[old_step], step))
    selected = []
    for gain, step in sorted(candidates, reverse=True):
        if all(abs(step - existing_step) >= min_spacing for _, existing_step in selected):
            selected.append((gain, step))
        if len(selected) >= count:
            break
    selected.sort(key=lambda item: item[1])
    return selected


def nearest_checkpoint(run_dir, step):
    checkpoints = []
    for path in run_dir.glob("model_*.pt"):
        match = re.fullmatch(r"model_(\d+)\.pt", path.name)
        if match:
            checkpoints.append((int(match.group(1)), path))
    return min(checkpoints, key=lambda item: abs(item[0] - step))


def main():
    repo_root = Path(__file__).resolve().parent.parent
    rl_root = repo_root.parent
    parser = argparse.ArgumentParser()
    parser.add_argument("run_dir", type=Path)
    parser.add_argument("--isaaclab-root", type=Path, default=rl_root / "IsaacLab")
    parser.add_argument("--python-env", type=Path, default=rl_root / "env_isaaclab")
    parser.add_argument("--count", type=int, default=5)
    parser.add_argument("--video-length", type=int, default=500)
    args = parser.parse_args()

    run_dir = args.run_dir.resolve()
    accumulator = EventAccumulator(str(run_dir), size_guidance={"scalars": 0})
    accumulator.Reload()
    rewards = scalar_map(accumulator, "Train/mean_reward")
    if not rewards:
        raise RuntimeError(f"No Train/mean_reward data in {run_dir}")

    selected = select_milestones(rewards, window=50, count=args.count, min_spacing=200)
    tags = {
        "upright_height": scalar_map(accumulator, "Episode_Reward/upright_height_exp"),
        "stood_success": scalar_map(accumulator, "Episode_Reward/stood_success"),
        "termination": scalar_map(accumulator, "Episode_Termination/standup_failure"),
        "assist_force": scalar_map(accumulator, "Curriculum/assistive_lift/force_n"),
        "orientation_torque": scalar_map(accumulator, "Curriculum/assistive_lift/orientation_torque_nm"),
        "reset_level": scalar_map(accumulator, "Curriculum/assistive_lift/reset_level"),
        "push_force": scalar_map(accumulator, "Curriculum/assistive_lift/push_force_n"),
        "policy_std": scalar_map(accumulator, "Policy/mean_std"),
    }

    milestone_dir = run_dir / "milestones"
    milestone_dir.mkdir(exist_ok=True)
    records = []
    for gain, requested_step in selected:
        checkpoint_step, checkpoint = nearest_checkpoint(run_dir, requested_step)
        record = {
            "requested_step": requested_step,
            "checkpoint_step": checkpoint_step,
            "checkpoint": str(checkpoint),
            "reward": nearest_value(rewards, checkpoint_step),
            "reward_gain_50_iterations": gain,
        }
        for name, values in tags.items():
            record[name] = nearest_value(values, checkpoint_step)

        video_folder = run_dir / "videos" / "play"
        command = [
            str(args.python_env / "bin" / "isaaclab"),
            "-p",
            "scripts/reinforcement_learning/rsl_rl/play.py",
            "--task",
            "Isaac-Safe-Standup-Swingboy-Play-v0",
            "--checkpoint",
            str(checkpoint),
            "--num_envs",
            "1",
            "--video",
            "--video_length",
            str(args.video_length),
            "--headless",
            "--device",
            "cuda:0",
        ]
        result = subprocess.run(command, cwd=args.isaaclab_root, text=True, capture_output=True, timeout=240)
        record["record_exit_code"] = result.returncode
        record["record_log_tail"] = (result.stdout + result.stderr)[-2000:]
        recorded_videos = sorted(video_folder.glob("*.mp4"), key=lambda path: path.stat().st_mtime)
        if recorded_videos:
            destination = milestone_dir / f"step_{checkpoint_step:05d}_gain_{gain:+.2f}.mp4"
            shutil.copy2(recorded_videos[-1], destination)
            record["video"] = str(destination)
        records.append(record)

    (milestone_dir / "milestones.json").write_text(json.dumps(records, indent=2), encoding="utf-8")
    lines = ["# Swingboy Safe Stand-up Milestones", ""]
    for record in records:
        lines.extend(
            [
                f"## Iteration {record['checkpoint_step']}",
                "",
                f"- Reward: {record['reward']:.3f}",
                f"- 50-iteration gain: {record['reward_gain_50_iterations']:+.3f}",
                f"- Upright-height reward: {record['upright_height']:.3f}",
                f"- Stood-success reward: {record['stood_success']:.3f}",
                f"- Stand-up termination rate: {record['termination']:.4f}",
                f"- Assist force: {record['assist_force']:.1f} N",
                f"- Orientation assist: {record['orientation_torque']:.1f} Nm",
                f"- Reset curriculum level: {record['reset_level']:.0f}",
                f"- Push force: {record['push_force']:.1f} N",
                f"- Policy standard deviation: {record['policy_std']:.4f}",
                f"- Video: {record.get('video', 'recording failed')}",
                "",
            ]
        )
    (milestone_dir / "report.md").write_text("\n".join(lines), encoding="utf-8")


if __name__ == "__main__":
    main()
