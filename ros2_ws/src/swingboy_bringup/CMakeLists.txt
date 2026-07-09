cmake_minimum_required(VERSION 3.16)
project(swingboy_bringup)

find_package(ament_cmake REQUIRED)

install(DIRECTORY config launch rviz worlds
  DESTINATION share/${PROJECT_NAME}
)

ament_package()
