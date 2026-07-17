# Copyright (c) 2022-2025, The Isaac Lab Project Developers.
# All rights reserved.
#
# SPDX-License-Identifier: BSD-3-Clause

"""Swingboy flat-ground task using the validated Tita training structure."""

import ddt_lab.tasks.manager_based.locomotion.mdp as mdp
from ddt_lab.assets.ddt_robot import DDT_SWINGBOY_CFG
from isaaclab.managers import ObservationTermCfg as ObsTerm
from isaaclab.managers import RewardTermCfg as RewTerm
from isaaclab.managers import SceneEntityCfg
from isaaclab.managers import TerminationTermCfg as DoneTerm
from isaaclab.utils import configclass
from isaaclab.utils.noise import AdditiveUniformNoiseCfg as Unoise

from ..tita.flat_env_cfg import TitaFlatEnvCfg
from ..tita.rough_env_cfg import (
    ActionsCfg as TitaActionsCfg,
    CommandsCfg,
    EventCfg,
    ObservationsCfg as TitaObservationsCfg,
    RewardsCfg as TitaRewardsCfg,
    SceneCfg as TitaSceneCfg,
    TerminationsCfg as TitaTerminationsCfg,
)


LEG_JOINTS = ["left_hip", "left_knee", "right_hip", "right_knee"]
WHEEL_JOINTS = ["left_wheel", "right_wheel"]
WHEEL_BODIES = ["left_wheel", "right_wheel"]
LOWER_LEG_BODIES = ["left_knee_wheel_link", "right_knee_wheel_link"]
HIP_KNEE_BODIES = ["left_hip_knee_link", "right_hip_knee_link"]


@configclass
class SceneCfg(TitaSceneCfg):
    robot = DDT_SWINGBOY_CFG.replace(prim_path="{ENV_REGEX_NS}/Robot")


@configclass
class ActionsCfg(TitaActionsCfg):
    joint_pos_0 = mdp.JointPositionActionCfg(
        asset_name="robot",
        joint_names=["left_hip"],
        clip={".*": (-100.0, 100.0)},
        scale=0.25,
        use_default_offset=True,
        preserve_order=True,
    )
    joint_pos_1 = mdp.JointPositionActionCfg(
        asset_name="robot",
        joint_names=["left_knee"],
        clip={".*": (-100.0, 100.0)},
        scale=0.25,
        use_default_offset=True,
        preserve_order=True,
    )
    joint_vel_2 = mdp.JointVelocityActionCfg(
        asset_name="robot",
        joint_names=["left_wheel"],
        clip={".*": (-100.0, 100.0)},
        scale=5.0,
        use_default_offset=True,
        preserve_order=True,
    )
    joint_pos_3 = mdp.JointPositionActionCfg(
        asset_name="robot",
        joint_names=["right_hip"],
        clip={".*": (-100.0, 100.0)},
        scale=0.25,
        use_default_offset=True,
        preserve_order=True,
    )
    joint_pos_4 = mdp.JointPositionActionCfg(
        asset_name="robot",
        joint_names=["right_knee"],
        clip={".*": (-100.0, 100.0)},
        scale=0.25,
        use_default_offset=True,
        preserve_order=True,
    )
    joint_vel_5 = mdp.JointVelocityActionCfg(
        asset_name="robot",
        joint_names=["right_wheel"],
        clip={".*": (-100.0, 100.0)},
        scale=-5.0,
        use_default_offset=True,
        preserve_order=True,
    )

    # Remove Tita-only action terms inherited by name.
    joint_pos_2 = None
    joint_vel_3 = None
    joint_pos_5 = None
    joint_pos_6 = None
    joint_vel_7 = None


@configclass
class ObservationsCfg(TitaObservationsCfg):
    @configclass
    class PolicyCfg(TitaObservationsCfg.PolicyCfg):
        joint_pos = ObsTerm(
            func=mdp.joint_pos_rel_without_wheel,
            params={
                "asset_cfg": SceneEntityCfg("robot", joint_names=".*", preserve_order=True),
                "wheel_asset_cfg": SceneEntityCfg("robot", joint_names=".*_wheel"),
            },
            noise=Unoise(n_min=-0.01, n_max=0.01),
            clip=(-100.0, 100.0),
            scale=1.0,
        )
        joint_vel = ObsTerm(
            func=mdp.joint_vel_rel,
            params={"asset_cfg": SceneEntityCfg("robot", joint_names=".*", preserve_order=True)},
            noise=Unoise(n_min=-1.5, n_max=1.5),
            clip=(-100.0, 100.0),
            scale=0.05,
        )

    @configclass
    class CriticCfg(TitaObservationsCfg.CriticCfg):
        joint_pos = ObsTerm(
            func=mdp.joint_pos_rel_without_wheel,
            params={
                "asset_cfg": SceneEntityCfg("robot", joint_names=".*", preserve_order=True),
                "wheel_asset_cfg": SceneEntityCfg("robot", joint_names=".*_wheel"),
            },
            clip=(-100.0, 100.0),
            scale=1.0,
        )
        joint_vel = ObsTerm(
            func=mdp.joint_vel_rel,
            params={"asset_cfg": SceneEntityCfg("robot", joint_names=".*", preserve_order=True)},
            clip=(-100.0, 100.0),
            scale=0.05,
        )

    @configclass
    class PrivCfg(TitaObservationsCfg.PrivCfg):
        contact_state = ObsTerm(
            func=mdp.contact_state,
            params={"sensor_cfg": SceneEntityCfg("contact_forces", body_names=WHEEL_BODIES)},
            clip=(-1.0, 1.0),
            scale=1.0,
        )
        joint_kp_factor = ObsTerm(
            func=mdp.joint_kp_factor,
            params={"asset_cfg": SceneEntityCfg("robot", joint_names=".*", preserve_order=True)},
            clip=(0.0, 2.0),
            scale=1.0,
        )
        joint_kd_factor = ObsTerm(
            func=mdp.joint_kd_factor,
            params={"asset_cfg": SceneEntityCfg("robot", joint_names=".*", preserve_order=True)},
            clip=(0.0, 2.0),
            scale=1.0,
        )

    policy: PolicyCfg = PolicyCfg()
    critic: CriticCfg = CriticCfg()
    priv: PrivCfg = PrivCfg()


