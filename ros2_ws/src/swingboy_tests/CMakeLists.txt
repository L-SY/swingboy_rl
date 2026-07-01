cmake_minimum_required(VERSION 3.16)
project(swingboy_tests)

find_package(ament_cmake REQUIRED)

install(PROGRAMS
  scripts/run_gazebo_smoke.sh
  scripts/run_gazebo_rl_test.sh
  DESTINATION lib/${PROJECT_NAME}
)

ament_package()
