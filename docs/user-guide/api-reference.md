# 公共调用参考

先按物理功能选择接口，再查本页。以下签名由本版 wheel 的声明静态抽取；不 import 整个科学库。

函数和配置类共 32 个公共入口。7 个入口附有既有 canonical 合同的生成投影；其余是有限兼容参考。声明中的符号默认值按来源保留，不能假定是已求值常量。类字段的源码默认值也不补造单位或科学保证。

## 径向剖面、坐标与边界

物理说明：[径向剖面、坐标与边界](tokamak/radial-profiles.md)。

<a id="api-scirel.fusion.grid.make_grid"></a>

### make_grid

建立径向单元中心与物理间距。

`from scirel.fusion.grid import make_grid`

```python
make_grid(nr: int, a: float, radial_grid: str='uniform', edge_cluster_power: float=2.0)
```

**已有详细合同**：`scirel.fusion.make-grid`。以下内容由本版 canonical 记录投影，完整机器可读版本见 Agent 的对应 API 文件。

#### 输入

| 名称 | 含义 | 单位 | 形状 / 类型 | 约束或默认值 |
| --- | --- | --- | --- | --- |
| `nr` | Number of radial cells | 1 | scalar / int | Positive integer; selected evidence uses nr=4, no new validation/clamping. |
| `a` | Plasma minor radius | m | scalar / float | Positive radius; selected evidence uses a=2 m. |
| `radial_grid` | Source radial-grid selector | 1 | scalar / str | uniform or edge_cluster_sqrt are evidenced; linear is a retained alias.; default=uniform |
| `edge_cluster_power` | Exponent in sqrt(max(1-(1-x)^p,0)) | 1 | scalar / float | Positive exponent; evidence uses p=2.; default=2 |

#### 输出

| 名称 | 含义 | 单位 | 形状 / 类型 | 约束或默认值 |
| --- | --- | --- | --- | --- |
| `rho` | Normalized cell centers | 1 | [nr] / floating array | Caller supplies the declared domain. |
| `r` | Physical minor-radius cell centers | m | [nr] / floating array | Caller supplies the declared domain. |
| `dr` | Physical cell width; scalar for uniform compatibility | m | scalar for uniform; [nr] for clustered / floating array | Caller supplies the declared domain. |

关系：rho_i=(face_i+face_{i+1})/2; r_i=a*rho_i; dr=a/nr for uniform, a*diff(faces) otherwise.

适用前提：Install the pinned fusion extra in the tested Linux x86_64 CPython 3.12 profile.；Use positive grid counts/radius and compatible declared shapes; configure JAX x64 before numeric calls for the bound evidence.

无效输入：Original errors propagate; grid and axis selectors raise named ValueError. No newly invented checks, clipping or defaults.

运行失败：Dependency, shape, source computation and nonfinite behavior propagate unchanged; optional dependency import occurs only on symbol access.

证据上限：Bounded source behavior and installed nonregression only. No correctness qualification, human approval or whole D1 completion.

<a id="api-scirel.fusion.grid.make_rho_faces"></a>

### make_rho_faces

建立径向单元面。

`from scirel.fusion.grid import make_rho_faces`

```python
make_rho_faces(nr: int, radial_grid: str='uniform', edge_cluster_power: float=2.0)
```

**已有详细合同**：`scirel.fusion.make-rho-faces`。以下内容由本版 canonical 记录投影，完整机器可读版本见 Agent 的对应 API 文件。

#### 输入

| 名称 | 含义 | 单位 | 形状 / 类型 | 约束或默认值 |
| --- | --- | --- | --- | --- |
| `nr` | Number of radial cells | 1 | scalar / int | Positive integer; selected evidence uses nr=4, no new validation/clamping. |
| `radial_grid` | Source radial-grid selector | 1 | scalar / str | uniform or edge_cluster_sqrt are evidenced; linear is a retained alias.; default=uniform |
| `edge_cluster_power` | Exponent in sqrt(max(1-(1-x)^p,0)) | 1 | scalar / float | Positive exponent; evidence uses p=2.; default=2 |

#### 输出

| 名称 | 含义 | 单位 | 形状 / 类型 | 约束或默认值 |
| --- | --- | --- | --- | --- |
| `faces` | Normalized radial cell faces | 1 | [nr+1] / floating array | Caller supplies the declared domain. |

关系：x_i=i/nr; uniform faces=x; clustered faces=sqrt(max(1-(1-x)^p,0)).

适用前提：Install the pinned fusion extra in the tested Linux x86_64 CPython 3.12 profile.；Use positive grid counts/radius and compatible declared shapes; configure JAX x64 before numeric calls for the bound evidence.

无效输入：Original errors propagate; grid and axis selectors raise named ValueError. No newly invented checks, clipping or defaults.

运行失败：Dependency, shape, source computation and nonfinite behavior propagate unchanged; optional dependency import occurs only on symbol access.

证据上限：Bounded source behavior and installed nonregression only. No correctness qualification, human approval or whole D1 completion.

<a id="api-scirel.fusion.grid.radial_gradient"></a>

### radial_gradient

按来源边界约定计算径向梯度。

`from scirel.fusion.grid import radial_gradient`

```python
radial_gradient(y, rho, a)
```

**已有详细合同**：`scirel.fusion.radial-gradient`。以下内容由本版 canonical 记录投影，完整机器可读版本见 Agent 的对应 API 文件。

#### 输入

| 名称 | 含义 | 单位 | 形状 / 类型 | 约束或默认值 |
| --- | --- | --- | --- | --- |
| `y` | Scalar profile sampled at rho; unit preserved through differentiation. | caller field units | [nr] / floating array | One-dimensional array of length nr >= 2; y and rho must have identical lengths. rho increases within (0,1). |
| `rho` | Cell-center normalized minor-radius coordinate, increasing within (0,1). | 1 | [nr] / floating array | One-dimensional array of length nr >= 2; y and rho must have identical lengths. rho increases within (0,1). |
| `a` | Plasma minor radius | m | scalar / float | Positive radius; selected evidence uses a=2 m. |

#### 输出

| 名称 | 含义 | 单位 | 形状 / 类型 | 约束或默认值 |
| --- | --- | --- | --- | --- |
| `gradient` | Source dy/dr approximation | caller field units / m | [nr] / floating array | One-dimensional result of the same length nr >= 2 as the matching y and rho inputs. |

关系：First gradient is zero by copied axis ghost; interior (y[i+1]-y[i-1])/(a*(rho[i+1]-rho[i-1])+1e-12); last uses backward difference with same denominator regularization.

