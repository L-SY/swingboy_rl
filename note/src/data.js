export const checklistSections = [
  {
    id: "mechanics",
    title: "机械与几何",
    icon: "Ruler",
    items: [
      { id: "link-mass", title: "Link 质量实测", detail: "base / hip / knee / wheel 已分别称重", done: true },
      { id: "inertia", title: "惯量与质心复核", detail: "惯量由 STL 封闭面与实测质量估算，仍需记录质心实测误差", done: false },
      { id: "mesh-scale", title: "STL 尺寸与单位", detail: "URDF 使用 0.001 缩放，需与实物关键尺寸交叉检查", done: true },
      { id: "collision", title: "碰撞几何逐 Link 检查", detail: "当前使用原始 STL + convex decomposition，需检查接触点和穿透", done: false },
      { id: "self-collision", title: "自碰撞策略", detail: "当前关闭 self collision，需确认 hip 与 wheel 机械干涉如何表达", done: false },
      { id: "wheel-radius", title: "轮子半径与轴距", detail: "建立实测值、URDF 值和接触半径对照", done: false }
    ]
  },
  {
    id: "actuation",
    title: "关节与执行器",
    icon: "Gauge",
    items: [
      { id: "joint-axis", title: "关节方向与符号", detail: "hip: +Y，knee: -Y，左右轮方向相反", done: true },
      { id: "joint-limit", title: "机械限位", detail: "hip 0°–130°，knee 5°–290°，wheel continuous", done: true },
      { id: "calibration-pose", title: "实机上电校准姿态", detail: "hip 130° / knee 5°，必须与 policy 启动流程一致", done: true },
      { id: "motor-envelope", title: "力矩–转速包络", detail: "目前只记录峰值，需增加连续值、温度降额与驱动器限流", done: false },
      { id: "pd-gains", title: "PD 与实机一致", detail: "腿部 P=30 / D=1；轮子速度驱动 damping=1", done: true },
      { id: "latency", title: "延迟与控制周期实测", detail: "需记录传感、ROS 2、总线、驱动器和执行总延迟", done: false }
    ]
  },
  {
    id: "simulation",
    title: "仿真一致性",
    icon: "Boxes",
    items: [
      { id: "static-pose", title: "静态姿态与地面关系", detail: "确认 reset 后无穿透、无过大去穿透速度", done: true },
      { id: "gravity-sag", title: "零动作重力下沉测试", detail: "分别测试关闭和开启 PD 时的静态行为", done: false },
      { id: "contact-material", title: "轮地摩擦与恢复系数", detail: "需用斜坡/滚动/制动实验标定，而不是只做大范围随机化", done: false },
      { id: "control-rate", title: "物理与 policy 频率", detail: "sim dt=0.005 s，decimation=4，policy=50 Hz", done: true },
      { id: "single-env", title: "单环境可视化检查", detail: "检查 action、contact force、reset 和坐标系", done: true },
      { id: "sim-crosscheck", title: "Isaac / MuJoCo / Gazebo 交叉检查", detail: "同一姿态、PD 和指令下对比关节响应", done: false }
    ]
  },
  {
    id: "mdp",
    title: "MDP 与学习问题",
    icon: "BrainCircuit",
    items: [
      { id: "task-minimum", title: "最小任务可学性", detail: "先用默认站立姿态、平地、零速度验证 PPO 能学会平衡", done: false },
      { id: "obs-deployable", title: "Actor 观测可部署", detail: "当前 actor 无 base linear velocity / scan，其余量可从 IMU 和编码器获得", done: true },
      { id: "action-contract", title: "Action 符号、尺度与偏置", detail: "需生成自动对照表，并在 Isaac 与 ROS 2 中逐项比较", done: false },
      { id: "reward-unit-test", title: "Reward 逐项单元测试", detail: "对理想站立、趴地、空转、倾倒和高速漂移状态计算奖励", done: false },
      { id: "terminal-audit", title: "Terminal 无奖励漏洞", detail: "当前 hip/knee link 接触立即终止，需验证是否会阻断起立探索", done: false },
      { id: "reset-contract", title: "Reset 与实机启动一致", detail: "当前训练 knee 约 33.5°–35.3°，实机校准 knee=5°，尚未闭环", done: false }
    ]
  },
  {
    id: "training",
    title: "训练与验收",
    icon: "ChartNoAxesCombined",
    items: [
      { id: "overfit-one", title: "单姿态过拟合测试", detail: "关闭噪声、随机化和 push，验证能否快速学会站立", done: false },
      { id: "seed-repeat", title: "多随机种子复现", detail: "至少 3 个 seed，不以单次最好 checkpoint 作为结论", done: false },
      { id: "eval-suite", title: "固定验收集", detail: "站立、低速、制动、转向、push、摩擦变化和摔倒恢复", done: false },
      { id: "checkpoint-video", title: "Checkpoint 曲线与视频对齐", detail: "保存关键奖励跃迁节点的 deterministic rollout", done: true },
      { id: "deployment-gate", title: "实机部署门槛", detail: "动作、速度、力矩、姿态和看门狗限制必须先在 Gazebo/Sim 通过", done: false }
    ]
  }
];

