# MuJoCo simulation

This directory contains the MuJoCo Playground Python package and its learning
entry points. The Swingboy environment is under
`mujoco_playground/_src/locomotion/swingboy/`.

Install from this directory so the package layout remains standard:

```bash
cd sim/mujoco
uv sync --extra cuda --extra learning
```

The upstream project metadata retained for reference is under
`../../ref/mujoco_playground/`.