适用前提：Install the pinned fusion extra in the tested Linux x86_64 CPython 3.12 profile.；Use matching one-dimensional y and rho arrays of length nr >= 2, increasing rho within (0,1), and positive radius a; configure JAX x64 before numeric calls for the bound evidence.

无效输入：The documented domain requires matching one-dimensional inputs with nr >= 2. No new validation, endpoint handling, clipping or defaults are added. Outside this domain, the original indexing, shape, error or return behavior remains unchanged and is not certified as a valid [nr] gradient.

运行失败：Dependency, shape, source computation and nonfinite behavior propagate unchanged; optional dependency import occurs only on symbol access.

证据上限：Bounded source behavior and installed nonregression only. No correctness qualification, human approval or whole D1 completion.

<a id="api-scirel.fusion.grid.boundary_augmented_profile"></a>

### boundary_augmented_profile

给绘图剖面补上轴和边界点。

`from scirel.fusion.grid import boundary_augmented_profile`

```python
boundary_augmented_profile(rho, y, edge_value=None, method='copy', n_points=4)
```

**已有详细合同**：`scirel.fusion.boundary-augmented-profile`。以下内容由本版 canonical 记录投影，完整机器可读版本见 Agent 的对应 API 文件。

#### 输入

| 名称 | 含义 | 单位 | 形状 / 类型 | 约束或默认值 |
| --- | --- | --- | --- | --- |
| `rho` | Cell-center normalized minor-radius coordinate, increasing within (0,1). | 1 | [nr] / floating array | Caller supplies the declared domain. |
| `y` | Profile values at rho. | caller field units | [nr] / floating array | Caller supplies the declared domain. |
| `edge_value` | Physical edge value, or None to copy last value | caller field units | scalar or None / float or None | No new edge closure is invented.; default=null |
| `method` | Axis extrapolation method | 1 | scalar / str | copy, linear, quadratic or cubic selected source policy.; default=copy |
| `n_points` | Number of points in polynomial fit | 1 | scalar / int | Used only for explicit polynomial legacy policies.; default=4 |

#### 输出

| 名称 | 含义 | 单位 | 形状 / 类型 | 约束或默认值 |
| --- | --- | --- | --- | --- |
| `rho_aug` | Coordinates including axis and edge | 1 | [nr+2] / floating array | Caller supplies the declared domain. |
| `y_aug` | Augmented values in unchanged field units | caller field units | [nr+2] / floating array | Caller supplies the declared domain. |

关系：Prepend rho=0 with copied first value by default, then append rho=1 with supplied edge or last value. Explicit linear/quadratic/cubic legacy extrapolation remains selectable.

适用前提：Install the pinned fusion extra in the tested Linux x86_64 CPython 3.12 profile.；Use positive grid counts/radius and compatible declared shapes; configure JAX x64 before numeric calls for the bound evidence.

无效输入：Original errors propagate; grid and axis selectors raise named ValueError. No newly invented checks, clipping or defaults.

运行失败：Dependency, shape, source computation and nonfinite behavior propagate unchanged; optional dependency import occurs only on symbol access.

证据上限：Bounded source behavior and installed nonregression only. No correctness qualification, human approval or whole D1 completion.

## 状态初始化与时间演化

物理说明：[状态初始化与时间演化](tokamak/state-and-evolution.md)。

<a id="api-scirel.fusion.configuration.MachineConfig"></a>

### MachineConfig

装置与等离子体几何参数。

`from scirel.fusion.configuration import MachineConfig`

构造字段按下面的声明传入；未写默认值的字段必须提供。

<details><summary>展开字段、类型与源码默认值</summary>

| 字段 | 类型声明 | 源码默认值 |
| --- | --- | --- |
| `R0` | `float` | `6.2` |
| `a` | `float` | `2.0` |
| `kappa` | `float` | `1.7` |
| `delta` | `float` | `0.5` |
| `Bt` | `float` | `5.3` |
| `Ip` | `float` | `15000000.0` |
| `Zeff` | `float` | `1.8` |
| `lnLambda` | `float` | `17.0` |
| `plasma_species` | `str` | `'DT'` |
| `dt_fraction_D` | `float` | `0.5` |
| `dt_fraction_T` | `float` | `0.5` |
| `impurity_Z` | `float` | `74.0` |

</details>

**兼容参考**：未附独立完整科学合同。调用的物理输入、状态和限制见上面的主题；未知单位、模型有效性和通用正确性不从函数名称猜补。

<a id="api-scirel.fusion.configuration.ActuatorConfig"></a>

### ActuatorConfig

加热和驱动参数。

`from scirel.fusion.configuration import ActuatorConfig`

构造字段按下面的声明传入；未写默认值的字段必须提供。

<details><summary>展开字段、类型与源码默认值</summary>

| 字段 | 类型声明 | 源码默认值 |
| --- | --- | --- |
| `P_aux_MW` | `float` | `50.0` |
| `f_e_heat` | `float` | `0.6` |
| `aux_partition_model` | `str` | `'slowing_down'` |
| `nbi_birth_energy_MeV` | `float` | `1.0` |
| `nbi_fast_ion_A` | `float` | `2.0` |
| `nbi_fast_ion_Z` | `float` | `1.0` |
| `heat_center` | `float` | `0.2` |
| `heat_width` | `float` | `0.25` |
| `greenwald_fraction_target` | `float` | `0.9` |
| `greenwald_edge_density_fraction` | `float` | `0.1` |
| `edge_Te_keV` | `float` | `0.25` |
| `edge_Ti_keV` | `float` | `0.25` |
| `cd_fraction` | `float` | `0.0` |
| `cd_efficiency_20` | `float` | `0.3` |
| `cd_fraction_max` | `float` | `0.5` |
| `cd_center` | `float` | `0.2` |
| `cd_width` | `float` | `0.3` |

</details>

**兼容参考**：未附独立完整科学合同。调用的物理输入、状态和限制见上面的主题；未知单位、模型有效性和通用正确性不从函数名称猜补。

<a id="api-scirel.fusion.configuration.SimulationConfig"></a>

### SimulationConfig

数值与模型选择参数。

`from scirel.fusion.configuration import SimulationConfig`

构造字段按下面的声明传入；未写默认值的字段必须提供。

<details><summary>展开字段、类型与源码默认值</summary>