export const baselineGroups = [
  {
    id: "mass",
    title: "质量与结构",
    fields: [
      { id: "base_mass", label: "base_link", value: "1.837", unit: "kg", source: "实测" },
      { id: "hip_mass", label: "hip_link × 2", value: "1.293", unit: "kg / side", source: "实测" },
      { id: "knee_mass", label: "knee_link × 2", value: "0.765", unit: "kg / side", source: "实测" },
      { id: "wheel_mass", label: "wheel_link × 2", value: "0.233", unit: "kg / side", source: "实测" },
      { id: "total_mass", label: "URDF 总质量", value: "6.419", unit: "kg", source: "计算" },
      { id: "target_height", label: "目标 base 高度", value: "0.300", unit: "m", source: "训练设定" }
    ]
  },
  {
    id: "joints",
    title: "关节与零位",
    fields: [
      { id: "hip_limit", label: "Hip 限位", value: "0 … 130", unit: "deg", source: "实物确认" },
      { id: "knee_limit", label: "Knee 限位", value: "5 … 290", unit: "deg", source: "实物确认" },
      { id: "wheel_type", label: "Wheel 关节", value: "continuous", unit: "", source: "URDF" },
      { id: "calib_hip", label: "校准 Hip", value: "130", unit: "deg", source: "实机流程" },
      { id: "calib_knee", label: "校准 Knee", value: "5", unit: "deg", source: "实机流程" },
      { id: "train_knee", label: "训练默认 Knee", value: "35.3", unit: "deg", source: "DDT asset cfg" }
    ]
  },
  {
    id: "motors",
    title: "执行器与控制",
    fields: [
      { id: "leg_torque", label: "Hip / Knee 峰值力矩", value: "30.5", unit: "N·m", source: "电机参数" },
      { id: "leg_speed", label: "Hip / Knee 峰值转速", value: "15.49", unit: "rad/s", source: "电机参数" },
      { id: "wheel_torque", label: "Wheel 峰值力矩", value: "19.94", unit: "N·m", source: "电机参数" },
      { id: "wheel_speed", label: "Wheel 峰值转速", value: "24.18", unit: "rad/s", source: "电机参数" },
      { id: "leg_kp", label: "Leg Kp", value: "30", unit: "N·m/rad", source: "当前配置" },
      { id: "leg_kd", label: "Leg Kd", value: "1", unit: "N·m·s/rad", source: "当前配置" },
      { id: "policy_rate", label: "Policy 频率", value: "50", unit: "Hz", source: "dt / decimation" }
    ]
  }
];

