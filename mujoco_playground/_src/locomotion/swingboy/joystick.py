"""Velocity-command tracking task for Swingboy."""

from typing import Any, Dict, Optional, Union

import jax
import jax.numpy as jp
from ml_collections import config_dict
from mujoco import mjx

from mujoco_playground._src import mjx_env
from mujoco_playground._src.locomotion.swingboy import base as swingboy_base
from mujoco_playground._src.locomotion.swingboy import constants as consts


def default_config() -> config_dict.ConfigDict:
  return config_dict.create(
      ctrl_dt=0.02,
      sim_dt=0.004,
      episode_length=1000,
      action_repeat=1,
      leg_action_scale=0.35,
      wheel_action_scale=16.0,
      target_base_height=0.35,
      terminate_base_height=0.14,
      max_base_height=0.60,
      noise_config=config_dict.create(
          level=1.0,
          scales=config_dict.create(
              joint_pos=0.02,
              joint_vel=0.8,
              gyro=0.05,
              gravity=0.02,
              linvel=0.05,
              height=0.01,
          ),
      ),
      reward_config=config_dict.create(
          scales=config_dict.create(
              tracking_lin_vel=2.0,
              tracking_ang_vel=0.8,
              height=1.5,
              upright=1.0,
              lin_vel_y=-0.15,
              lin_vel_z=-0.6,
              ang_vel_xy=-0.08,
              pose=-0.15,
              wheel_idle=-0.02,
              torques=-0.00004,
              action_rate=-0.03,
              termination=-2.0,
          ),
          tracking_sigma=0.20,
          yaw_tracking_sigma=0.35,
          height_sigma=0.004,
          upright_sigma=0.12,
      ),
      command_config=config_dict.create(
          min=[-0.6, 0.0, -1.2],
          max=[0.9, 0.0, 1.2],
          zero_prob=0.15,
          resample_time=4.0,
      ),
      impl="jax",
      naconmax=1024,
      njmax=256,
  )