| 字段 | 类型声明 | 源码默认值 |
| --- | --- | --- |
| `nr` | `int` | `32` |
| `radial_grid` | `str` | `'uniform'` |
| `edge_cluster_power` | `float` | `2.0` |
| `dt` | `float` | `0.001` |
| `n_steps` | `int` | `500` |
| `end_time_s` | `float` | `0.0` |
| `dt_mode` | `str` | `'fixed'` |
| `cfl_number` | `float` | `0.25` |
| `cfl_diffusivity_ref_m2_s` | `float` | `1.0` |
| `adjust_dt_to_end_time` | `bool` | `True` |
| `save_every` | `int` | `10` |
| `save_results_enabled` | `bool` | `False` |
| `save_result_times_s` | `tuple` | `()` |
| `save_result_file` | `str` | `'outputs/tokagrad_results.npz'` |
| `save_result_format` | `str` | `'npz'` |
| `save_result_include_metadata_json` | `bool` | `True` |
| `plot_diffusivity` | `bool` | `False` |
| `plot_psi` | `bool` | `False` |
| `equilibrium_skip_steps` | `int` | `1` |
| `source_skip_steps` | `int` | `1` |
| `transport_skip_steps` | `int` | `1` |
| `pedestal_skip_steps` | `int` | `1` |
| `diffusion_scheme` | `str` | `'semi_implicit'` |
| `implicit_nonlinear_iters` | `int` | `3` |
| `implicit_relaxation` | `float` | `1.0` |
| `predictor_corrector_relaxation` | `float` | `1.0` |
| `newton_iters` | `int` | `4` |
| `newton_damping` | `float` | `0.7` |
| `newton_jacobian_regularization` | `float` | `1e-06` |
| `density_evolution_model` | `str` | `'greenwald_feedback'` |
| `freeze_temperature_profiles` | `bool` | `False` |
| `differentiable_smooth_mode` | `bool` | `False` |
| `smooth_clip_width` | `float` | `0.01` |
| `smooth_rate_width` | `float` | `0.01` |
| `source_implicitness` | `float` | `1.0` |
| `source_max_delta_keV` | `float` | `2.5` |
| `initial_beta_N_target` | `float` | `1.8` |
| `initial_temperature_rescale_to_beta_N` | `bool` | `True` |
| `initial_profile_quadrature_points` | `int` | `32` |
| `greenwald_tanh_core_factor` | `float` | `1.1` |
| `greenwald_tanh_pedestal_factor` | `float` | `1.0` |
| `greenwald_tanh_transition_fraction` | `float` | `0.25` |
| `greenwald_tanh_default_width` | `float` | `0.04` |
| `density_feedback_tau` | `float` | `0.001` |
| `greenwald_feedback_average_basis` | `str` | `'volume'` |
| `density_feedback_method` | `str` | `'implicit_source'` |
| `density_boundary_source_width` | `float` | `0.1` |
| `density_source_max_delta` | `float` | `0.25` |
| `initial_profile_model` | `str` | `'h_mode'` |
| `initial_current_profile_model` | `str` | `'saturated_components'` |
| `simulation_model` | `str` | `'1.5d'` |
| `zero_d_H_factor` | `float` | `1.0` |
| `zero_d_L_factor` | `float` | `1.0` |
| `zero_d_dt_fraction_tauE` | `float` | `0.1` |
| `zero_d_tauE_min` | `float` | `0.001` |
| `zero_d_tauE_max` | `float` | `20.0` |
| `zero_d_core_shape_power` | `float` | `2.0` |
| `zero_d_temperature_max_keV` | `float` | `80.0` |
| `zero_d_alpha_birth_energy_MeV` | `float` | `3.52` |
| `zero_d_fast_nbi_fraction` | `float` | `1.0` |
| `zero_d_use_lax_scan` | `bool` | `True` |
| `zero_d_profile_reconstruction_fast_path` | `bool` | `True` |
| `zero_d_reconstruct_current` | `bool` | `True` |
| `transport_mode` | `str` | `'diffusive'` |
| `transport_model` | `str` | `'tglfnn_jax'` |
| `transport_surrogate_scale` | `float` | `1.0` |
| `transport_flux_scale` | `float` | `1.0` |
| `transport_flux_clip` | `float` | `50.0` |
| `transport_flux_max_delta_keV` | `float` | `2.5` |
| `transport_flux_max_delta_ne20` | `float` | `0.25` |
| `fusion_surrogates_fail_mode` | `str` | `'fallback'` |
| `chi_clip_min` | `float` | `0.03` |
| `chi_clip_max` | `float` | `30.0` |
| `qlknn_gb_to_chi` | `float` | `1.0` |
| `gradient_floor` | `float` | `0.5` |
| `tglfnn_model_dir` | `str` | `'external_models/neural'` |
| `tglfnn_model_name` | `str` | `'DIIID_ion_stiffness_60_rotation'` |
| `tglfnn_fail_mode` | `str` | `'fallback'` |
| `tglfnn_jax_max_nets` | `int` | `10` |
| `tglfnn_gb_to_chi` | `float` | `1.0` |
| `tglfnn_use_gyrobohm_scale` | `bool` | `True` |
| `tglfnn_clip_inputs_to_training` | `bool` | `True` |
| `tglfnn_training_clip_sigma` | `float` | `5.0` |
| `tglfnn_vpar_1` | `float` | `0.0` |
| `tglfnn_vpar_shear_1` | `float` | `0.0` |
| `tglfnn_vexb_shear` | `float` | `0.0` |
| `chi_e_base` | `float` | `0.6` |
| `chi_i_base` | `float` | `0.45` |
| `Dn_base` | `float` | `0.15` |
| `chi_edge_mult` | `float` | `4.0` |
| `stiffness` | `float` | `1.5` |
| `grad_crit_keV_per_m` | `float` | `3.0` |
| `bohm_chi_e_bohm_coeff` | `float` | `8e-05` |
| `bohm_chi_e_gyrobohm_coeff` | `float` | `5e-06` |
| `bohm_chi_i_bohm_coeff` | `float` | `8e-05` |
| `bohm_chi_i_gyrobohm_coeff` | `float` | `5e-06` |
| `bohm_particle_c1` | `float` | `1.0` |
| `bohm_particle_c2` | `float` | `0.3` |
| `bohm_chi_min` | `float` | `0.05` |
| `bohm_chi_max` | `float` | `100.0` |
| `bohm_particle_min` | `float` | `0.05` |
| `bohm_particle_max` | `float` | `100.0` |
| `ntheta` | `int` | `16` |
| `theta_grid_alignment` | `str` | `'auto'` |
| `shafranov_shift_max` | `float` | `0.25` |
| `triangularity_profile_power` | `float` | `1.0` |
| `elongation_profile_power` | `float` | `1.0` |
| `transport_geometry` | `str` | `'flux'` |
| `phi_dot_over_phi` | `float` | `0.0` |
| `auto_phi_dot_over_phi` | `bool` | `True` |
| `phi_dot_over_phi_clip` | `float` | `5.0` |
| `reduced_geometry_metrics` | `bool` | `True` |
| `torax_circular_psi_geometry` | `bool` | `False` |
| `heat_convection_model` | `str` | `'none'` |
| `heat_convection_e_base` | `float` | `0.0` |
| `heat_convection_i_base` | `float` | `0.0` |
| `particle_convection_model` | `str` | `'none'` |
| `particle_convection_base` | `float` | `0.0` |
| `ware_pinch_scale` | `float` | `1.0` |
| `ware_pinch_bpol_min_T` | `float` | `0.02` |
| `ware_pinch_velocity_max_m_s` | `float` | `200.0` |
| `equilibrium_model` | `str` | `'reduced_fixed_boundary'` |
| `geqdsk_path` | `str` | `''` |
| `geqdsk_use_pressure` | `bool` | `False` |
| `geqdsk_q_profile_source` | `str` | `'eqdsk'` |
| `geqdsk_flux_coordinate` | `str` | `'sqrt_psi'` |
| `geqdsk_surface_geometry` | `str` | `'psirz_contours'` |
| `geqdsk_inner_contour_fallback` | `str` | `'axis_hessian'` |
| `geqdsk_lcfs_margin` | `float` | `0.0` |
| `pedestal_model` | `str` | `'eped1_nn_jax'` |
| `eped1nn_model_dir` | `str` | `'external_models/neural'` |
| `eped1nn_model_name` | `str` | `'EPED1_H_superH'` |
| `eped1nn_fail_mode` | `str` | `'fallback'` |
| `eped1nn_output_scale` | `float` | `1.0` |
| `eped1nn_jax_max_nets` | `int` | `1` |
| `pedestal_kbm_width_coeff` | `float` | `0.076` |
| `pedestal_width_min` | `float` | `0.025` |
| `pedestal_width_max` | `float` | `0.15` |
| `pedestal_alpha_scale` | `float` | `1.0` |
| `pedestal_alpha_min` | `float` | `1.0` |
| `pedestal_alpha_max` | `float` | `5.5` |
| `pedestal_pressure_relax_tau` | `float` | `0.005` |
| `pedestal_density_height20` | `float` | `0.25` |
| `pedestal_te_fraction` | `float` | `0.5` |
| `pedestal_transition_sharpness` | `float` | `0.012` |
| `pedestal_enforcement` | `str` | `'tanh_underlay'` |
| `pedestal_blend_fraction` | `float` | `1.0` |
| `pedestal_blend_core_width_factor` | `float` | `0.5` |
| `pedestal_blend_mask_sharpness` | `float` | `0.02` |
| `pedestal_blend_include_density` | `bool` | `True` |
| `pedestal_blend_max_delta_keV` | `float` | `2.0` |
| `pedestal_blend_max_delta_ne20` | `float` | `0.1` |
| `pedestal_underlay_smooth_keV` | `float` | `0.05` |
| `pedestal_underlay_smooth_ne20` | `float` | `0.005` |
| `pedestal_alpha_resolution_guard` | `bool` | `True` |
| `pedestal_alpha_calibration_min_width_cells` | `float` | `0.75` |
| `pedestal_alpha_calibration_width_cells` | `float` | `0.25` |
| `pedestal_alpha_discrete_scale_max` | `float` | `5.0` |
| `pedestal_alpha_tracking` | `bool` | `True` |
| `pedestal_alpha_tracking_gain` | `float` | `1.5` |
| `pedestal_source_max_delta_keV` | `float` | `0.5` |
| `pedestal_min_temperature_keV` | `float` | `0.25` |
| `pedestal_projection_fraction` | `float` | `0.8` |
| `pedestal_lh_threshold_model` | `str` | `'delabie'` |
| `pedestal_lh_power_basis` | `str` | `'net_separatrix'` |
| `pedestal_lh_threshold_scale` | `float` | `1.0` |
| `pedestal_lh_margin` | `float` | `0.01` |
| `pedestal_lh_min_gate` | `float` | `0.0` |
| `pedestal_lh_gate_cutoff` | `float` | `0.01` |
| `martin_lh_coeff` | `float` | `0.0488` |
| `martin_lh_n_exp` | `float` | `0.717` |
| `martin_lh_bt_exp` | `float` | `0.803` |
| `martin_lh_s_exp` | `float` | `0.941` |
| `delabie_lh_coeff` | `float` | `0.0441` |
| `delabie_lh_n_exp` | `float` | `1.08` |
| `delabie_lh_bt_exp` | `float` | `0.58` |
| `delabie_lh_meff_exp` | `float` | `0.975` |
| `delabie_lh_d_exp` | `float` | `1.0` |
| `delabie_lh_s_exp` | `float` | `1.0` |
| `current_evolution_model` | `str` | `'psi_diffusion'` |
| `resistivity_multiplier` | `float` | `1.0` |
| `saturated_current_conductivity_power` | `float` | `1.0` |
| `saturated_current_sigma_floor` | `float` | `0.02` |
| `saturated_current_smooth` | `float` | `0.15` |
| `psi_solver_form` | `str` | `'face_fv'` |
| `psi_state_grid` | `str` | `'face'` |
| `new_psi_boundary_model` | `str` | `'fixed_ip_neumann'` |
| `current_source_smoothing_passes` | `int` | `1` |
| `current_enclosed_smoothing_passes` | `int` | `0` |
| `current_axis_regularization_faces` | `int` | `2` |
| `current_diagnostic_smoothing_passes` | `int` | `1` |
| `psi_edge_robin_length_m` | `float` | `0.01` |
| `neoclassical_transport_model` | `str` | `'neonn_jax'` |
| `neonn_model_dir` | `str` | `'external_models/neural'` |
| `neonn_model_name` | `str` | `'jbsnn'` |
| `neonn_fail_mode` | `str` | `'fallback'` |
| `neonn_jax_max_nets` | `int` | `1` |
| `neonn_transport_scale` | `float` | `1.0` |
| `neoclassical_chi_scale` | `float` | `1.0` |
| `neoclassical_D_scale` | `float` | `1.0` |
| `neoclassical_chi_max` | `float` | `5.0` |
| `chang_hinton_particle_fraction` | `float` | `0.2` |
| `chang_hinton_epsilon_min` | `float` | `0.03` |
| `neoclassical_abs_effective_diffusivity` | `bool` | `False` |
| `neoclassical_shaing_ion_mode` | `str` | `'off'` |
| `neoclassical_shaing_ion_multiplier` | `float` | `1.8` |
| `neoclassical_shaing_blend_start` | `float` | `0.2` |
| `neoclassical_shaing_blend_rate` | `float` | `5.0` |
| `current_feedback_model` | `str` | `'psi_boundary_loop_voltage'` |
| `loop_voltage_gain` | `float` | `0.4` |
| `loop_voltage_max` | `float` | `4.0` |
| `bootstrap_model` | `str` | `'sauter'` |
| `neonn_bootstrap_fail_mode` | `str` | `'fallback'` |
| `neonn_bootstrap_output_name` | `str` | `''` |
| `neonn_bootstrap_output_units` | `str` | `'auto'` |
| `neonn_bootstrap_scale` | `float` | `1.0` |
| `bootstrap_multiplier` | `float` | `1.0` |
| `bootstrap_btheta_floor` | `float` | `0.08` |
| `include_ohmic_heating` | `bool` | `True` |
| `include_ei_exchange` | `bool` | `True` |
| `include_radiation_losses` | `bool` | `True` |
| `include_alpha_heating` | `bool` | `True` |
| `bremsstrahlung_scale` | `float` | `1.0` |
| `line_radiation_scale` | `float` | `1.0` |
| `line_radiation_Lz_ref_W_m3` | `float` | `3e-35` |
| `line_radiation_Tcut_keV` | `float` | `1.5` |
| `line_radiation_Z_scaling_power` | `float` | `0.5` |
| `line_radiation_edge_power` | `float` | `3.0` |
| `synchrotron_scale` | `float` | `1.0` |
| `synchrotron_wall_reflectivity` | `float` | `0.8` |
| `synchrotron_escape_fraction` | `float` | `0.05` |
| `alpha_heating_scale` | `float` | `1.0` |
| `alpha_partition_model` | `str` | `'slowing_down'` |
| `alpha_electron_fraction_fixed` | `float` | `0.85` |
| `alpha_ion_fraction_fixed` | `float` | `0.15` |
| `ei_exchange_multiplier` | `float` | `1.0` |

