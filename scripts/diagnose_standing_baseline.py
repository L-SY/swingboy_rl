#!/usr/bin/env python3
"""Measure whether Swingboy can hold the curriculum stand pose under zero actions."""

import argparse

from isaaclab.app import AppLauncher


parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("--steps", type=int, default=600, help="Number of 50 Hz policy steps to simulate.")
parser.add_argument("--print-every", type=int, default=25)
AppLauncher.add_app_launcher_args(parser)
args = parser.parse_args()

app_launcher = AppLauncher(args)
simulation_app = app_launcher.app

import gymnasium as gym
import torch

import isaaclab_tasks  # noqa: F401
from isaaclab_tasks.utils import parse_env_cfg


TASK = "Isaac-Standup-Discovery-Swingboy-v0"
LEG_JOINTS = ["left_hip", "left_knee", "right_hip", "right_knee"]
WHEEL_JOINTS = ["left_wheel", "right_wheel"]
WHEEL_BODIES = ["left_wheel", "right_wheel"]
NON_WHEEL_BODIES = [
    "base_link",
    "left_hip_knee_link",
    "left_knee_wheel_link",
    "right_hip_knee_link",
    "right_knee_wheel_link",
]


def main() -> None:
    env_cfg = parse_env_cfg(TASK, device=args.device, num_envs=1)
    env_cfg.observations.policy.enable_corruption = False
    env_cfg.terminations.time_out = None
    env_cfg.terminations.standup_failure = None
    env_cfg.terminations.spawn_area = None
    env_cfg.curriculum.assistive_lift = None

    env = gym.make(TASK, cfg=env_cfg)
    env.reset()
    base_env = env.unwrapped
    robot = base_env.scene["robot"]
    contact_sensor = base_env.scene.sensors["contact_forces"]
    leg_ids, _ = robot.find_joints(LEG_JOINTS, preserve_order=True)
    wheel_joint_ids, _ = robot.find_joints(WHEEL_JOINTS, preserve_order=True)
    wheel_body_ids, _ = contact_sensor.find_bodies(WHEEL_BODIES, preserve_order=True)
    non_wheel_body_ids, _ = contact_sensor.find_bodies(NON_WHEEL_BODIES, preserve_order=True)

    min_height = float("inf")
    max_tilt = 0.0
    first_illegal_contact = None
    for step in range(args.steps):
        actions = torch.zeros(env.action_space.shape, device=base_env.device)
        with torch.inference_mode():
            env.step(actions)

        height = robot.data.root_pos_w[0, 2].item()
        tilt = torch.acos((-robot.data.projected_gravity_b[0, 2]).clamp(-1.0, 1.0)).item()
        planar_speed = torch.linalg.vector_norm(robot.data.root_lin_vel_b[0, :2]).item()
        wheel_contact = torch.linalg.vector_norm(
            contact_sensor.data.net_forces_w[0, wheel_body_ids], dim=-1
        )
        non_wheel_contact = torch.linalg.vector_norm(
            contact_sensor.data.net_forces_w[0, non_wheel_body_ids], dim=-1
        )
        max_non_wheel_contact = non_wheel_contact.max().item()
        if first_illegal_contact is None and max_non_wheel_contact > 1.0:
            first_illegal_contact = step
        min_height = min(min_height, height)
        max_tilt = max(max_tilt, tilt)

        if step % args.print_every == 0 or step == args.steps - 1:
            leg_deg = torch.rad2deg(robot.data.joint_pos[0, leg_ids]).tolist()
            wheel_speed = robot.data.joint_vel[0, wheel_joint_ids].tolist()
            print(
                f"step={step:04d} t={step * base_env.step_dt:5.2f}s z={height:.3f} "
                f"tilt_deg={torch.rad2deg(torch.tensor(tilt)).item():6.2f} "
                f"vxy={planar_speed:.3f} leg_deg={[round(v, 2) for v in leg_deg]} "
                f"wheel_speed={[round(v, 3) for v in wheel_speed]} "
                f"wheel_contact={[round(v, 2) for v in wheel_contact.tolist()]} "
                f"max_non_wheel_contact={max_non_wheel_contact:.2f}"
            )

    print(
        f"SUMMARY min_height={min_height:.3f} max_tilt_deg={max_tilt * 180.0 / torch.pi:.2f} "
        f"first_illegal_contact_step={first_illegal_contact}"
    )
    env.close()


if __name__ == "__main__":
    main()
    simulation_app.close()
