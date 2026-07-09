import os

from launch import LaunchDescription
from launch.actions import (
    DeclareLaunchArgument,
    ExecuteProcess,
    OpaqueFunction,
    RegisterEventHandler,
    SetEnvironmentVariable,
    TimerAction,
)
from launch.conditions import IfCondition
from launch.event_handlers import OnProcessExit
from launch.substitutions import Command, LaunchConfiguration, PathJoinSubstitution
from launch_ros.actions import Node
from launch_ros.substitutions import FindPackageShare


def _join_env_paths(*paths):
    return ":".join(path for path in paths if path)


def launch_setup(context, *args, **kwargs):
    description_share = FindPackageShare("swingboy_description")
    bringup_share = FindPackageShare("swingboy_bringup")
    description_share_path = description_share.perform(context)
    description_parent_path = os.path.dirname(description_share_path)

    world = LaunchConfiguration("world").perform(context)
    if not world:
        world = PathJoinSubstitution([bringup_share, "worlds", "rough_test.sdf"]).perform(context)

    controllers_file = PathJoinSubstitution([bringup_share, "config", "controllers.yaml"])
    robot_xacro = PathJoinSubstitution([description_share, "urdf", "swingboy.urdf.xacro"])
    robot_description = {
        "robot_description": Command(
            [
                "xacro ",
                robot_xacro,
                " controllers_file:=",
                controllers_file,
            ]
        )
    }

    gz_server = Node(
        package="ros_gz_sim",
        executable="gzserver",
        output="screen",
        parameters=[
            {
                "world_sdf_file": world,
                "initial_sim_time": 0.0,
                "verbosity_level": 3,
            }
        ],
    )
    gz_gui = ExecuteProcess(
        cmd=["gz", "sim", "-g"],
        output="screen",
        condition=IfCondition(LaunchConfiguration("gui")),
    )

    robot_state_publisher = Node(
        package="robot_state_publisher",
        executable="robot_state_publisher",
        output="screen",
        parameters=[robot_description, {"use_sim_time": True}],
    )

    bridge = Node(
        package="ros_gz_bridge",
        executable="parameter_bridge",
        output="screen",
        arguments=[
            "/clock@rosgraph_msgs/msg/Clock[gz.msgs.Clock",
            "/swingboy/imu@sensor_msgs/msg/Imu[gz.msgs.IMU",
            "/model/swingboy/odometry@nav_msgs/msg/Odometry[gz.msgs.Odometry",
        ],
        remappings=[
            ("/model/swingboy/odometry", "/swingboy/odom"),
        ],
        parameters=[{"use_sim_time": True}],
    )

    spawn_robot = Node(
        package="ros_gz_sim",
        executable="create",
        output="screen",
        arguments=[
            "-name",
            "swingboy",
            "-topic",
            "robot_description",
            "-x",
            LaunchConfiguration("x"),
            "-y",
            LaunchConfiguration("y"),
            "-z",
            LaunchConfiguration("z"),
        ],
        parameters=[{"use_sim_time": True}],
    )

    spawn_joint_state = Node(
        package="controller_manager",
        executable="spawner",
        output="screen",
        arguments=["joint_state_broadcaster", "--controller-manager", "/controller_manager"],
        parameters=[{"use_sim_time": True}],
    )
    spawn_legs = Node(
        package="controller_manager",
        executable="spawner",
        output="screen",
        arguments=[
            "swingboy_leg_controller",
            "--controller-manager",
            "/controller_manager",
            "--param-file",
            controllers_file,
        ],
        parameters=[{"use_sim_time": True}],
    )
    spawn_wheels = Node(
        package="controller_manager",
        executable="spawner",
        output="screen",
        arguments=[
            "swingboy_wheel_controller",
            "--controller-manager",
            "/controller_manager",
            "--param-file",
            controllers_file,
        ],
        parameters=[{"use_sim_time": True}],
    )

    rl_controller = Node(
        package="swingboy_rl_controller",
        executable="swingboy_rl_controller",
        name="swingboy_rl_controller",
        output="screen",
        condition=IfCondition(LaunchConfiguration("use_rl")),
        parameters=[
            {
                "use_sim_time": True,
                "policy_path": LaunchConfiguration("policy_path"),
                "publish_rate_hz": LaunchConfiguration("policy_rate"),
            }
        ],
    )

    height_scan_publisher = Node(
        package="swingboy_rl_controller",
        executable="swingboy_height_scan_publisher",
        name="swingboy_height_scan_publisher",
        output="screen",
        condition=IfCondition(LaunchConfiguration("use_height_scan")),
        parameters=[
            {
                "use_sim_time": True,
                "publish_rate_hz": LaunchConfiguration("height_scan_rate"),
            }
        ],
    )

    return [
        SetEnvironmentVariable(
            "GZ_SIM_RESOURCE_PATH",
            _join_env_paths(
                description_parent_path,
                description_share_path,
                os.environ.get("GZ_SIM_RESOURCE_PATH", ""),
            ),
        ),
        SetEnvironmentVariable(
            "GZ_SIM_SYSTEM_PLUGIN_PATH",
            _join_env_paths(
                "/opt/ros/lyrical/lib",
                os.environ.get("GZ_SIM_SYSTEM_PLUGIN_PATH", ""),
            ),
        ),
        gz_server,
        TimerAction(period=1.0, actions=[gz_gui]),
        robot_state_publisher,
        bridge,
        height_scan_publisher,
        TimerAction(period=2.0, actions=[spawn_robot]),
        TimerAction(period=5.0, actions=[spawn_joint_state, spawn_legs, spawn_wheels]),
        RegisterEventHandler(
            OnProcessExit(
                target_action=spawn_legs,
                on_exit=[TimerAction(period=0.5, actions=[rl_controller])],
            )
        ),
    ]


def generate_launch_description():
    return LaunchDescription(
        [
            DeclareLaunchArgument("world", default_value=""),
            DeclareLaunchArgument("headless", default_value="false"),
            DeclareLaunchArgument("gui", default_value="false"),
            DeclareLaunchArgument("paused", default_value="false"),
            DeclareLaunchArgument("use_rl", default_value="true"),
            DeclareLaunchArgument("use_height_scan", default_value="false"),
            DeclareLaunchArgument(
                "policy_path",
                default_value="/home/lsy/桌面/RL/swingboy_rl/policies/swingboy_track_latest.onnx",
            ),
            DeclareLaunchArgument("policy_rate", default_value="50.0"),
            DeclareLaunchArgument("height_scan_rate", default_value="50.0"),
            DeclareLaunchArgument("x", default_value="0.0"),
            DeclareLaunchArgument("y", default_value="0.0"),
            DeclareLaunchArgument("z", default_value="0.35"),
            OpaqueFunction(function=launch_setup),
        ]
    )
