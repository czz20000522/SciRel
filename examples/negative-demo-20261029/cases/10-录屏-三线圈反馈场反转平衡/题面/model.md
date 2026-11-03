# 有限自由边界模型、Green算子与状态协议

mu0=4pi*1e-7。R_i=(i-1)*.14/16，Z_j=-.75+(j-1)*1.5/32，i=1..17、j=1..33；dR=.14/16、dZ=1.5/32。数组第一轴R、第二轴Z，中面一基索引Z0=17。磁通psi单位Wb（按下列Green归一约定），压力Pa，Jphi A/m²。给定Be与Rs是归一化标尺；Pm=Be²/(2mu0)，u=psi/(Be Rs²)。Jphi的符号由下式决定，不因目标电流为负而翻转整场。

选定连续闭合为Delta*psi=psi_RR-psi_R/R+psi_ZZ=-mu0 R² dP/dpsi，不增加额外环向场函数项；当前要求结果以本节指定的有限更新协议为准。

## 边界节点、有限线圈和Green数据

非轴边界共有Nb=2(nR-1)+(nZ-2)=63点，按b=1..63固定排列：b<nR时(i_b,j_b)=(b+1,1)；b>Nb-nR+1时(i_b,j_b)=(Nb-b+2,nZ)；其余(i_b,j_b)=(nR,b-nR+2)。顺序从下端R第二点走到右下角，沿右壁上行，再从右上角向R第二点返回；轴两角不在列表。

每个线圈截面在R_l±h_l/2各等距10点、Z_l±w_l/2各等距100点，包含端点；每个样点视作电流I_l/1000的圆环。这是等权样点和，不是梯形端权。三个线圈几何/电流见inputs.json，全部正1MA。

场点(r,z)与环样点(r',z')的m=4rr'/[(r+r')²+(z-z')²]。m=0时G=0；其余G=sqrt(rr')/[(2pi)sqrt(m)]*[(2-m)K(m)-2E(m)]。K/E为下一节固定近似。预计算psiCoil_b=Σ_(l,a,c)mu0*(I_l/1000)*G(R_ib,Z_jb;r_la,z_lc)，并保存Gs_(i,j,b)=G(R_ib,Z_jb;R_i,Z_j)，仅内部i=2..16、j=2..32参与后续等离子体积分，其它Gs为0。当前网格/线圈无重合奇点，不另加自能正则化。

## 指定椭圆积分近似

令p=1-m。m=1时K=1e300、E=1；否则K=A(p)-B(p)ln p，E=C(p)-D(p)ln p。四个多项式按Horner顺序：

A=((((.01451196212p+.03742563713)p+.03590092383)p+.09666344259)p+1.38629436112)，
B=((((.00441787012p+.03328355346)p+.06880248576)p+.12498593597)p+.5)，
C=((((.01736506451p+.04757383546)p+.0626060122)p+.44325141463)p+1)，
D=((((.00526449639p+.04069697526)p+.09200180037)p+.2499836831)p)。

固定近似与有限样点和是当前模型，不自行替换另一特殊函数/连续积分并假定零误差；参数m不能误作模数sqrt(m)。

## 初值与三层循环

先M=max_b|psiCoil_b|。初始psi=.01*[.1-exp(-((R/.14-.2)²/.3²+(Z/.75)²/.4²))]*M；不预先覆盖初始轴/边界。C=Ctmp=1、CI=CItmp=1，psi0=psi1=psi2=psi，psiOuter=psi，innerDelta=.1，boundaryDelta=100tol，Be1=1.1Be；tol=1e-9Wb，coilCounter=1。无重启或外部二维初值。

当|Be1/Be-1|>5e-4且coilCounter<200时进行线圈反馈周期：先boundaryCounter=1、innerCounter=1，**不重置boundaryDelta、psiOuter、C、CI、Ctmp、CItmp或psi0**。随后当boundaryCounter<=30且boundaryDelta>2tol时进行边界更新。

边界更新先由当前psi形成Jfd：内部Jfd_(i,j)=-{[psi_(i+1,j)-2psi_(i,j)+psi_(i-1,j)]/dR²-[psi_(i+1,j)-psi_(i-1,j)]/(2dR R_i)+[psi_(i,j+1)-2psi_(i,j)+psi_(i,j-1)]/dZ²}/(mu0 R_i)，四边Jfd=0。此时sectionCurrent=ΣJfd*dR*dZ。