</details>

**兼容参考**：未附独立完整科学合同。调用的物理输入、状态和限制见上面的主题；未知单位、模型有效性和通用正确性不从函数名称猜补。

<a id="api-scirel.fusion.configuration.PlasmaState"></a>

### PlasmaState

演化状态及历史几何字段。

`from scirel.fusion.configuration import PlasmaState`

构造字段按下面的声明传入；未写默认值的字段必须提供。

<details><summary>展开字段、类型与源码默认值</summary>

| 字段 | 类型声明 | 源码默认值 |
| --- | --- | --- |
| `Te` | `jnp.ndarray` | 必填 |
| `Ti` | `jnp.ndarray` | 必填 |
| `ne20` | `jnp.ndarray` | 必填 |
| `psi_ind` | `jnp.ndarray` | 必填 |
| `psi_edge` | `jnp.ndarray` | 必填 |
| `Phi_b_prev` | `jnp.ndarray` | `jnp.asarray(0.0)` |
| `dV_drho_prev` | `jnp.ndarray` | `jnp.asarray(0.0)` |

</details>

**兼容参考**：未附独立完整科学合同。调用的物理输入、状态和限制见上面的主题；未知单位、模型有效性和通用正确性不从函数名称猜补。

<a id="api-scirel.fusion.configuration.load_static_input"></a>