class Joystick(swingboy_base.SwingboyEnv):
  """Track planar velocity commands while keeping the base near 0.3 m."""

  def __init__(
      self,
      task: str = "flat_terrain",
      config: config_dict.ConfigDict = default_config(),
      config_overrides: Optional[Dict[str, Union[str, int, list[Any]]]] = None,
  ):
    super().__init__(
        xml_path=consts.task_to_xml(task).as_posix(),
        config=config,
        config_overrides=config_overrides,
    )
    self._cmd_min = jp.array(self._config.command_config.min)
    self._cmd_max = jp.array(self._config.command_config.max)
    self._default_leg_pose = self._default_ctrl[:4]

  def sample_command(self, rng: jax.Array) -> jax.Array:
    rng_cmd, rng_zero = jax.random.split(rng)
    cmd = jax.random.uniform(
        rng_cmd, shape=(3,), minval=self._cmd_min, maxval=self._cmd_max
    )
    keep_cmd = jax.random.bernoulli(
        rng_zero, 1.0 - self._config.command_config.zero_prob
    )
    return jp.where(keep_cmd, cmd, jp.zeros(3))

  def reset(self, rng: jax.Array) -> mjx_env.State:
    rng, xy_rng, qvel_rng, cmd_rng, cmd_time_rng = jax.random.split(rng, 5)
    qpos = self._init_q
    qpos = qpos.at[0:2].set(
        qpos[0:2] + jax.random.uniform(xy_rng, (2,), minval=-0.15, maxval=0.15)
    )
    qvel = jp.zeros(self.mjx_model.nv)
    qvel = qvel.at[0:6].set(
        jax.random.uniform(qvel_rng, (6,), minval=-0.05, maxval=0.05)
    )

    data = mjx_env.make_data(
        self.mj_model,
        qpos=qpos,
        qvel=qvel,
        ctrl=self._default_ctrl,
        impl=self.mjx_model.impl.value,
        naconmax=self._config.naconmax,
        njmax=self._config.njmax,
    )
    data = mjx.forward(self.mjx_model, data)

    cmd_steps = jp.round(
        jax.random.exponential(cmd_time_rng)
        * self._config.command_config.resample_time
        / self.dt
    ).astype(jp.int32)
    info = {
        "rng": rng,
        "command": self.sample_command(cmd_rng),
        "steps_until_next_cmd": cmd_steps,
        "last_act": jp.zeros(self.action_size),
        "last_last_act": jp.zeros(self.action_size),
    }

    metrics = {}
    for k in self._config.reward_config.scales.keys():
      metrics[f"reward/{k}"] = jp.zeros(())

    obs = self._get_obs(data, info)
    reward, done = jp.zeros(2)
    return mjx_env.State(data, obs, reward, done, metrics, info)

  def step(self, state: mjx_env.State, action: jax.Array) -> mjx_env.State:
    action = jp.clip(action, -1.0, 1.0)
    ctrl = self._action_to_ctrl(action)
    data = mjx_env.step(self.mjx_model, state.data, ctrl, self.n_substeps)

    done = self._get_termination(data)
    rewards = self._get_reward(data, action, state.info, done)
    rewards = {
        k: jp.nan_to_num(v, nan=0.0, posinf=1000.0, neginf=0.0)
        for k, v in rewards.items()
    }
    rewards = {
        k: v * self._config.reward_config.scales[k] for k, v in rewards.items()
    }
    reward = jp.nan_to_num(
        jp.clip(sum(rewards.values()) * self.dt, 0.0, 10000.0),
        nan=0.0,
        posinf=0.0,
        neginf=0.0,
    )

    state.info["last_last_act"] = state.info["last_act"]
    state.info["last_act"] = action
    state.info["steps_until_next_cmd"] -= 1
    state.info["rng"], cmd_rng, cmd_time_rng = jax.random.split(
        state.info["rng"], 3
    )
    should_resample = state.info["steps_until_next_cmd"] <= 0
    state.info["command"] = jp.where(
        should_resample,
        self.sample_command(cmd_rng),
        state.info["command"],
    )
    state.info["steps_until_next_cmd"] = jp.where(
        done | should_resample,
        jp.round(
            jax.random.exponential(cmd_time_rng)
            * self._config.command_config.resample_time
            / self.dt
        ).astype(jp.int32),
        state.info["steps_until_next_cmd"],
    )

    obs = self._get_obs(data, state.info)
    for k, v in rewards.items():
      state.metrics[f"reward/{k}"] = v

    return state.replace(
        data=data, obs=obs, reward=reward, done=done.astype(reward.dtype)
    )

  def _action_to_ctrl(self, action: jax.Array) -> jax.Array:
    leg_targets = (
        self._default_leg_pose + action[:4] * self._config.leg_action_scale
    )
    wheel_targets = action[4:] * self._config.wheel_action_scale
    ctrl = jp.hstack([leg_targets, wheel_targets])
    return jp.clip(
        ctrl, self._actuator_ctrlrange[:, 0], self._actuator_ctrlrange[:, 1]
    )

  def _get_termination(self, data: mjx.Data) -> jax.Array:
    gravity = self.get_gravity(data)
    base_height = self.get_base_height(data)
    too_low = base_height < self._config.terminate_base_height
    too_high = base_height > self._config.max_base_height
    tipped = gravity[2] > -0.45
    finite = jp.all(jp.isfinite(data.qpos)) & jp.all(jp.isfinite(data.qvel))
    return too_low | too_high | tipped | ~finite

  def _get_obs(
      self, data: mjx.Data, info: Dict[str, Any]
  ) -> Dict[str, jax.Array]:
    rng = info["rng"]

    def noisy(value: jax.Array, scale: float):
      nonlocal rng
      rng, noise_rng = jax.random.split(rng)
      noise = (2 * jax.random.uniform(noise_rng, value.shape) - 1) * scale
      return value + noise * self._config.noise_config.level

    linvel = self.get_local_linvel(data)
    gyro = self.get_gyro(data)
    gravity = self.get_gravity(data)
    leg_pos = data.qpos[self._leg_qpos_ids]
    joint_vel = data.qvel[self._joint_qvel_ids]
    height = jp.array([self.get_base_height(data)])

    state = jp.hstack([
        noisy(linvel, self._config.noise_config.scales.linvel),
        noisy(gyro, self._config.noise_config.scales.gyro),
        noisy(gravity, self._config.noise_config.scales.gravity),
        noisy(height, self._config.noise_config.scales.height)
        - self._config.target_base_height,
        noisy(leg_pos, self._config.noise_config.scales.joint_pos)
        - self._default_leg_pose,
        noisy(joint_vel, self._config.noise_config.scales.joint_vel),
        info["last_act"],
        info["command"],
    ])

    privileged_state = jp.hstack([
        state,
        linvel,
        gyro,
        gravity,
        height,
        leg_pos - self._default_leg_pose,
        joint_vel,
        data.actuator_force,
    ])

    info["rng"] = rng
    return {
        "state": jp.nan_to_num(state),
        "privileged_state": jp.nan_to_num(privileged_state),
    }

  def _get_reward(
      self,
      data: mjx.Data,
      action: jax.Array,
      info: Dict[str, Any],
      done: jax.Array,
  ) -> Dict[str, jax.Array]:
    local_linvel = self.get_local_linvel(data)
    global_linvel = self.get_global_linvel(data)
    global_angvel = self.get_global_angvel(data)
    gyro = self.get_gyro(data)
    gravity = self.get_gravity(data)
    command = info["command"]
    leg_pos = data.qpos[self._leg_qpos_ids]
    wheel_vel = data.qvel[self._wheel_qvel_ids]

    lin_vel_error = jp.square(command[0] - local_linvel[0])
    yaw_vel_error = jp.square(command[2] - gyro[2])
    height_error = jp.square(self.get_base_height(data) - self._config.target_base_height)
    upright_error = jp.sum(jp.square(gravity[:2]))
    cmd_norm = jp.linalg.norm(command)

    return {
        "tracking_lin_vel": jp.exp(
            -lin_vel_error / self._config.reward_config.tracking_sigma
        ),
        "tracking_ang_vel": jp.exp(
            -yaw_vel_error / self._config.reward_config.yaw_tracking_sigma
        ),
        "height": jp.exp(
            -height_error / self._config.reward_config.height_sigma
        ),
        "upright": jp.exp(
            -upright_error / self._config.reward_config.upright_sigma
        ),
        "lin_vel_y": jp.square(local_linvel[1]),
        "lin_vel_z": jp.square(global_linvel[2]),
        "ang_vel_xy": jp.sum(jp.square(global_angvel[:2])),
        "pose": jp.sum(jp.square(leg_pos - self._default_leg_pose)),
        "wheel_idle": jp.sum(jp.square(wheel_vel)) * (cmd_norm < 0.05),
        "torques": jp.sum(jp.square(data.actuator_force)),
        "action_rate": jp.sum(jp.square(action - info["last_act"])),
        "termination": done,
    }
