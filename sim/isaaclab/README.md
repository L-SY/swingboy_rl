# Isaac Lab / DDT_Lab integration

The current task is an overlay for DDT_Lab pinned in
`../../third_party/versions.yaml`. It contains:

- the Swingboy articulation and Tita-style flat velocity task;
- the NP3O runner checkpoint/resume fixes;
- the URDF used by Isaac Sim;
- canonical meshes linked from `../../assets/meshes/`.

Apply the overlay to a clean DDT_Lab checkout:

```bash
./sim/isaaclab/install_ddt_overlay.sh /path/to/DDT_Lab
```

The registered training task is `DDT-Velocity-Flat-Swingboy-v0`. The play task
is `DDT-Velocity-Flat-Swingboy-Play-v0`.
