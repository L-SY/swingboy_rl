from setuptools import find_packages, setup

package_name = "swingboy_rl_controller"

setup(
    name=package_name,
    version="0.1.0",
    packages=find_packages(exclude=["test"]),
    data_files=[
        ("share/ament_index/resource_index/packages", [f"resource/{package_name}"]),
        (f"share/{package_name}", ["package.xml"]),
    ],
    install_requires=["setuptools"],
    zip_safe=True,
    maintainer="lsy",
    maintainer_email="lsy@example.com",
    description="ONNX policy runner for Swingboy ros2_control commands.",
    license="Apache-2.0",
    entry_points={
        "console_scripts": [
            "swingboy_rl_controller = swingboy_rl_controller.rl_controller:main",
        ],
    },
)
