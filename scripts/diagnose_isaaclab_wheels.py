#!/usr/bin/env python3
"""Apply a fixed wheel command and print the complete Isaac Lab wheel-control path."""

import argparse

from isaaclab.app import AppLauncher


parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("--steps", type=int, default=150)
parser.add_argument("--wheel-action", type=float, default=0.5)
AppLauncher.add_app_launcher_args(parser)
args = parser.parse_args()

app_launcher = AppLauncher(args)
simulation_app = app_launcher.app

import gymnasium as gym
import torch

import isaaclab_tasks  # noqa: F401
from isaaclab_tasks.utils import parse_env_cfg


def main() -> None:
    env_cfg = parse_env_cfg("Isaac-Safe-Standup-Swingboy-v0", device=args.device, num_envs=1)
    env_cfg.observations.policy.enable_corruption = False
    env_cfg.terminations.standup_failure = None
    env = gym.make("Isaac-Safe-Standup-Swingboy-v0", cfg=env_cfg)
    env.reset()

    base_env = env.unwrapped
    robot = base_env.scene["robot"]
    wheel_action = base_env.action_manager.get_term("wheel_joint_vel")
    wheel_joint_ids, _ = robot.find_joints(["left_wheel", "right_wheel"], preserve_order=True)
    contact_sensor = base_env.scene.sensors["contact_forces"]
    wheel_body_ids, _ = contact_sensor.find_bodies(["left_wheel", "right_wheel"], preserve_order=True)

    for step in range(args.steps):
        actions = torch.zeros(env.action_space.shape, device=base_env.device)
        actions[:, -2:] = args.wheel_action
        with torch.inference_mode():
            env.step(actions)

        if step % 10 == 0 or step == args.steps - 1:
            contact = torch.linalg.vector_norm(contact_sensor.data.net_forces_w[:, wheel_body_ids], dim=-1)[0]
            speed = robot.data.joint_vel[0, wheel_joint_ids]
            torque = robot.data.applied_torque[0, wheel_joint_ids]
            print(
                f"step={step:03d} z={robot.data.root_pos_w[0, 2].item():.3f} "
                f"contact={contact.tolist()} raw={wheel_action.raw_actions[0].tolist()} "
                f"target={wheel_action.processed_actions[0].tolist()} "
                f"speed={speed.tolist()} torque={torque.tolist()}"
            )

    env.close()


if __name__ == "__main__":
    main()
    simulation_app.close()
