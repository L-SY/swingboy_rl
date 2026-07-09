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
  position-controlled revolute joints. Hip limits are `0..130 deg`
  (`0..2.268928 rad`), and knee limits are `0..290 deg`
  (`0..5.061455 rad`).
- The mechanical calibration/reset pose is hip `130 deg` and knee `0 deg` on
  both sides. With the current STL geometry this places the wheel bottom about
  `0.158 m` below `base_link`, so training resets near `base_z=0.17 m`.
- The policy action offset, i.e. the target commanded by zero leg actions, is
  hip `130 deg` and knee `50 deg` on both sides. This gives a wheel-on-ground
  base height near `0.35 m`. ROS 2 deployment uses the same separation:
  observations are relative to the calibration pose, while leg actions are
  applied around the extended standing offset.
- RSL-RL exploration noise is configured with log standard deviation to avoid
  the scalar `std` parameter becoming negative late in training.
- The stand/track reward targets velocity tracking while holding the base near
  `0.35 m`.

## IsaacLab Recovery Task

The current workflow should be staged. Train stand/slow walking first from the
default standing pose, then fine-tune recovery from harder resets.

Stand-first task:

```bash
HEADLESS=false RENDERING_MODE=performance NUM_ENVS=4096 MAX_ITERATIONS=3000 \
  RUN_NAME=stand_default_pose_gui \
  scripts/train_isaaclab_swingboy_stand.sh
```

This task keeps the same deployment-style 27-value observation as recovery. It
resets from the mechanical calibration pose, but a zero leg action commands the
extended standing target. The base height target is `0.35 m`, falls terminate
quickly, and push disturbances stay disabled until the robot can stay upright.
Hip-link contact is penalized but not a terminal condition in this stand-only
phase, because the robot starts from a low calibration pose and needs room to
learn the get-up transient. Sustained hip-link contact termination is restored
for the velocity-tracking phase. Wheel action scale is kept large enough for
two-wheel self-balancing, while leg action scales are joint-specific: hip
`0.35 rad`, knee `0.75 rad`. The stand phase also has a post-grace low-height
termination: after `2.0 s`, episodes below `0.26 m` are reset instead of being
counted as successful timeouts.

The left/right symmetry reward compares the hip-to-wheel line pitch angle in the
base frame instead of raw hip/knee joint equality. It fades out as commanded yaw
rate increases, so turning policies may use asymmetric leg geometry.

Velocity tracking curriculum from scratch:

```bash
HEADLESS=false \
  NUM_ENVS=2048 MAX_ITERATIONS=10000 \
  RUN_NAME=track_velocity_curriculum_from_zero \
  scripts/train_isaaclab_swingboy_track.sh
```

The tracking task starts from the calibration reset pose and immediately
commands the extended standing action offset, but does not need to
resume a checkpoint. Command velocity ranges are expanded by an IsaacLab
curriculum term only when recent reset episodes have high timeout success, low
fall/contact termination rate, and sufficient `track_lin_vel_xy_exp` /
`track_ang_vel_z_exp` episode reward. TensorBoard logs the active level and
metrics under `Curriculum/command_velocity/*`.
The first command level uses relaxed thresholds (`success>=0.82`,
`termination<=0.20`) and later levels tighten progressively. Track PPO uses a
moderate exploration setup (`init_noise_std=0.25`, `entropy_coef=0.002`) so the
from-scratch policy can discover balancing without letting the action standard
deviation grow too aggressively.

For the current recovery-first experiment, use:

```bash
cd /home/lsy/桌面/RL/IsaacLab
PYTHONUNBUFFERED=1 TERM=xterm /home/lsy/桌面/RL/env_isaaclab/bin/isaaclab \
  -p scripts/reinforcement_learning/rsl_rl/train.py \
  --task Isaac-Velocity-Recovery-Swingboy-v0 \
  --num_envs 2048 \
  --max_iterations 1800 \
  --device cuda:0 \
  --headless \
  --run_name recovery_zero_joints_noscan_nobaselin
```

This task intentionally removes policy access to base linear velocity and
height scan. The actor/critic observation is 27 values:

- base angular velocity: 3
- projected gravity: 3
- velocity command: 3
- relative joint position: 6
- joint velocity: 6
- previous action: 6

The reset keeps the IsaacLab standing pose as the action offset, but starts the
episode with all joint positions scaled to zero. This lets the policy command
the standing target easily while still learning from the zero-joint initial
state.