### load_static_input

从 JSON 读取静态配置。

`from scirel.fusion.configuration import load_static_input`

```python
load_static_input(path: str | Path, machine: MachineConfig | None=None, actuator: ActuatorConfig | None=None, sim: SimulationConfig | None=None)
```

**兼容参考**：未附独立完整科学合同。调用的物理输入、状态和限制见上面的主题；未知单位、模型有效性和通用正确性不从函数名称猜补。

<a id="api-scirel.fusion.configuration.load_waveform_input"></a>

### load_waveform_input

从 JSON 读取时变输入。

`from scirel.fusion.configuration import load_waveform_input`

```python
load_waveform_input(path: str | Path, machine: MachineConfig | None=None, actuator: ActuatorConfig | None=None, sim: SimulationConfig | None=None)
```

**兼容参考**：未附独立完整科学合同。调用的物理输入、状态和限制见上面的主题；未知单位、模型有效性和通用正确性不从函数名称猜补。

<a id="api-scirel.fusion.dynamics.initial_state"></a>

### initial_state

构造径向初始状态。

`from scirel.fusion.dynamics import initial_state`

```python
initial_state(machine, actuator, sim)
```

**已有详细合同**：`scirel.fusion.initial-state`。以下内容由本版 canonical 记录投影，完整机器可读版本见 Agent 的对应 API 文件。

#### 输入

| 名称 | 含义 | 单位 | 形状 / 类型 | 约束或默认值 |
| --- | --- | --- | --- | --- |
| `machine` | Source machine configuration; R0,a in m, Bt in T, Ip in A, kappa/delta/Zeff dimensionless. | mixed declared configuration units | scalar fields / MachineConfig | Use exact source config defaults or explicitly selected source-admissible controls. |
| `actuator` | Source actuator configuration; P_aux_MW in MW, edge temperatures keV, positions/widths normalized. | mixed declared configuration units | scalar fields / ActuatorConfig | Caller supplies the declared domain. |
| `sim` | Frozen model/numerical configuration, including nr, ntheta, dt in s, selectors and update cadences. | counts: 1; dt: s; closure scales per source | scalar fields / SimulationConfig | Review-supported reduced analytic domain; no restricted neural requirement or unevidenced branch support. |

#### 输出

| 名称 | 含义 | 单位 | 形状 / 类型 | 约束或默认值 |
| --- | --- | --- | --- | --- |
| `state` | Complete new seven-field PlasmaState with updated previous-geometry history; not an independently certified physical solution. | Te,Ti: keV; ne20: 1e20 m^-3; psi_ind,psi_edge: source poloidal-flux proxy; Phi_b_prev: Wb; dV_drho_prev: m^3 | Te/Ti/ne20/dV_drho_prev [nr]; psi_ind [nr+1] for selected face convention; psi_edge/Phi_b_prev scalar / PlasmaState | Caller supplies the declared domain. |

