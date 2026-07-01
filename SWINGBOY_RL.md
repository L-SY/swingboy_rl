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

Training outputs are intentionally not tracked:

- `logs/`
- `checkpoints/`
- `.venv/`
- MuJoCo asset caches

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
