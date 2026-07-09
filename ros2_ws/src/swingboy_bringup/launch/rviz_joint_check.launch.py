from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.conditions import IfCondition, UnlessCondition
from launch.substitutions import Command, LaunchConfiguration, PathJoinSubstitution
from launch_ros.actions import Node
from launch_ros.substitutions import FindPackageShare


def generate_launch_description():
    robot_xacro = PathJoinSubstitution(
        [FindPackageShare("swingboy_description"), "urdf", "swingboy.urdf.xacro"]
    )
    rviz_config = PathJoinSubstitution(
        [FindPackageShare("swingboy_bringup"), "rviz", "swingboy_joint_check.rviz"]
    )
    use_gui = LaunchConfiguration("use_gui")
    use_rviz = LaunchConfiguration("use_rviz")

    robot_description = {
        "robot_description": Command(
            [
                "xacro ",
                robot_xacro,
                " use_ros2_control:=false",
            ]
        )
    }

    return LaunchDescription(
        [
            DeclareLaunchArgument("use_gui", default_value="true"),
            DeclareLaunchArgument("use_rviz", default_value="true"),
            Node(
                package="robot_state_publisher",
                executable="robot_state_publisher",
                name="robot_state_publisher",
                output="screen",
                parameters=[robot_description],
            ),
            Node(
                package="joint_state_publisher_gui",
                executable="joint_state_publisher_gui",
                name="joint_state_publisher_gui",
                output="screen",
                parameters=[robot_description],
                condition=IfCondition(use_gui),
            ),
            Node(
                package="joint_state_publisher",
                executable="joint_state_publisher",
                name="joint_state_publisher",
                output="screen",
                parameters=[robot_description],
                condition=UnlessCondition(use_gui),
            ),
            Node(
                package="rviz2",
                executable="rviz2",
                name="rviz2",
                output="screen",
                arguments=["-d", rviz_config],
                condition=IfCondition(use_rviz),
            ),
        ]
    )