export const currentMdp = {
  summary: {
    simulator: "Isaac Sim 5.1 / Isaac Lab + DDT_Lab",
    algorithm: "NP3O (BarlowTwins-PPO)",
    task: "DDT-Velocity-Flat-Swingboy-v0",
    environments: "4096",
    controlRate: "50 Hz",
    episode: "20 s",
    status: "基线待重新验证"
  },
  actorObservations: [
    ["base_ang_vel", "3", "×0.25，uniform noise ±0.2"],
    ["projected_gravity", "3", "uniform noise ±0.05"],
    ["velocity_command", "3", "vx, vy, yaw; scale 2, 2, 0.25"],
    ["joint_pos_rel", "4", "不包含轮子位置，noise ±0.01"],
    ["joint_vel", "6", "×0.05，noise ±1.5"],
    ["last_action", "6", "上一次动作"],
    ["history", "10 frames", "不展平，供 NP3O 编码器使用"]
  ],
  criticAdditions: [
    "base linear velocity",
    "wheel contact state",
    "joint Kp/Kd randomization factors",
    "rough task 可选 height scan"
  ],
  actions: [
    ["left/right hip", "position", "default + action × 0.25 rad"],
    ["left/right knee", "position", "default + action × 0.25 rad"],
    ["left wheel", "velocity", "action × 5 rad/s"],
    ["right wheel", "velocity", "action × -5 rad/s"]
  ],
  commands: [
    ["vx", "-1.0 … 1.0 m/s"],
    ["vy", "0.0 m/s"],
    ["yaw rate", "-1.0 … 1.0 rad/s"],
    ["heading", "-π … π; 10 s resample"]
  ],
  rewards: [
    ["track_lin_vel_xy_exp", "+2.0", "std=1.0"],
    ["track_ang_vel_z_exp", "+1.0", "std=1.0"],
    ["alive", "+0.5", "未终止"],
    ["base_height_l2", "-10.0", "target=0.30 m"],
    ["flat_orientation_l2", "-5.0", "base 水平"],
    ["joint_mirror", "-1.0", "左右 hip/knee 对称"],
    ["undesired_contacts", "-1.0", "lower leg contact > 1 N"],
    ["lin_vel_z_l2", "-2.0", "垂向速度"],
    ["ang_vel_xy_l2", "-0.05", "roll/pitch 角速度"],
    ["joint_torques_l2", "-1e-5", "关节力矩"],
    ["joint_acc_l2", "-2.5e-7", "关节加速度"],
    ["action_rate_l2", "-0.01", "动作变化"]
  ],
  terminations: [
    ["time_out", "20 s", "正常 timeout"],
    ["hip_knee_contact", "> 1 N", "left/right hip_knee_link 接触立即终止"]
  ],
  reset: [
    ["base", "z=0.30 m; x/y ±0.5 m; yaw ±π"],
    ["joints", "default pose × [0.95, 1.0]"],
    ["default", "hip=130°, knee=35.3°, wheel=0"],
    ["root velocity", "x ±0.10, y/z ±0.05, r/p/y ±0.15"]
  ]
};

