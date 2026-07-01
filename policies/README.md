# Policies

Place exported IsaacLab policies here.

Expected deployment file:

- `swingboy_rough_latest.onnx`

The ONNX policy should be exported from the same IsaacLab observation/action
setup documented in `ros2_ws/README.md`. The ROS controller also supports an
empty `policy_path`; in that mode it only holds the default standing pose and
sends zero wheel velocity, which is useful for Gazebo smoke tests.
