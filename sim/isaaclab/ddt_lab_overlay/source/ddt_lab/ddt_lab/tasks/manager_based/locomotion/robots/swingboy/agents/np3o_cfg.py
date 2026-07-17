# Copyright (c) 2022-2025, The Isaac Lab Project Developers.
# All rights reserved.
#
# SPDX-License-Identifier: BSD-3-Clause

from ddt_lab.tasks.manager_based.locomotion.agents.np3o_cfg import base_np3o_runner_cfg


def swingboy_tita_flat_np3o_runner_cfg() -> dict:
    cfg = base_np3o_runner_cfg()
    cfg["runner"]["experiment_name"] = "swingboy_tita_flat"
    cfg["runner"]["max_iterations"] = 3000
    cfg["policy"]["init_noise_std"] = 0.5
    return cfg