Recovery termination is delayed instead of immediate:

- `time_out`
- `base_contact`: terminate only after `base_link` contact force stays above
  `1.0 N` continuously for `1.25 s`

The recovery rewards keep velocity tracking but prioritize standing:

- base height target: `0.32 m`, weight `-120`
- low base penalty below `0.28 m`, weight `-80`
- flat base orientation, weight `-8`
- left/right hip and knee symmetry, weight `-0.35`
- base contact force penalty, weight `-0.06`
- non-wheel leg link contact force penalty, weight `-0.12`
- termination penalty, weight `-8`
- mostly standing / slow commands at the start of training
- interval push disturbance every `3-6 s`, applied as root velocity impulses

Open a GUI training run:

```bash
HEADLESS=false RENDERING_MODE=performance NUM_ENVS=4096 MAX_ITERATIONS=10000 \
  RUN_NAME=recovery_height_sym_push_gui \
  scripts/train_isaaclab_swingboy_recovery.sh
```

Resume a GUI run from a checkpoint:

```bash
HEADLESS=false RESUME=true \
  LOAD_RUN=2026-07-02_11-10-41_recovery_4096env_10000iter_20260702_111037 \
  CHECKPOINT=model_550.pt \
  NUM_ENVS=4096 MAX_ITERATIONS=10000 \
  RUN_NAME=recovery_height_sym_push_gui_from_550 \
  scripts/train_isaaclab_swingboy_recovery.sh
```

Export a recovery policy to a separate ONNX file:

```bash
TASK=Isaac-Velocity-Recovery-Swingboy-Play-v0 \
POLICY_OUT=/home/lsy/桌面/RL/swingboy_rl/policies/swingboy_recovery_latest.onnx \
scripts/export_isaaclab_swingboy_policy.sh \
  /home/lsy/桌面/RL/IsaacLab/logs/rsl_rl/swingboy_recovery_noscan_nobaselin/<run>/model_<iter>.pt
```

The ROS 2 controller auto-detects the ONNX input size:

- `206`: rough policy with base linear velocity and height scan
- `30`: flat policy with base linear velocity and no height scan
- `27`: recovery policy with no base linear velocity and no height scan

After training, export the selected checkpoint:

```bash
scripts/export_isaaclab_swingboy_policy.sh \
  /home/lsy/桌面/RL/IsaacLab/logs/rsl_rl/swingboy_rough_mixed/<run>/model_<iter>.pt
```

The script copies the exported ONNX policy to:

```bash
policies/swingboy_track_latest.onnx
```

Current exported policy:

- IsaacLab checkpoint:
  `/home/lsy/桌面/RL/IsaacLab/logs/rsl_rl/swingboy_stand_noscan_nobaselin/2026-07-02_16-38-33_track_velocity_curriculum_mid_entropy_from_zero_gui_20260702_163826/model_1200.pt`
- Candidate metrics near iteration 1200: curriculum level `4`, mean reward
  `20.89`, mean episode length `594.16`, timeout `0.9341`,
  `root_height=0.0176`, `base_contact=0.0037`, and `hip_link_contact=0.0446`.
- This candidate is preferred over the final `model_9999.pt` because the late
  training action standard deviation became numerically unstable.
- Exported ONNX:
  `policies/swingboy_track_latest.onnx`
- Observation layout:
  `27` values, no base linear velocity and no height scan.
- This policy was trained with the previous standing pose and is obsolete after
  the hip/knee limit and default-pose change. Retrain and export a new
  `policies/swingboy_track_latest.onnx` before using it as the deployment
  default.

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

Open the live Gazebo GUI with the exported policy:

```bash
ros2 launch swingboy_bringup gazebo_rl.launch.py \
  gui:=true \
  use_rl:=true \
  policy_path:=/home/lsy/桌面/RL/swingboy_rl/policies/swingboy_track_latest.onnx \
  use_height_scan:=false
```

Then send keyboard velocity commands from another terminal:

```bash
ros2 run swingboy_rl_controller swingboy_keyboard_teleop
```

The Gazebo controller starts only after the leg and wheel controllers are
active. It warms up from the current Gazebo joint state to the IsaacLab default
standing pose before running the ONNX policy, then clips and low-pass filters
actions before sending them to `ros2_control`.

The launch also starts `swingboy_height_scan_publisher`, which publishes the
same 176-value height-scan shape used by the IsaacLab rough-terrain policy for
the procedural `rough_test.sdf` world.

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
