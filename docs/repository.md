# Repository conventions

## Ownership

- `assets/meshes/` is the only canonical copy of the original Swingboy STL
  geometry. Simulator-specific converted or split meshes may live beside the
  simulator files that consume them.
- `sim/isaaclab/` contains files authored or modified for the DDT_Lab task.
- `sim/mujoco/` contains the pinned MuJoCo Playground source tree and the
  Swingboy environment built on it.
- `ros2_ws/src/` contains deployable ROS 2 packages only.
- `policies/<version>/` contains inference exports and a `metadata.yaml` file.
- `ref/` contains read-only upstream examples. Production code must not import
  modules from `ref/`.

## Generated files

Do not commit `logs/`, `checkpoints/`, ROS `build/install/log`, TensorBoard
events, or simulator caches. Full optimizer checkpoints should be attached to
a GitHub release when they are needed; only compact deployment exports belong
under `policies/`.

## Third-party updates

Update `third_party/versions.yaml` whenever an upstream checkout changes. Keep
local changes in an overlay or patch instead of editing an untracked upstream
checkout without recording the revision.
