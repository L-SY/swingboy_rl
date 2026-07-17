#!/usr/bin/env python3
"""Sweep simple pitch PD wheel controllers from Swingboy's curriculum stand pose."""

import argparse
import itertools

from isaaclab.app import AppLauncher


parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("--steps", type=int, default=600)
AppLauncher.add_app_launcher_args(parser)
args = parser.parse_args()

app_launcher = AppLauncher(args)
simulation_app = app_launcher.app

import gymnasium as gym
import torch

import isaaclab_tasks  # noqa: F401
from isaaclab_tasks.utils import parse_env_cfg


TASK = "Isaac-Standup-Discovery-Swingboy-v0"
KP_VALUES = (0.5, 1.0, 2.0, 4.0, 8.0)
KD_VALUES = (0.05, 0.10, 0.20, 0.40)
ALL_CONTROLLERS = tuple(itertools.product((-1.0, 1.0), KP_VALUES, KD_VALUES))
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
    non_wheel_ids, _ = contact_sensor.find_bodies(NON_WHEEL_BODIES, preserve_order=True)

    results = []
    tilt_limit = torch.deg2rad(torch.tensor(30.0, device=base_env.device))
    for sign, kp_value, kd_value in ALL_CONTROLLERS:
        with torch.inference_mode():
            env.reset()
        alive = True
        survived_steps = 0
        max_tilt = 0.0
        max_drift = 0.0
        for _ in range(args.steps):
            gravity_x = robot.data.projected_gravity_b[0, 0]
            pitch_rate = robot.data.root_ang_vel_b[0, 1]
            wheel_action = torch.clamp(sign * (kp_value * gravity_x + kd_value * pitch_rate), -1.0, 1.0)
            actions = torch.zeros(env.action_space.shape, device=base_env.device)
            actions[:, -2:] = wheel_action
            with torch.inference_mode():
                env.step(actions)

            tilt = torch.acos((-robot.data.projected_gravity_b[0, 2]).clamp(-1.0, 1.0))
            displacement = torch.linalg.vector_norm(
                robot.data.root_pos_w[0, :2] - base_env.scene.env_origins[0, :2]
            )
            non_wheel_force = torch.linalg.vector_norm(
                contact_sensor.data.net_forces_w[0, non_wheel_ids], dim=-1
            ).max()
            valid = bool(
                (robot.data.root_pos_w[0, 2] >= 0.27)
                & (tilt <= tilt_limit)
                & (non_wheel_force <= 1.0)
            )
            if alive:
                survived_steps += 1
            alive = alive and valid
            max_tilt = max(max_tilt, float(tilt.item()))
            max_drift = max(max_drift, float(displacement.item()))
            if not valid:
                break

        results.append(
            (
                survived_steps,
                sign,
                kp_value,
                kd_value,
                max_tilt * 180.0 / torch.pi,
                max_drift,
            )
        )
    results.sort(reverse=True)
    print("rank survived_s sign kp kd max_tilt_deg max_drift_m")
    for rank, result in enumerate(results[:15], start=1):
        steps, sign, kp_value, kd_value, tilt_deg, drift = result
        print(
            f"{rank:02d} {steps * base_env.step_dt:10.2f} {sign:+.0f} "
            f"{kp_value:4.2f} {kd_value:4.2f} {tilt_deg:12.2f} {drift:11.3f}"
        )

    env.close()


if __name__ == "__main__":
    main()
    simulation_app.close()
