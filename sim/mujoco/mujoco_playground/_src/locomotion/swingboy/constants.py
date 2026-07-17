"""Constants for Swingboy locomotion environments."""

from etils import epath

ROOT_PATH = epath.Path(__file__).parent
XML_DIR = ROOT_PATH / "xmls"
ROBOT_DIR = ROOT_PATH.parents[4] / "swingboy_v1"
MESH_DIR = ROBOT_DIR / "meshes"

ROOT_BODY = "base_link"
IMU_SITE = "imu"

FLAT_TERRAIN_XML = XML_DIR / "scene_flat.xml"
ROUGH_TERRAIN_XML = XML_DIR / "scene_rough.xml"

LEG_JOINTS = (
    "left_hip",
    "left_knee",
    "right_hip",
    "right_knee",
)
WHEEL_JOINTS = (
    "left_wheel",
    "right_wheel",
)
ACTUATOR_ORDER = LEG_JOINTS + WHEEL_JOINTS

LOCAL_LINVEL_SENSOR = "local_linvel"
GLOBAL_LINVEL_SENSOR = "global_linvel"
GLOBAL_ANGVEL_SENSOR = "global_angvel"
GYRO_SENSOR = "gyro"


def task_to_xml(task: str) -> epath.Path:
  if task == "flat_terrain":
    return FLAT_TERRAIN_XML
  if task == "rough_terrain":
    return ROUGH_TERRAIN_XML
  raise ValueError(f"Unknown Swingboy task: {task}")