export const referenceRepos = [
  {
    id: "ddt-tita",
    name: "DDT_Lab / Tita",
    robot: "Tita 轮腿机器人",
    relevance: "极高",
    status: "已核对本地代码",
    url: "https://github.com/DDTRobot/DDT_Lab",
    revision: "701a49c",
    simulator: "Isaac Sim 5.1 + Isaac Lab",
    algorithm: "NP3O / BarlowTwins-PPO",
    terrain: "平地 + 粗糙地形，terrain level curriculum",
    actions: "6 个腿关节位置（scale 0.25）+ 2 个轮子速度（scale 5.0）",
    observations: "Actor: 角速度、投影重力、速度指令、非轮关节位置、全关节速度、last action；10 帧历史。Actor 不看 base linear velocity。",
    critic: "额外使用 base linear velocity、轮接触、Kp/Kd 因子；rough 使用 height scan 编码。",
    commands: "vx [-1,1] m/s，vy=0，yaw [-1,1] rad/s，heading command，10 s 重采样。",
    rewards: "速度跟踪 +1/+0.5；z 速度 -2，roll/pitch 角速度 -0.05，torque -1e-5，acc -2.5e-7，action rate -0.01，腿对称 -1，非期望接触 -1，姿态 -5，高度 0.3 m / -10。",
    terminal: "20 s timeout；base_link 接触力 >1 N 终止。",
    initialState: "base 使用 asset 默认高度；root x/y/yaw 和速度随机；joint position 按 [-0.5,1.0] 系数 reset。",
    randomization: "摩擦/恢复、base mass/inertia/COM、执行器增益、reset force/torque，10–15 s 速度 push。",
    result: "仓库提供 Tita flat/rough 训练与 play 任务；当前 Swingboy DDT 任务直接继承该结构。",
    lessons: ["轮子用速度 action，腿用位置 action", "Actor 用可部署本体感观测，critic 使用 privileged state", "历史编码器用于估计隐变量", "不应直接照搬质量和外力的绝对范围"],
    sourceFiles: ["ref/ddt_tita/rough_env_cfg.py", "ref/ddt_tita/np3o_cfg.py"]
  },
  {
    id: "tron1-wf",
    name: "LimX TRON1 WheelFoot",
    robot: "TRON1 轮足双足",
    relevance: "极高",
    status: "已核对本地代码",
    url: "https://github.com/limxdynamics/tron1-rl-isaaclab",
    revision: "28ae509",
    simulator: "Isaac Sim + Isaac Lab",
    algorithm: "RSL-RL PPO + 10-frame history encoder",
    terrain: "flat / blind rough / stairs / height-scan variants，terrain curriculum",
    actions: "6 个腿关节位置 scale=0.25 + 2 个轮子速度 scale=1.0。",
    observations: "Actor: base angular velocity、projected gravity、非轮关节位置、全关节速度、last action；command 作为独立观测组；10 帧历史。",
    critic: "base linear/angular velocity、gravity、关节状态、height scan、torque/acc、轮速/接触、mass/inertia/PD/COM/material 等 privileged state。",
    commands: "vx [-0.7,0.7]，vy [-0.5,0.5]，yaw [-π,π]，heading，3–15 s 重采样。",
    rewards: "alive +1，linear/yaw tracking +3/+1，leg symmetry +0.5；轮 x 对齐 -50，z/xy 速度、torque、acc、action rate、限位、非期望接触、姿态 -12、轮距 -100、base height 0.8 m / -30 等。",
    terminal: "20 s timeout；base_Link 接触 >1 N 终止。",
    initialState: "WheelFoot 腿关节默认全 0；reset joint offset ±0.2 rad，velocity ±0.5；root pose/velocity 随机。",
    randomization: "mass/inertia/COM/material/PD 大范围随机；随机外力概率 0.002，x/y 最大 500 N。",
    result: "官方提供 WheelFoot 训练、ROS/ROS 2、Gazebo 和 MuJoCo 部署链路，适合对照 sim-to-sim 接口。",
    lessons: ["腿间距和轮子 x 对齐是独立强约束", "command 与 proprioception 分组输入", "critic 中的 privileged state 非常完整", "先验证 flat / blind 再引入 scan 与 stairs"],
    sourceFiles: ["third_party/versions.yaml", "https://github.com/limxdynamics/tron1-rl-isaaclab/tree/main/exts/bipedal_locomotion"]
  },
  {
    id: "legged-gym",
    name: "legged_gym / ANYmal",
    robot: "ANYmal 四足基线",
    relevance: "中",
    status: "已核对上游基础配置",
    url: "https://github.com/leggedrobotics/legged_gym",
    revision: "8fa29ac",
    simulator: "NVIDIA Isaac Gym / PhysX",
    algorithm: "RSL-RL PPO",
    terrain: "trimesh rough terrain；斜坡、台阶、离散障碍；10×20 terrain curriculum",
    actions: "12 关节位置目标，default angle + action × 0.5。",
    observations: "base linear/angular velocity、projected gravity、commands、joint position/velocity、last actions，rough 任务附加 187 点 height samples；总计 235 维。",
    critic: "基础配置默认不使用 asymmetric privileged observation。",
    commands: "vx/vy/yaw [-1,1]，heading [-π,π]，10 s 重采样。",
    rewards: "linear/yaw tracking +1/+0.5；z 速度 -2，xy 角速度 -0.05，torque -1e-5，acc -2.5e-7，feet air time +1，collision -1，action rate -0.01；总 reward 可裁到非负。",
    terminal: "timeout 20 s；按 robot config 指定 terminate_after_contacts_on 的 body contact。",
    initialState: "base 默认 z=1 m，关节使用机器人专用 default angles；root 位置/速度 reset。",
    randomization: "friction [0.5,1.25]，可选 base mass，15 s push，最大 xy 速度冲量 1 m/s，观测噪声。",
    result: "经典 sim-to-real 粗糙地形 locomotion 基线；现已迁移至 Isaac Lab，但奖励和 curriculum 结构仍有参考价值。",
    lessons: ["先构建可过拟合的基础 reward，再增加 terrain curriculum", "每个非零 reward scale 都应有对应可解释的函数", "噪声与 domain randomization 是部署设计的一部分"],
    sourceFiles: ["https://github.com/leggedrobotics/legged_gym/blob/master/legged_gym/envs/base/legged_robot_config.py"]
  },
  {
    id: "mujoco-go1",
    name: "MuJoCo Playground / Go1",
    robot: "Unitree Go1 四足",
    relevance: "中",
    status: "已核对本地锁定版本",
    url: "https://github.com/google-deepmind/mujoco_playground",
    revision: "a61676a",
    simulator: "MuJoCo MJX / MuJoCo Warp",
    algorithm: "Brax PPO（也支持 RSL-RL PPO）",
    terrain: "flat / rough heightfield；Warp 适合更多 mesh contact",
    actions: "12 关节位置目标，default pose + action × 0.5，50 Hz policy / 250 Hz physics。",
    observations: "Actor 51D: local linear velocity、gyro、gravity、12 joint position/velocity、12 last action、3 command，均含可配噪声。",
    critic: "Actor state + 无噪声 IMU/关节、accelerometer、actuator force、foot contact/velocity/air-time、外力状态。",
    commands: "三维速度指令幅值约 [1.5,0.8,1.2]，按概率将各维置零，指数分布重采样时间。",
    rewards: "linear/yaw tracking +1/+0.5，z 速度 -0.5，xy 角速度 -0.05，orientation -5，pose +0.5，termination/stand -1，torque -2e-4，action rate -0.01，energy -0.001，足部高度/滑移/腾空。",
    terminal: "torso up-vector z < 0 判定翻倒；episode 1000 policy steps。",
    initialState: "XML home keyframe；x/y ±0.5 m，yaw ±π，root xyz/rpy velocity ±0.5。",
    randomization: "观测噪声；可选 velocity kick perturbation；训练时可注入 domain randomization function。",
    result: "Go1 joystick flat/rough 官方配置使用 2×10^8 timesteps，提供 sim-to-real 和互动训练工具链。",
    lessons: ["先用确定的 XML home keyframe 定义 reset", "Actor/critic 观测契约非常清晰", "reward 以 dt 缩放并 clip 至非负，需注意与 Isaac Lab 的语义不同", "不能只比 reward weight，必须同时比较函数形式和 dt"],
    sourceFiles: ["sim/mujoco/mujoco_playground/_src/locomotion/go1/joystick.py", "sim/mujoco/mujoco_playground/config/locomotion_params.py"]
  }
];

