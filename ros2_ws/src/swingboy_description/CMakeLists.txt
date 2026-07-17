cmake_minimum_required(VERSION 3.16)
project(swingboy_description)

find_package(ament_cmake REQUIRED)

install(DIRECTORY urdf
  DESTINATION share/${PROJECT_NAME}
)

install(DIRECTORY "${CMAKE_CURRENT_SOURCE_DIR}/../../../assets/meshes/"
  DESTINATION share/${PROJECT_NAME}/meshes
)

ament_package()