关系：Construct source profiles and current convention; obtain reduced geometry; bind Phi_b and dV/drho to the initial history fields. Source initial-current selectors and fixed bounded current/geometry updates remain unchanged.

适用前提：Install the pinned fusion extra in the tested Linux x86_64 CPython 3.12 profile.；Use positive grid counts/radius and compatible declared shapes; configure JAX x64 before numeric calls for the bound evidence.

无效输入：Original errors propagate; grid and axis selectors raise named ValueError. No newly invented checks, clipping or defaults.

运行失败：Dependency, shape, source computation and nonfinite behavior propagate unchanged; optional dependency import occurs only on symbol access.

证据上限：Bounded source behavior and installed nonregression only. No correctness qualification, human approval or whole D1 completion.

<a id="api-scirel.fusion.dynamics.step"></a>

### step

更新径向状态。

`from scirel.fusion.dynamics import step`

```python
step(state: PlasmaState, machine, actuator, sim)
```

**兼容参考**：未附独立完整科学合同。调用的物理输入、状态和限制见上面的主题；未知单位、模型有效性和通用正确性不从函数名称猜补。

<a id="api-scirel.fusion.dynamics.initialize_step_cache"></a>

### initialize_step_cache

建立演化缓存。

`from scirel.fusion.dynamics import initialize_step_cache`

```python
initialize_step_cache(state: PlasmaState, machine, actuator, sim) -> StepCache
```

**兼容参考**：未附独立完整科学合同。调用的物理输入、状态和限制见上面的主题；未知单位、模型有效性和通用正确性不从函数名称猜补。

<a id="api-scirel.fusion.dynamics.step_cached"></a>

### step_cached

使用缓存更新状态。

`from scirel.fusion.dynamics import step_cached`

```python
step_cached(state: PlasmaState, cache: StepCache, i, machine, actuator, sim)
```

**兼容参考**：未附独立完整科学合同。调用的物理输入、状态和限制见上面的主题；未知单位、模型有效性和通用正确性不从函数名称猜补。

<a id="api-scirel.fusion.dynamics.initial_state_0d"></a>

### initial_state_0d

构造约化 0D 初始状态。

`from scirel.fusion.dynamics import initial_state_0d`

```python
initial_state_0d(machine: MachineConfig, actuator: ActuatorConfig, sim: SimulationConfig)
```

**已有详细合同**：`scirel.fusion.initial-state-0d`。以下内容由本版 canonical 记录投影，完整机器可读版本见 Agent 的对应 API 文件。

#### 输入

| 名称 | 含义 | 单位 | 形状 / 类型 | 约束或默认值 |
| --- | --- | --- | --- | --- |
| `machine` | Source machine configuration; R0,a in m, Bt in T, Ip in A, kappa/delta/Zeff dimensionless. | mixed declared configuration units | scalar fields / MachineConfig | Use exact source config defaults or explicitly selected source-admissible controls. |
| `actuator` | Source actuator configuration; P_aux_MW in MW, edge temperatures keV, positions/widths normalized. | mixed declared configuration units | scalar fields / ActuatorConfig | Caller supplies the declared domain. |
| `sim` | Frozen model/numerical configuration, including nr, ntheta, dt in s, selectors and update cadences. | counts: 1; dt: s; closure scales per source | scalar fields / SimulationConfig | Review-supported reduced analytic domain; no restricted neural requirement or unevidenced branch support. |

#### 输出

| 名称 | 含义 | 单位 | 形状 / 类型 | 约束或默认值 |
| --- | --- | --- | --- | --- |
| `state` | Complete new seven-field PlasmaState with updated previous-geometry history; not an independently certified physical solution. | Te,Ti: keV; ne20: 1e20 m^-3; psi_ind,psi_edge: source poloidal-flux proxy; Phi_b_prev: Wb; dV_drho_prev: m^3 | Te/Ti/ne20/dV_drho_prev [nr]; psi_ind [nr+1] for selected face convention; psi_edge/Phi_b_prev scalar / PlasmaState | Caller supplies the declared domain. |

关系：Use original radial initial_state, reduced geometry and thermal-energy integration, then reconstruct the source reduced profile at the same thermal energy with genuine predecessor fields.

适用前提：Install the pinned fusion extra in the tested Linux x86_64 CPython 3.12 profile.；Use positive grid counts/radius and compatible declared shapes; configure JAX x64 before numeric calls for the bound evidence.

无效输入：Original errors propagate; grid and axis selectors raise named ValueError. No newly invented checks, clipping or defaults.

运行失败：Dependency, shape, source computation and nonfinite behavior propagate unchanged; optional dependency import occurs only on symbol access.

证据上限：Bounded source behavior and installed nonregression only. No correctness qualification, human approval or whole D1 completion.

<a id="api-scirel.fusion.dynamics.zero_d_step_with_dt"></a>

### zero_d_step_with_dt

更新约化 0D 状态并返回实际步长。

`from scirel.fusion.dynamics import zero_d_step_with_dt`

```python
zero_d_step_with_dt(state: PlasmaState, machine: MachineConfig, actuator: ActuatorConfig, sim: SimulationConfig)
```

**已有详细合同**：`scirel.fusion.zero-d-step-with-dt`。以下内容由本版 canonical 记录投影，完整机器可读版本见 Agent 的对应 API 文件。

#### 输入

| 名称 | 含义 | 单位 | 形状 / 类型 | 约束或默认值 |
| --- | --- | --- | --- | --- |
| `state` | Complete caller-owned PlasmaState; preserve all geometry-history fields. | Te,Ti: keV; ne20: 1e20 m^-3; psi_ind,psi_edge: source poloidal-flux proxy; Phi_b_prev: Wb; dV_drho_prev: m^3 | Te/Ti/ne20/dV_drho_prev [nr]; psi_ind [nr+1] for selected face convention; psi_edge/Phi_b_prev scalar / PlasmaState | Genuine initialized predecessor with selected source shape and lifecycle; no captured-answer or substituted history. |
| `machine` | Source machine configuration; R0,a in m, Bt in T, Ip in A, kappa/delta/Zeff dimensionless. | mixed declared configuration units | scalar fields / MachineConfig | Use exact source config defaults or explicitly selected source-admissible controls. |
| `actuator` | Source actuator configuration; P_aux_MW in MW, edge temperatures keV, positions/widths normalized. | mixed declared configuration units | scalar fields / ActuatorConfig | Caller supplies the declared domain. |
| `sim` | Frozen model/numerical configuration, including nr, ntheta, dt in s, selectors and update cadences. | counts: 1; dt: s; closure scales per source | scalar fields / SimulationConfig | Review-supported reduced analytic domain; no restricted neural requirement or unevidenced branch support. |