@configclass
class RewardsCfg(TitaRewardsCfg):
    track_lin_vel_xy_exp = RewTerm(
        func=mdp.track_lin_vel_xy_exp,
        weight=2.0,
        params={"command_name": "base_velocity", "std": 1.0},
    )
    track_ang_vel_z_exp = RewTerm(
        func=mdp.track_ang_vel_z_exp,
        weight=1.0,
        params={"command_name": "base_velocity", "std": 1.0},
    )
    alive = RewTerm(func=mdp.is_alive, weight=0.5)
    joint_mirror = RewTerm(
        func=mdp.joint_mirror,
        weight=-1.0,
        params={
            "asset_cfg": SceneEntityCfg("robot"),
            "mirror_joints": [["left_(hip|knee)", "right_(hip|knee)"]],
        },
    )
    stand_still = RewTerm(
        func=mdp.stand_still,
        weight=0.0,
        params={
            "command_name": "base_velocity",
            "command_threshold": 0.1,
            "asset_cfg": SceneEntityCfg("robot", joint_names=WHEEL_JOINTS),
        },
    )
    undesired_contacts = RewTerm(
        func=mdp.undesired_contacts,
        weight=-1.0,
        params={
            "sensor_cfg": SceneEntityCfg("contact_forces", body_names=LOWER_LEG_BODIES),
            "threshold": 1.0,
        },
    )


@configclass
class TerminationsCfg(TitaTerminationsCfg):
    base_contact = None
    hip_knee_contact = DoneTerm(
        func=mdp.illegal_contact,
        params={
            "sensor_cfg": SceneEntityCfg("contact_forces", body_names=HIP_KNEE_BODIES),
            "threshold": 1.0,
        },
    )


@configclass
class SwingboyTitaFlatEnvCfg(TitaFlatEnvCfg):
    scene: SceneCfg = SceneCfg(num_envs=4096, env_spacing=2.5)
    observations: ObservationsCfg = ObservationsCfg()
    actions: ActionsCfg = ActionsCfg()
    commands: CommandsCfg = CommandsCfg()
    rewards: RewardsCfg = RewardsCfg()
    terminations: TerminationsCfg = TerminationsCfg()
    events: EventCfg = EventCfg()

    def __post_init__(self):
        super().__post_init__()
        self.commands.base_velocity.ranges.lin_vel_y = (0.0, 0.0)
        self.rewards.base_height_l2.params["target_height"] = 0.30

        # Tita is about four times heavier than Swingboy. Keep the same
        # relative domain-randomization strength instead of copying forces and
        # added mass in absolute units.
        self.events.add_base_mass.params["mass_distribution_params"] = (-0.125, 0.5)
        self.events.add_base_com.params["com_range"] = {
            "x": (-0.02, 0.02),
            "y": (-0.02, 0.02),
            "z": (-0.02, 0.02),
        }
        self.events.base_external_force_torque.params["force_range"] = (-2.5, 2.5)
        self.events.base_external_force_torque.params["torque_range"] = (-2.5, 2.5)

        # First establish the Tita-style standing/locomotion baseline. Wider
        # joint resets can be introduced after this policy is reliable.
        self.events.reset_robot_joints.params["position_range"] = (0.95, 1.0)
        self.events.reset_base.params["velocity_range"] = {
            "x": (-0.10, 0.10),
            "y": (-0.05, 0.05),
            "z": (-0.05, 0.05),
            "roll": (-0.15, 0.15),
            "pitch": (-0.15, 0.15),
            "yaw": (-0.15, 0.15),
        }


@configclass
class SwingboyTitaFlatEnvCfg_PLAY(SwingboyTitaFlatEnvCfg):
    def __post_init__(self):
        super().__post_init__()
        self.scene.num_envs = 1
        self.scene.env_spacing = 2.5
        self.observations.policy.enable_corruption = False
        self.events.base_external_force_torque = None
        self.events.push_robot = None
        self.events.add_base_inertia = None
        self.events.add_base_com = None
        self.events.add_base_mass = None
        self.events.randomize_actuator_gains = None