接着psib_b=CI*psiCoil_b+Σ_(i=2..16,j=2..32)mu0*CI*Gs_(i,j,b)*Jfd_(i,j)*dR*dZ；CI同时乘线圈项和等离子体项，不只改变线圈。按i、j、b逐项累加，不再加积分端权。psib在随后整个内层迭代中保持。

innerDelta=10tol、innerCounter=1。boundaryCounter=1时设jit=1、w=w0=.99；后续边界轮保留w，不启用另一离散格式。只要innerCounter<=20000且innerDelta>tol，执行空间内步。

## 内步、C反馈和边界覆盖

以内步进入时psi与C计算P=C Pm beta_s exp(-alpha u)(1+sigma u)^n，dP=C Pm beta_s exp(-alpha u)(1+sigma u)^(n-1)*[-alpha(1+sigma u)+n sigma]/(Be Rs²)，Jphi=R*dP。P/J在全部17×33节点形成，不作非负截断或等离子体区域mask。sectionCurrent=ΣJphi*dR*dZ覆盖前面Jfd的全截面电流变量。

中面反馈电流Iw=Σ_(i=1..i_b(Z0)-1)2pi*Jphi_(i,Z0)*R_i*dR。i_b(Z0)指边界列表第17项的径向索引，当前为17，所以求和i=1..16；它不是全R-Z积分，也不包括R末点。目标Izeta0直接为inputs.json负值；原输入牌组正值已显式取负一次，不再重复。

若boundaryCounter>1，在P/dP/J/Iw已经形成后，C←w*C+(1-w)*Ctmp*Izeta0/Iw。boundaryCounter=1不更新C，即使内步>100也不启用另一题的反馈门。本轮空间更新仍使用更新C之前的dP，新C下一内步才影响压力源。

对i=2..16、j=2..32，由同一旧场psi0计算：

psiNew_(i,j)=w*psi0_(i,j)+(1-w)*.5dZ²*{R_i/dR²*[(psi0_(i+1,j)-psi0_(i,j))/(R_i+.5dR)-(psi0_(i,j)-psi0_(i-1,j))/(R_i-.5dR)]+[psi0_(i,j+1)+psi0_(i,j-1)]/dZ²+mu0 R_i² dP_(i,j)}。

保留jit1的径向半节点分母与.5dZ²，不换标准三点Jacobi/Gauss-Seidel式。随后先轴行psi(1,:)=0，再按63项顺序写入psi(i_b,j_b)=psib_b。Z上下端取Green边界，不是零法向导数，不再重写端部角点。

innerCounter+=1，innerDelta=max|psiNew-psi0|，psi2←psi1、psi1←psi0、psi0←psiNew，Ctmp←C。C步差不计入innerDelta。内层退出后boundaryDelta=max|psi-psiOuter|、psiOuter←psi，boundaryCounter+=1，再判断下一边界更新。达到20000内步仍可能继续边界/线圈层，上限退出不等于收敛。

## 外场反馈、停止与输出时刻

边界层退出后Be1=sqrt(2mu0*max_i P_(i,Z0))，CI←.95CI+.05CItmp*Be/Be1，coilCounter+=1、CItmp←CI，再检查最外层条件。若boundaryDelta已<=2tol，下一线圈周期可能跳过整个边界/内层，只用旧P重算Be1/CI；不得添加boundaryDelta重置或强制再解。Iw或Be1为0、出现非有限/复数时保留实际失败/HOLD，不加epsilon或更改目标使其可跑。

最后psi为更新后场；P/dP/Jphi/Iw保留最后内步更新前psi/C所算值，C/CI为反馈后值，Be1按保留P计算。若最后线圈周期跳过边界层，内/边界计数器为该周期重置的1，不能伪称总迭代数。输出三个判定innerDelta<=tol、boundaryDelta<=2tol、|Be1/Be-1|<=5e-4，全部为真且要求值有限实数才称有限协议收敛。

独立物理残差、网格收敛性、Green近似误差、反馈存在唯一性和物理有效范围的预算仍pending；有限停止规则本身不批准这些结论。