#### 输出

| 名称 | 含义 | 单位 | 形状 / 类型 | 约束或默认值 |
| --- | --- | --- | --- | --- |
| `new_state` | Complete new seven-field PlasmaState with updated previous-geometry history; not an independently certified physical solution. | Te,Ti: keV; ne20: 1e20 m^-3; psi_ind,psi_edge: source poloidal-flux proxy; Phi_b_prev: Wb; dV_drho_prev: m^3 | Te/Ti/ne20/dV_drho_prev [nr]; psi_ind [nr+1] for selected face convention; psi_edge/Phi_b_prev scalar / PlasmaState | Caller supplies the declared domain. |
| `dt_eff_s` | Actual physical timestep used; caller must accumulate this value | s | scalar / floating array | Caller supplies the declared domain. |

关系：Frozen-power equation dW/dt=P_net-W/tau_E: W_new=exp(-dt_eff/(tau+1e-12))*W+(1-exp(-dt_eff/(tau+1e-12)))*tau*P_net, then max(W_new,1e-6) and source profile reconstruction. dt_eff=min(sim.dt,zero_d_dt_fraction_tauE*tau_E_proxy), with source proxy not tau_E used for this bound.

适用前提：Install the pinned fusion extra in the tested Linux x86_64 CPython 3.12 profile.；Use positive grid counts/radius and compatible declared shapes; configure JAX x64 before numeric calls for the bound evidence.

无效输入：Original errors propagate; grid and axis selectors raise named ValueError. No newly invented checks, clipping or defaults.

运行失败：Dependency, shape, source computation and nonfinite behavior propagate unchanged; optional dependency import occurs only on symbol access.

证据上限：Bounded source behavior and installed nonregression only. No correctness qualification, human approval or whole D1 completion.

## 平衡几何与输运闭合

物理说明：[平衡几何与输运闭合](tokamak/equilibrium-and-transport.md)。

<a id="api-scirel.fusion.geometry.solve_fixed_boundary_equilibrium"></a>

### solve_fixed_boundary_equilibrium

按配置取得约化或给定磁几何。

`from scirel.fusion.geometry import solve_fixed_boundary_equilibrium`

```python
solve_fixed_boundary_equilibrium(state, machine, actuator, sim)
```

**兼容参考**：未附独立完整科学合同。调用的物理输入、状态和限制见上面的主题；未知单位、模型有效性和通用正确性不从函数名称猜补。

<a id="api-scirel.fusion.geometry.read_geqdsk"></a>

### read_geqdsk

读取 G-EQDSK 磁平衡文件。

`from scirel.fusion.geometry import read_geqdsk`

```python
read_geqdsk(path)
```

**兼容参考**：未附独立完整科学合同。调用的物理输入、状态和限制见上面的主题；未知单位、模型有效性和通用正确性不从函数名称猜补。

<a id="api-scirel.fusion.surrogates.fusion_surrogates_effective_diffusivities"></a>

### fusion_surrogates_effective_diffusivities

将外部代理通量转换为有效扩散。

`from scirel.fusion.surrogates import fusion_surrogates_effective_diffusivities`

```python
fusion_surrogates_effective_diffusivities(rho, Te, Ti, ne20, q, machine, sim, eq=None)
```

**兼容参考**：未附独立完整科学合同。调用的物理输入、状态和限制见上面的主题；未知单位、模型有效性和通用正确性不从函数名称猜补。

<a id="api-scirel.fusion.transport.angioni_neoclassical_diffusivities"></a>

### angioni_neoclassical_diffusivities

取得来源 Angioni–Sauter 有效扩散。

`from scirel.fusion.transport import angioni_neoclassical_diffusivities`

```python
angioni_neoclassical_diffusivities(rho, Te, Ti, ne20, q, machine, sim, eq=None, _allow_neonn_fallback: bool=True)
```

**兼容参考**：未附独立完整科学合同。调用的物理输入、状态和限制见上面的主题；未知单位、模型有效性和通用正确性不从函数名称猜补。

<a id="api-scirel.fusion.transport.chang_hinton_neoclassical_diffusivities"></a>

### chang_hinton_neoclassical_diffusivities

取得来源约化 Chang–Hinton 有效扩散。

`from scirel.fusion.transport import chang_hinton_neoclassical_diffusivities`

```python
chang_hinton_neoclassical_diffusivities(rho, Te, Ti, ne20, q, machine, sim, eq=None)
```

**兼容参考**：未附独立完整科学合同。调用的物理输入、状态和限制见上面的主题；未知单位、模型有效性和通用正确性不从函数名称猜补。

## 加热、电流与诊断

物理说明：[加热、电流与诊断](tokamak/heating-current-diagnostics.md)。

<a id="api-scirel.fusion.diagnostics.compute_diagnostics"></a>

### compute_diagnostics

计算模型诊断字典。

`from scirel.fusion.diagnostics import compute_diagnostics`

```python
compute_diagnostics(state, machine, actuator=None, sim=None, include_equilibrium=True, *, rho=None, eq=None, current_components=None, heat_diag=None)
```

**兼容参考**：未附独立完整科学合同。调用的物理输入、状态和限制见上面的主题；未知单位、模型有效性和通用正确性不从函数名称猜补。

<a id="api-scirel.fusion.diagnostics.total_heating_sources"></a>

### total_heating_sources

组合电子和离子温度源项。

`from scirel.fusion.diagnostics import total_heating_sources`

```python
total_heating_sources(rho, state, machine, actuator, sim, eq=None, dV_drho=None)
```

**兼容参考**：未附独立完整科学合同。调用的物理输入、状态和限制见上面的主题；未知单位、模型有效性和通用正确性不从函数名称猜补。

<a id="api-scirel.fusion.diagnostics.current_components_from_state"></a>

### current_components_from_state

组合电流组成。

`from scirel.fusion.diagnostics import current_components_from_state`

```python
current_components_from_state(rho, state, machine, actuator, sim, eq=None, q=None)
```

**兼容参考**：未附独立完整科学合同。调用的物理输入、状态和限制见上面的主题；未知单位、模型有效性和通用正确性不从函数名称猜补。

## 时变驱动与优化

物理说明：[时变驱动与优化](tokamak/control-and-optimization.md)。

<a id="api-scirel.fusion.controls.apply_control_vector"></a>

### apply_control_vector

