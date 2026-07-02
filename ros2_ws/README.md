# Swingboy ROS 2 / Gazebo Sim

This workspace contains the ROS 2 and Gazebo Sim side of the Swingboy setup.
It is intentionally separate from the IsaacLab checkout used for training.

Packages:

- `swingboy_description`: STL visual/collision robot model with `ros2_control` interfaces.
- `swingboy_bringup`: Gazebo Sim launch, controller configuration, and rough test world.
- `swingboy_rl_controller`: Python ONNX policy runner that sends commands to ros2_control.
- `swingboy_height_scan_publisher`: IsaacLab-style height scan publisher for `rough_test.sdf`.
- `swingboy_tests`: smoke-test scripts for launching the simulation.

Build:

```bash
cd /home/lsy/桌面/RL/swingboy_rl/ros2_ws
sudo apt install python3-onnxruntime
source /opt/ros/lyrical/setup.bash
colcon build --symlink-install
source install/setup.bash
```

Launch Gazebo without RL policy, holding the learned standing pose:

```bash
ros2 launch swingboy_bringup gazebo_rl.launch.py use_rl:=false
```

Launch with an exported ONNX policy:

```bash
ros2 launch swingboy_bringup gazebo_rl.launch.py \
  gui:=true \
  use_rl:=true \
  policy_path:=/home/lsy/桌面/RL/swingboy_rl/policies/swingboy_rough_latest.onnx
```

Keyboard control in another terminal:

```bash
cd /home/lsy/桌面/RL/swingboy_rl/ros2_ws
source /opt/ros/lyrical/setup.bash
source install/setup.bash
ros2 run swingboy_rl_controller swingboy_keyboard_teleop
```

Controls: `W/S` changes forward speed, `A/D` changes yaw rate, `X` or space
stops, and `Q` quits.

The controller mirrors the IsaacLab action scaling: four leg position actions
with scale `0.30` and two wheel velocity actions with scale `12.0`.
For Gazebo deployment, it also applies a startup warmup, action clipping, and a
low-pass filter before publishing to `ros2_control`. The defaults are:

- `warmup_duration_s=3.0`
- `leg_action_clip=2.0`
- `wheel_action_clip=3.4`
- `action_filter_alpha=0.35`
- `leg_target_rate_limit=4.0 rad/s`

The launch file starts `swingboy_height_scan_publisher` by default. It publishes
176 height-scan values for the procedural geometry in `rough_test.sdf`, using
the IsaacLab convention `base_z - terrain_z - 0.5`. If no
`/swingboy/height_scan` publisher is present, the controller falls back to
`-0.2`, matching the approximate flat-ground value for a `0.30 m` base height.

Smoke test:

```bash
./src/swingboy_tests/scripts/run_gazebo_smoke.sh
```

RL command test after exporting a policy:

```bash
./src/swingboy_tests/scripts/run_gazebo_rl_test.sh
```

The rough Gazebo world is `swingboy_bringup/worlds/rough_test.sdf`. It contains
flat ground, shallow ramps, small uneven blocks, and a skate-style bank. The
current ROS controller accepts `/cmd_vel`, consumes `/swingboy/height_scan`, and
runs the exported IsaacLab policy through ONNX Runtime.
