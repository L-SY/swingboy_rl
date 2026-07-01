#!/usr/bin/env python3
"""Play a trained Swingboy policy in the MuJoCo viewer with keyboard commands."""

import argparse
import functools
import time
from pathlib import Path

from brax.training.agents.ppo import networks as ppo_networks
from brax.training.agents.ppo import train as ppo
from etils import epath
import jax
import jax.numpy as jp
from ml_collections import config_dict
import mujoco
import mujoco.viewer
import numpy as np

from mujoco_playground import registry
from mujoco_playground import wrapper
from mujoco_playground.config import locomotion_params
from mujoco_playground._src import mjx_env
from mujoco_playground._src.locomotion.swingboy import base as swingboy_base
from mujoco_playground._src.locomotion.swingboy import constants as consts


def _latest_checkpoint(path: Path) -> Path:
  path = path.expanduser().resolve()
  if path.name.isdigit():
    return path
  candidates = [p for p in path.iterdir() if p.is_dir() and p.name.isdigit()]
  if not candidates:
    raise FileNotFoundError(f"No numeric checkpoint directories found in {path}")
  return max(candidates, key=lambda p: int(p.name))


def _default_checkpoint() -> Path:
  patterns = (
      "logs/SwingboyJoystickRoughTerrain-*-swingboy-rough-long/checkpoints",
      "logs/SwingboyJoystickFlatTerrain-*-swingboy-flat-long/checkpoints",
      "logs/SwingboyJoystickRoughTerrain-*/checkpoints",
      "logs/SwingboyJoystickFlatTerrain-*/checkpoints",
  )
  candidates = []
  for pattern in patterns:
    candidates.extend(Path(".").glob(pattern))
  if not candidates:
    raise FileNotFoundError(
        "No Swingboy checkpoint found. Pass --checkpoint explicitly."
    )
  return max(candidates, key=lambda p: p.stat().st_mtime)


def _terrain_to_env_name(terrain: str) -> str:
  if terrain == "rough":
    return "SwingboyJoystickRoughTerrain"
  return "SwingboyJoystickFlatTerrain"


def _load_policy(checkpoint: Path, env_name: str, impl: str):
  restore_checkpoint_path = _latest_checkpoint(checkpoint)
  env_cfg = registry.get_default_config(env_name)
  env_cfg_overrides = {"impl": impl}
  env = registry.load(env_name, config=env_cfg, config_overrides=env_cfg_overrides)

  ppo_params = locomotion_params.brax_ppo_config(env_name, impl)
  ppo_params.num_timesteps = 0
  ppo_params.num_envs = 1
  ppo_params.num_evals = 1
  ppo_params.run_evals = False

  training_params = dict(ppo_params)
  network_config = training_params.pop("network_factory", config_dict.create())
  num_eval_envs = training_params.pop("num_eval_envs", 1)
  network_factory = functools.partial(
      ppo_networks.make_ppo_networks, **network_config
  )

  make_inference_fn, params, _ = ppo.train(
      environment=env,
      eval_env=env,
      progress_fn=lambda *_: None,
      network_factory=network_factory,
      restore_checkpoint_path=restore_checkpoint_path,
      save_checkpoint_path=None,
      wrap_env_fn=wrapper.wrap_for_brax_training,
      num_eval_envs=num_eval_envs,
      seed=0,
      vision=False,
      **training_params,
  )
  inference_fn = jax.jit(make_inference_fn(params, deterministic=True))
  return inference_fn, restore_checkpoint_path


class KeyboardCommand:
  """Small keyboard command source for the MuJoCo viewer."""

  def __init__(self, max_vx: float, max_wz: float, step_vx: float, step_wz: float):
    self.command = np.zeros(3, dtype=np.float32)
    self.max_vx = max_vx
    self.max_wz = max_wz
    self.step_vx = step_vx
    self.step_wz = step_wz
    self.reset_requested = False

  def _print(self) -> None:
    print(
        "command "
        f"vx={self.command[0]:+.2f} m/s, "
        f"wz={self.command[2]:+.2f} rad/s"
    )

  def on_key(self, key: int) -> None:
    if key in (ord("W"), ord("w")):
      self.command[0] = min(self.max_vx, self.command[0] + self.step_vx)
    elif key in (ord("S"), ord("s")):
      self.command[0] = max(-self.max_vx, self.command[0] - self.step_vx)
    elif key in (ord("A"), ord("a")):
      self.command[2] = min(self.max_wz, self.command[2] + self.step_wz)
    elif key in (ord("D"), ord("d")):
      self.command[2] = max(-self.max_wz, self.command[2] - self.step_wz)
    elif key in (ord("X"), ord("x"), 32):
      self.command[:] = 0.0
    elif key in (ord("R"), ord("r")):
      self.reset_requested = True
      print("reset requested")
      return
    else:
      return
    self._print()


