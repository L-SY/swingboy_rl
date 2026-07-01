"""Base classes for Swingboy."""

from typing import Any, Dict, Optional, Union

from etils import epath
import jax
import jax.numpy as jp
from ml_collections import config_dict
import mujoco
from mujoco import mjx
import numpy as np

from mujoco_playground._src import mjx_env
from mujoco_playground._src.locomotion.go1 import go1_constants
from mujoco_playground._src.locomotion.swingboy import constants as consts


def get_assets() -> Dict[str, bytes]:
  assets: Dict[str, bytes] = {}
  mjx_env.update_assets(assets, consts.XML_DIR, "*.xml")
  mjx_env.update_assets(assets, consts.XML_DIR / "assets")
  mjx_env.update_assets(assets, consts.MESH_DIR, "*.stl")
  mjx_env.update_assets(assets, go1_constants.ROOT_PATH / "xmls" / "assets")
  return assets


class SwingboyEnv(mjx_env.MjxEnv):
  """Base class for Swingboy wheel-legged environments."""

  def __init__(
      self,
      xml_path: str,
      config: config_dict.ConfigDict,
      config_overrides: Optional[Dict[str, Union[str, int, list[Any]]]] = None,
  ) -> None:
    super().__init__(config, config_overrides)

    self._model_assets = get_assets()
    self._mj_model = mujoco.MjModel.from_xml_string(
        epath.Path(xml_path).read_text(), assets=self._model_assets
    )
    self._mj_model.opt.timestep = self.sim_dt
    self._mj_model.opt.ccd_iterations = 20

    self._mj_model.vis.global_.offwidth = 1920
    self._mj_model.vis.global_.offheight = 1080

    self._mjx_model = mjx.put_model(self._mj_model, impl=self._config.impl)
    self._xml_path = xml_path

    self._init_q = jp.array(self._mj_model.keyframe("home").qpos)
    self._default_ctrl = jp.array(self._mj_model.keyframe("home").ctrl)

    self._imu_site_id = self._mj_model.site(consts.IMU_SITE).id
    self._root_body_id = self._mj_model.body(consts.ROOT_BODY).id
    self._floor_geom_id = self._mj_model.geom("floor").id

    self._leg_qpos_ids = jp.array(
        mjx_env.get_qpos_ids(self._mj_model, consts.LEG_JOINTS)
    )
    self._leg_qvel_ids = jp.array(
        mjx_env.get_qvel_ids(self._mj_model, consts.LEG_JOINTS)
    )
    self._wheel_qvel_ids = jp.array(
        mjx_env.get_qvel_ids(self._mj_model, consts.WHEEL_JOINTS)
    )
    self._joint_qvel_ids = jp.array(
        mjx_env.get_qvel_ids(
            self._mj_model, consts.LEG_JOINTS + consts.WHEEL_JOINTS
        )
    )
    self._actuator_ctrlrange = jp.array(self._mj_model.actuator_ctrlrange)

  def get_local_linvel(self, data: mjx.Data) -> jax.Array:
    return mjx_env.get_sensor_data(
        self.mj_model, data, consts.LOCAL_LINVEL_SENSOR
    )

  def get_global_linvel(self, data: mjx.Data) -> jax.Array:
    return mjx_env.get_sensor_data(
        self.mj_model, data, consts.GLOBAL_LINVEL_SENSOR
    )

  def get_global_angvel(self, data: mjx.Data) -> jax.Array:
    return mjx_env.get_sensor_data(
        self.mj_model, data, consts.GLOBAL_ANGVEL_SENSOR
    )

  def get_gyro(self, data: mjx.Data) -> jax.Array:
    return mjx_env.get_sensor_data(self.mj_model, data, consts.GYRO_SENSOR)

  def get_gravity(self, data: mjx.Data) -> jax.Array:
    xmat = data.site_xmat[self._imu_site_id].reshape(3, 3)
    return xmat.T @ jp.array([0.0, 0.0, -1.0])

  def get_base_height(self, data: mjx.Data) -> jax.Array:
    return data.qpos[2]

  @property
  def xml_path(self) -> str:
    return self._xml_path

  @property
  def action_size(self) -> int:
    return self._mjx_model.nu

  @property
  def mj_model(self) -> mujoco.MjModel:
    return self._mj_model

  @property
  def mjx_model(self) -> mjx.Model:
    return self._mjx_model