将优化控制向量映射到 pytree 配置。

`from scirel.fusion.controls import apply_control_vector`

```python
apply_control_vector(x_phys, machine: PytreeMachineConfig, actuator: PytreeActuatorConfig, sim, names=CONTROL_NAMES)
```

**兼容参考**：未附独立完整科学合同。调用的物理输入、状态和限制见上面的主题；未知单位、模型有效性和通用正确性不从函数名称猜补。

<a id="api-scirel.fusion.controls.Waveform"></a>

### Waveform

单个物理输入的时间波形。

`from scirel.fusion.controls import Waveform`

构造字段按下面的声明传入；未写默认值的字段必须提供。

<details><summary>展开字段、类型与源码默认值</summary>

| 字段 | 类型声明 | 源码默认值 |
| --- | --- | --- |
| `times` | `jnp.ndarray` | 必填 |
| `values` | `jnp.ndarray` | 必填 |
| `hold_left` | `bool` | `True` |
| `hold_right` | `bool` | `True` |
| `interpolation` | `str` | `'linear'` |

</details>

**兼容参考**：未附独立完整科学合同。调用的物理输入、状态和限制见上面的主题；未知单位、模型有效性和通用正确性不从函数名称猜补。

<a id="api-scirel.fusion.controls.ScenarioWaveform"></a>

### ScenarioWaveform

多物理输入的场景波形。

`from scirel.fusion.controls import ScenarioWaveform`

构造字段按下面的声明传入；未写默认值的字段必须提供。

<details><summary>展开字段、类型与源码默认值</summary>

| 字段 | 类型声明 | 源码默认值 |
| --- | --- | --- |
| `controls` | `Mapping[str, Waveform]` | 必填 |
| `name` | `str` | `'custom'` |

</details>

`value(self, key: str, t, default=None)`。

**兼容参考**：未附独立完整科学合同。调用的物理输入、状态和限制见上面的主题；未知单位、模型有效性和通用正确性不从函数名称猜补。

<a id="api-scirel.fusion.controls.apply_waveform_controls"></a>

### apply_waveform_controls

在指定时间应用场景波形。

`from scirel.fusion.controls import apply_waveform_controls`

```python
apply_waveform_controls(machine: MachineConfig, actuator: ActuatorConfig, waveform: ScenarioWaveform | None, t)
```

**兼容参考**：未附独立完整科学合同。调用的物理输入、状态和限制见上面的主题；未知单位、模型有效性和通用正确性不从函数名称猜补。

<a id="api-scirel.fusion.optimization.autodiff_value_and_grad_pytree"></a>

### autodiff_value_and_grad_pytree

计算控制目标及梯度。

`from scirel.fusion.optimization import autodiff_value_and_grad_pytree`

```python
autodiff_value_and_grad_pytree(z, objective='Q', base_machine: PytreeMachineConfig | None=None, base_actuator: PytreeActuatorConfig | None=None, base_sim: SimulationConfig | None=None, bounds=DEFAULT_CONTROL_BOUNDS, names=PYTREE_CONTROL_NAMES, constraints=DEFAULT_CONSTRAINTS, constraint_smooth_width: float=0.01, objective_weights=None)
```

**兼容参考**：未附独立完整科学合同。调用的物理输入、状态和限制见上面的主题；未知单位、模型有效性和通用正确性不从函数名称猜补。

<a id="api-scirel.fusion.optimization.optimize_controls_optax"></a>

### optimize_controls_optax

以 Optax 迭代控制参数。

`from scirel.fusion.optimization import optimize_controls_optax`

```python
optimize_controls_optax(x0_phys, objective='Q', base_machine: MachineConfig | PytreeMachineConfig | None=None, base_actuator: ActuatorConfig | PytreeActuatorConfig | None=None, base_sim: SimulationConfig | None=None, bounds=DEFAULT_CONTROL_BOUNDS, names=PYTREE_CONTROL_NAMES, n_iter: int=10, learning_rate: float=0.01, gradient_mode: str='autodiff', constraints=DEFAULT_CONSTRAINTS, constraint_smooth_width: float=0.01, objective_weights=None, profile_timing: bool=False, max_grad_norm: float | None=None, max_update_norm: float | None=None, iteration_callback: Callable[[dict[str, Any]], None] | None=None)
```

**兼容参考**：未附独立完整科学合同。调用的物理输入、状态和限制见上面的主题；未知单位、模型有效性和通用正确性不从函数名称猜补。

<a id="api-scirel.fusion.optimization.waveform_objective_from_z"></a>

### waveform_objective_from_z

计算波形参数目标。

`from scirel.fusion.optimization import waveform_objective_from_z`

```python
waveform_objective_from_z(z, times, bounds, base_machine=None, base_actuator=None, base_sim=None, objective='Q', keys=('Ip_MA', 'P_aux_MW'), smoothness_weight: float=0.0, slew_weight: float=0.0, constraints=DEFAULT_CONSTRAINTS, constraint_smooth_width: float=0.01, objective_weights=None, fixed_control_values=None, fixed_start: bool=False, fixed_final: bool=False, fixed_endpoint_keys=None, waveform_constraint_mode: str='auto')
```

**兼容参考**：未附独立完整科学合同。调用的物理输入、状态和限制见上面的主题；未知单位、模型有效性和通用正确性不从函数名称猜补。

<a id="api-scirel.fusion.optimization.optimize_waveform_optax"></a>

### optimize_waveform_optax

以 Optax 迭代波形参数。

`from scirel.fusion.optimization import optimize_waveform_optax`

```python
optimize_waveform_optax(z0=None, times=None, initial_control_values=None, bounds=None, objective='Q', keys=('Ip_MA', 'P_aux_MW'), base_machine=None, base_actuator=None, base_sim=None, n_iter: int=10, learning_rate: float=0.01, gradient_mode: str='autodiff', smoothness_weight: float=0.0, slew_weight: float=0.0, constraints=DEFAULT_CONSTRAINTS, constraint_smooth_width: float=0.01, objective_weights=None, profile_timing: bool=False, fixed_endpoints: bool=True, fixed_endpoint_keys=None, fixed_start: bool | None=None, fixed_final: bool | None=None, waveform_constraint_mode: str='auto', max_grad_norm: float | None=None, max_update_norm: float | None=None, iteration_callback: Callable[[dict[str, Any]], None] | None=None)
```

**兼容参考**：未附独立完整科学合同。调用的物理输入、状态和限制见上面的主题；未知单位、模型有效性和通用正确性不从函数名称猜补。