export const initialExperiments = [
  {
    id: "exp-ddt-700",
    date: "2026-07-17",
    name: "DDT Tita 结构迁移基线",
    simulator: "Isaac Lab / DDT_Lab",
    task: "DDT-Velocity-Flat-Swingboy-v0",
    run: "model_700.pt",
    seed: "42",
    status: "待复盘",
    hypothesis: "直接使用 Tita 的 NP3O 结构可先验证轮腿平衡与速度跟踪。",
    changes: "Swingboy URDF、6 actions、质量缩放后的 domain randomization、hip/knee contact terminal。",
    result: "Policy 可导出和 play，但站立与速度跟踪表现尚未达到验收标准。",
    next: "先完成 reset 姿态、接触、动作映射和奖励逐项单元测试。",
    evidence: "policies/v0.2.0-ddt/"
  }
];

export const initialDecisions = [
  {
    id: "decision-reset-gap",
    date: "2026-07-17",
    type: "风险",
    title: "训练默认姿态与实机校准姿态不同",
    detail: "实机上电后 hip=130° / knee=5°；当前训练默认 knee=35.3°，reset 为该默认值的 95%–100%。",
    state: "未解决"
  },
  {
    id: "decision-observation",
    date: "2026-07-17",
    type: "决策",
    title: "Actor 不使用 base linear velocity 和 height scan",
    detail: "保留 base angular velocity、projected gravity、command、joint state 和 action history；critic 可使用 privileged state。",
    state: "已采用"
  }
];
