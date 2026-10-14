# 复误差函数与 Maxwellian 近似的保留变体

本批保留 GPDF 的 Faddeeva 默认 32 阶、DR 默认 16 阶、Maxwellian FFT 默认 32 阶，和固定 8/12/16/24 极点近似。它们与高准确度 `evaluate_plasma_dispersion` 是不同算法合同，未合并成单一默认实现。依据是 Weideman 1994 的有理展开（https://epubs.siam.org/doi/10.1137/0731077）、定义 $w(z)=e^{-z^2}\operatorname{erfc}(-iz)$ 与 $Z=i\sqrt\pi w$。

历史正虚轴 `exp(y²)*erfc(y)` 在 y=40 给出 inf*0，而真实值有限；改用 erfcx。两个 Faddeeva 入口的显式 None 仍选择各自默认阶数，FFT 的显式 None 则拒绝。非有限输入、无效阶数立即拒绝；真实下半平面指数超出 float64 时明确失败，不能伪造有限值。矩阵 J-pole 求值从 MATLAB `length(z)` 的局部循环改为对所有元素计算。

独立测试使用 SciPy `wofz`、80 位 mpmath 定义式和 70 位实轴 Gaussian Cauchy 积分，而不读取来源捕获答案。反射、默认阶数、归一化、矩阵 shape 和显式失败分别验证。固定极点近似的误差容差与高阶 Faddeeva 的容差不同；不声称固定极点在任意下半平面具有统一精度。

数值极点表由冻结 D1 逐字数值转录，来源摘要记在数据模块。这是私有交付的来源关系，未产生再分发许可；可执行实现独立编写，未封装 MATLAB 运行时。来源 D0/D1 原字节与旧失败记录只读保留。
