# Swingboy RL

This repository is a MuJoCo Playground source checkout with a custom
wheel-legged robot environment under `mujoco_playground/_src/locomotion/swingboy`.

## What Is Included

- `SwingboyJoystickFlatTerrain`: flat-ground velocity-command tracking.
- `SwingboyJoystickRoughTerrain`: rough heightfield terrain; use `--impl=warp`.
- Original Swingboy STL appearance meshes converted to MuJoCo-readable binary
  STL. `base_link` is split into three chunks because MuJoCo limits each STL
  mesh to fewer than 200,000 faces.
- The same STL meshes are also used for collision geometry, per project setup.
- `ros2_ws`: ROS 2 Lyrical + Gazebo Sim workspace for deployment tests with
  STL visual/collision geometry, `ros2_control`, an ONNX RL controller, and
  rough Gazebo test terrain.
- `policies`: exported deployment policies. `swingboy_rough_latest.onnx` is the
  expected ROS controller input after IsaacLab export.

Training outputs are intentionally not tracked:

- `logs/`
- `checkpoints/`
- `.venv/`
- MuJoCo asset caches

## Current IsaacLab Training Path

The active training run uses IsaacLab, not MuJoCo Playground:

```bash
cd /home/lsy/桌面/RL/IsaacLab
PYTHONUNBUFFERED=1 TERM=xterm /home/lsy/桌面/RL/env_isaaclab/bin/isaaclab \
  -p scripts/reinforcement_learning/rsl_rl/train.py \
  --task Isaac-Velocity-RoughMixed-Swingboy-v0 \
  --num_envs 2048 \
  --max_iterations 600 \
  --device cuda:0 \
  --headless \
  --resume \
  --load_run 2026-07-01_17-47-16_wheel_drive_fixed_pose_rough_mixed_stage2_from_flat \
  --checkpoint model_1050_logstd_resetopt.pt \
  --run_name logstd_rough_continue_from_1050
```

Important IsaacLab notes:

- The robot asset uses original STL visual geometry and the same STL files for
  collision.
- Wheel joints are continuous velocity-controlled joints; leg joints are
  position-controlled revolute joints with `[-2.7, 2.7]` rad limits.
- RSL-RL exploration noise is configured with log standard deviation to avoid
  the scalar `std` parameter becoming negative late in training.
- The reward targets velocity tracking and a base height of `0.30 m`.

After training, export the selected checkpoint:

```bash
scripts/export_isaaclab_swingboy_policy.sh \
  /home/lsy/桌面/RL/IsaacLab/logs/rsl_rl/swingboy_rough_mixed/<run>/model_<iter>.pt
```

The script copies the exported ONNX policy to:

```bash
policies/swingboy_rough_latest.onnx
```

Current exported policy:

- IsaacLab checkpoint:
  `/home/lsy/桌面/RL/IsaacLab/logs/rsl_rl/swingboy_rough_mixed/2026-07-01_18-09-56_logstd_rough_continue_from_1050/model_1649.pt`
- Final training metrics at iteration 1649: mean reward `52.76`, mean episode
  length `1000`, `error_vel_xy=0.2154`, `error_vel_yaw=0.3983`, and
  `base_height_l2=-0.0012`.
- Exported ONNX:
  `policies/swingboy_rough_latest.onnx`

## ROS 2 / Gazebo Sim

Build and smoke test:

```bash
cd /home/lsy/桌面/RL/swingboy_rl/ros2_ws
source /opt/ros/lyrical/setup.bash
colcon build --symlink-install
source install/setup.bash
./src/swingboy_tests/scripts/run_gazebo_smoke.sh
```

Run the RL command test after exporting a policy:

```bash
./src/swingboy_tests/scripts/run_gazebo_rl_test.sh
```

The Gazebo controller starts only after the leg and wheel controllers are
active. It warms up from the current Gazebo joint state to the IsaacLab default
standing pose before running the ONNX policy, then clips and low-pass filters
actions before sending them to `ros2_control`.

## Environment Setup

```bash
cd mujoco_playground
uv venv --python 3.12
source .venv/bin/activate
uv pip install -U "jax[cuda12]" --index-url https://pypi.org/simple
uv --no-config sync --extra cuda
```

Check GPU:

```bash
unset LD_LIBRARY_PATH
uv --no-config run python -c "import jax; print(jax.default_backend(), jax.devices())"
```

## Quick Smoke Tests

Flat terrain:

```bash
unset LD_LIBRARY_PATH
export JAX_DEFAULT_MATMUL_PRECISION=highest
export XLA_PYTHON_CLIENT_PREALLOCATE=false

uv --no-config run train-jax-ppo \
  --env_name=SwingboyJoystickFlatTerrain \
  --impl=warp \
  --num_timesteps=8192 \
  --num_evals=1 \
  --num_envs=32 \
  --num_eval_envs=8 \
  --episode_length=100 \
  --batch_size=128 \
  --num_minibatches=4 \
  --num_updates_per_batch=1 \
  --unroll_length=5 \
  --num_videos=1 \
  --suffix=swingboy-flat-smoke
```

Rough terrain:

```bash
unset LD_LIBRARY_PATH
export JAX_DEFAULT_MATMUL_PRECISION=highest
export XLA_PYTHON_CLIENT_PREALLOCATE=false

uv --no-config run train-jax-ppo \
  --env_name=SwingboyJoystickRoughTerrain \
  --impl=warp \
  --num_timesteps=4096 \
  --num_evals=1 \
  --num_envs=16 \
  --num_eval_envs=4 \
  --episode_length=100 \
  --batch_size=64 \
  --num_minibatches=4 \
  --num_updates_per_batch=1 \
  --unroll_length=5 \
  --num_videos=1 \
  --suffix=swingboy-rough-smoke
```

## Longer Training Pattern

Train flat first, then fine-tune rough terrain from the flat checkpoint:

```bash
scripts/train_swingboy_chain.sh
```

For a shorter trial, override the step counts:

```bash
FLAT_STEPS=100000 ROUGH_STEPS=100000 scripts/train_swingboy_chain.sh
```

TensorBoard logging is enabled by default in this script for future runs. Disable
it with:

```bash
USE_TB=false scripts/train_swingboy_chain.sh
```

The equivalent manual commands are:

```bash
uv --no-config run train-jax-ppo \
  --env_name=SwingboyJoystickFlatTerrain \
  --impl=warp \
  --num_timesteps=5000000 \
  --num_evals=10 \
  --num_envs=128 \
  --num_eval_envs=32 \
  --episode_length=500 \
  --batch_size=256 \
  --num_minibatches=8 \
  --num_updates_per_batch=2 \
  --unroll_length=10 \
  --num_videos=1 \
  --suffix=swingboy-flat-long \
  --use_tb
```

```bash
uv --no-config run train-jax-ppo \
  --env_name=SwingboyJoystickRoughTerrain \
  --impl=warp \
  --load_checkpoint_path=logs/<flat-run>/checkpoints \
  --num_timesteps=5000000 \
  --num_evals=10 \
  --num_envs=32 \
  --num_eval_envs=8 \
  --episode_length=500 \
  --batch_size=128 \
  --num_minibatches=4 \
  --num_updates_per_batch=1 \
  --unroll_length=10 \
  --num_videos=1 \
  --suffix=swingboy-rough-long \
  --use_tb
```

## TensorBoard

The current run only has console reward logs because it was started before
TensorBoard logging was enabled in `scripts/train_swingboy_chain.sh`. For future
runs:

```bash
uv --no-config run --with tensorboard tensorboard --logdir logs --port 6006
```

Then open `http://localhost:6006`.

## Keyboard Play

After a checkpoint exists, run the trained policy in a live MuJoCo viewer:

```bash
uv --no-config run python scripts/play_swingboy_keyboard.py \
  --checkpoint logs/SwingboyJoystickRoughTerrain-20260701-101409-swingboy-rough-long/checkpoints \
  --terrain rough
```

Controls:

- `W` / `S`: increase or decrease forward velocity command.
- `A` / `D`: increase or decrease yaw-rate command.
- `X` or `Space`: stop.
- `R`: reset.

## Notes

- Full STL collision is significantly slower than primitive collision and may
  emit MuJoCo MJX mesh warnings. Warp is the recommended implementation for
  this setup because the original CAD meshes are also used for collisions.
- If training becomes unstable, the first thing to tune is wheel action scale,
  command range, and collision mesh complexity.
