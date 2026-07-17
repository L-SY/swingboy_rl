# Swingboy RL

Reinforcement-learning environments, robot assets, deployment code, and
reference material for the Swingboy two-wheel-legged robot.

## Repository layout

```text
swingboy_rl/
├── docs/                 Project and training documentation
├── assets/meshes/        Canonical source STL meshes
├── sim/isaaclab/         Isaac Lab / DDT_Lab overlay and robot URDF
├── sim/mujoco/           MuJoCo Playground source and learning tools
├── ros2_ws/src/          ROS 2 description, bringup, controller, and tests
├── policies/<version>/   Versioned deployment policies and metadata
├── note/                 Interactive readiness and experiment notebook
├── scripts/              Training, export, play, and diagnostic commands
├── third_party/          Reproducible upstream version pins
└── ref/                  Selected open-source reference files
```

Start with [the training notes](docs/training.md), the
[interactive project notebook](note/README.md), the
[Isaac Lab integration](sim/isaaclab/README.md), or the
[ROS 2 workspace](ros2_ws/README.md). Exact upstream revisions are recorded in
[`third_party/versions.yaml`](third_party/versions.yaml).

Generated training logs, checkpoints, ROS build products, and local Python
environments are intentionally excluded from Git. Deployment exports are kept
under `policies/` with version-specific metadata.