class SwingboyPolicyController:
  """Runs the trained JAX policy from live MuJoCo sensor data."""

  def __init__(
      self,
      model: mujoco.MjModel,
      inference_fn,
      command_source: KeyboardCommand,
      ctrl_dt: float,
      target_base_height: float,
      leg_action_scale: float,
      wheel_action_scale: float,
  ):
    self.model = model
    self.inference_fn = inference_fn
    self.command_source = command_source
    self.ctrl_dt = ctrl_dt
    self.target_base_height = target_base_height
    self.leg_action_scale = leg_action_scale
    self.wheel_action_scale = wheel_action_scale

    self.default_ctrl = np.array(model.keyframe("home").ctrl, dtype=np.float32)
    self.default_leg_pose = self.default_ctrl[:4]
    self.last_action = np.zeros(model.nu, dtype=np.float32)
    self.last_policy_time = -np.inf
    self.rng = jax.random.PRNGKey(0)

    self.imu_site_id = model.site(consts.IMU_SITE).id
    self.leg_qpos_ids = np.array(mjx_env.get_qpos_ids(model, consts.LEG_JOINTS))
    self.joint_qvel_ids = np.array(
        mjx_env.get_qvel_ids(
            model, consts.LEG_JOINTS + consts.WHEEL_JOINTS
        )
    )

  def reset(self, data: mujoco.MjData) -> None:
    mujoco.mj_resetDataKeyframe(self.model, data, 0)
    mujoco.mj_forward(self.model, data)
    data.ctrl[:] = self.default_ctrl
    self.last_action[:] = 0.0
    self.last_policy_time = -np.inf

  def _obs(self, data: mujoco.MjData) -> dict[str, jp.ndarray]:
    linvel = np.array(data.sensor(consts.LOCAL_LINVEL_SENSOR).data)
    gyro = np.array(data.sensor(consts.GYRO_SENSOR).data)
    imu_xmat = data.site_xmat[self.imu_site_id].reshape(3, 3)
    gravity = imu_xmat.T @ np.array([0.0, 0.0, -1.0])
    height = np.array([data.qpos[2] - self.target_base_height])
    leg_pos = data.qpos[self.leg_qpos_ids] - self.default_leg_pose
    joint_vel = data.qvel[self.joint_qvel_ids]

    obs = np.hstack([
        linvel,
        gyro,
        gravity,
        height,
        leg_pos,
        joint_vel,
        self.last_action,
        self.command_source.command,
    ]).astype(np.float32)
    return {"state": jp.asarray(obs)}

  def maybe_update_control(self, data: mujoco.MjData) -> None:
    if data.time - self.last_policy_time < self.ctrl_dt:
      return
    self.last_policy_time = data.time
    self.rng, act_rng = jax.random.split(self.rng)
    action = np.array(self.inference_fn(self._obs(data), act_rng)[0])
    action = np.clip(action, -1.0, 1.0).astype(np.float32)
    self.last_action = action

    leg_targets = self.default_leg_pose + action[:4] * self.leg_action_scale
    wheel_targets = action[4:] * self.wheel_action_scale
    ctrl = np.hstack([leg_targets, wheel_targets])
    data.ctrl[:] = np.clip(
        ctrl,
        self.model.actuator_ctrlrange[:, 0],
        self.model.actuator_ctrlrange[:, 1],
    )


def _load_model(terrain: str) -> mujoco.MjModel:
  xml_path = consts.ROUGH_TERRAIN_XML if terrain == "rough" else consts.FLAT_TERRAIN_XML
  model = mujoco.MjModel.from_xml_string(
      epath.Path(xml_path).read_text(), assets=swingboy_base.get_assets()
  )
  model.opt.timestep = 0.004
  model.opt.ccd_iterations = 40
  return model


def main() -> None:
  parser = argparse.ArgumentParser()
  parser.add_argument("--checkpoint", type=Path, default=None)
  parser.add_argument("--terrain", choices=("flat", "rough"), default="rough")
  parser.add_argument("--impl", choices=("jax", "warp"), default="warp")
  parser.add_argument("--max_vx", type=float, default=0.9)
  parser.add_argument("--max_wz", type=float, default=1.2)
  parser.add_argument("--step_vx", type=float, default=0.1)
  parser.add_argument("--step_wz", type=float, default=0.2)
  parser.add_argument("--dry_run", action="store_true")
  args = parser.parse_args()

  checkpoint = args.checkpoint or _default_checkpoint()
  env_name = _terrain_to_env_name(args.terrain)
  print(f"Loading {env_name} policy from {checkpoint}")
  inference_fn, restore_checkpoint_path = _load_policy(
      checkpoint, env_name, args.impl
  )
  print(f"Restored checkpoint: {restore_checkpoint_path}")

  model = _load_model(args.terrain)
  data = mujoco.MjData(model)
  command = KeyboardCommand(args.max_vx, args.max_wz, args.step_vx, args.step_wz)
  controller = SwingboyPolicyController(
      model=model,
      inference_fn=inference_fn,
      command_source=command,
      ctrl_dt=0.02,
      target_base_height=0.30,
      leg_action_scale=0.35,
      wheel_action_scale=16.0,
  )
  controller.reset(data)

  if args.dry_run:
    controller.maybe_update_control(data)
    print("Dry run action:", controller.last_action)
    return

  print("Keyboard: W/S forward speed, A/D yaw, X or Space stop, R reset.")
  with mujoco.viewer.launch_passive(
      model, data, key_callback=command.on_key
  ) as viewer:
    while viewer.is_running():
      start = time.time()
      if command.reset_requested:
        controller.reset(data)
        command.reset_requested = False
      controller.maybe_update_control(data)
      mujoco.mj_step(model, data)
      viewer.sync()
      elapsed = time.time() - start
      if elapsed < model.opt.timestep:
        time.sleep(model.opt.timestep - elapsed)


if __name__ == "__main__":
  main()
