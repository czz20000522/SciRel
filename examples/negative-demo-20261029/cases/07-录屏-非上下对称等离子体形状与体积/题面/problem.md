# 非上下对称等离子体边界的形状与体积

九个标量完全由题内有限轮廓、网格节点和 limiter_core_mask 配方决定，
不需要先求 Grad-Shafranov 平衡或读取外部装置数据。

给定以下完整有限几何输入，求 output-spec.json 的九个标量。原轮廓、六个参数和 theta 范围全部保留：
R(theta)=R0+a cos(theta+delta sin(theta))，
Z(theta)=Z0+b sin(theta)(1+eta sin(theta))，
R0=1.6 m、Z0=0.1 m、a=0.5 m、b=0.8 m、delta=0.3、eta=0.1，
theta∈[0,6.283185307179586] rad。

本次新选定256段采样：在原范围内按 k=0…255 等分取点，再精确复制第0点闭合成257点。没有重采样、平滑、极值插值或另选形状。原函数的 eta 保留上下不对称；不能用椭圆、解析极值或原参数直接替代有限顶点观测。

面积、周长、几何中心、短半径、伸长比及上下三角形度都取同一闭合折线的有限顶点/线段。体积另用本题完整给定的65×129矩形节点网格和同一多边形的 limiter_core_mask：
volume=2pi sum_(i,j)(R_grid[i,j]*dR*dZ*limiter_core_mask[i,j])。
每个节点取完整 dR*dZ，不用半权，不用多边形质心体积替代。网格范围、节点、步长、闭边界掩膜、轴序及精确判断规则均在 inputs.json 和 model.md 给出。

这是一个纯数据几何状态：core_boundary、R/Z节点图、dR/dZ和limiter_core_mask已由题内确定配方完整提供。无需把某个 equilibrium 对象或“先解GS”当作缺少的物理输入；也不声称这个给定边界已经是某个装置的收敛平衡或经过限器/磁通追踪。仅在将来调用特定接口时，属性装载属于实现工作。

没有普通输入或采样选择缺口。squareness、电流中心和整个 FGN-GEOM 的其余条件仍在本卡九输出范围之外，不因此新增本题输出或扩大覆盖。当前 candidate、scientific_review=pending；参考材料与运行链保持独立 HOLD: NOT_RUN。供题完整性不等待参考捕获/重放，本次未构造数组、运行科学内核、求解或计算答案。
