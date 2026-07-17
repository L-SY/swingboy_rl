# Versioned policies

Each policy version has its own directory and metadata describing the exact
observation/action contract.

- `v0.1.0-legacy/`: legacy IsaacLab policies used by the current ROS 2
  controller.
- `v0.2.0-ddt/`: DDT_Lab NP3O export from the Tita-style Swingboy task. This
  policy uses the NP3O history interface and is not yet compatible with the
  legacy ROS 2 controller.

Full optimizer checkpoints and TensorBoard logs are release artifacts, not
repository source files.
