# 原二次磁通的有限拓扑与受限边界规则

所有有限参数在inputs.json；本页只定义数学步骤，没有计算O点、边界磁通或轮廓答案。原磁通、域和四输出不变。支持范围是非退化、主O严格在limiter内、无相关X点的正常limited情景；更宽原条件单列保留。

## 1. 网格、输入与轴序

R_i=1/2+7i/320，i=0,…,64；Z_j=-1+j/40，j=0,…,84，单位m。两端都在原域端点，节点数组为[R,Z]：R[i,j]=R_i、Z[i,j]=Z_j。节点psi用原给定二次式构造，单位Wb/rad，不乘2π。实际有限差分步长取dR=R_1-R_0、dZ=Z_1-Z_0。输入舍入约定见JSON，不代入连续导数替换有限差分。

## 2. 候选点扫描、分类和主轴

先把梯度平方代理C的四周边界槽置0；内部节点计算

    gR=(psi[i+1,j]-psi[i-1,j])/(2dR)
    gZ=(psi[i,j+1]-psi[i,j-1])/(2dZ)
    C[i,j]=gR^2+gZ^2

C是筛选代理，不是另算带1/R²的物理Bp²。按i递增、内层j递增扫描内部节点，只有C严格小于其8个相邻节点时才生成候选；相等不算局部极小，不增加阈值、边缘候选或额外去重。

在该节点取

    hRR=(psi[i+1,j]-2psi[i,j]+psi[i-1,j])/dR^2
    hZZ=(psi[i,j+1]-2psi[i,j]+psi[i,j-1])/dZ^2
    h2RZ=(psi[i+1,j+1]+psi[i-1,j-1]-psi[i-1,j+1]-psi[i+1,j-1])/(2dR dZ)
    D=hRR*hZZ-h2RZ^2/4
    deltaR=-(gR*hZZ-h2RZ*gZ/2)/D
    deltaZ=-(gZ*hRR-h2RZ*gR/2)/D

注意h2RZ是上述实际有限交叉量；不能误把它当普通hRZ后再去掉1/2。只有abs(deltaR)<1.5dR且abs(deltaZ)<1.5dZ才接收。记录

    (R_i+deltaR, Z_j+deltaZ, psi[i,j]+(gR*deltaR+gZ*deltaZ)/2)

第三列是这一有限修正的磁通估计，不改成在新坐标重新代入解析psi或插值的另一答案。D>0归O，D<0归X；D==0的修正未在此定义，不加epsilon/扰动/正则化，仍属原HOLD边界，不能沿用前一个候选的delta。

O候选用最近R节点、最近Z节点处的limiter内部mask筛掉域外者。无O或筛后无O属于明确失败，不能用预填(R0,Z0,psi0)补救。多O按到计算域中心((Rmin+Rmax)/2,(Zmin+Zmax)/2)的距离平方递增排列；第0行是主O。精确等距不在本题新增tie规则，原HOLD保留，不用最低R/最低Z补规则。

X先按相对主O磁通差的平方递增排序，再仅保留(psi_X-psi_A)*current_sign<0者。若有X，仅从列表首项起作以下有限检查：沿主O到该X取n=int(max(abs(deltaR)/dR,abs(deltaZ)/dZ)+2)个含端点样本，双线性插值psi；若psi_X<psi_A则整条序列反号。需同时满足(max(p)-p_last)/(max(p)-p_first)<.001，以及最小p样本到主O距离平方<1e-4m²，才保留当前首项并停止删除；否则删首项继续。后续剩余项不被伪称全部重新验证。这一个首X筛选流程固定执行；discard_xpoints名称不作为可关闭它的开关。本题显式取true，不外延出另一套false语义。此固定步骤不构成diverted/多null工况已经覆盖；正常limited实例的X数组允许为空。

## 3. 闭limiter及双线性边界磁通

闭polygon顶点依次为(.85,-.63)、(1.68,-.63)、(1.68,.72)、(.85,.72)，再精确重复首点。它严格处于原矩形域内并包围原轴；不把计算域边界当limiter。

网格mask由该闭polygon的Path.contains_points(radius=0)内部判定构造。一般恰落边界的点无新的跨实现包含承诺；本题支持的是最近节点严格在limiter内部的主O。落在limiter边上的O候选、包含判定tie或退化polygon不被本有限样例悄悄解决。core的严格磁通条件也不把first-contact壁点当内部。

limiter细化使用实际网格交点，不另有待选refine数：对每个顶点，单轴cell索引=count(grid_coordinate<vertex_coordinate)-1。逐相邻顶点段，竖段取其跨过的水平网格线交点，横段取跨过的竖网格线交点；交点索引区间从两端较小cell索引+1到较大cell索引（两端规则以此为准）。加入该段结束顶点，按到结束顶点的欧氏距离递增排序，逐段连接所有细点，不去重。给每个细点按同一严格小于规则分配左下cell；点恰在网格线上使用其左/下cell。

对某cell内点(R,Z)，令a=(R-R_i)/dR、b=(Z-Z_j)/dZ，

    I[psi]=(1-a)(1-b)psi[i,j]+a(1-b)psi[i+1,j]
           +(1-a)b psi[i,j+1]+a b psi[i+1,j+1]

按细点第一次出现的cell顺序分组，再按该cell内原细点顺序生成全部psi_limiter值。current_sign=+1，psi_B取该列表的有符号最大值；相同最大值按列表首项，但本题不把一般接触tie扩展成已验证条件，也不额外请求一个未定义的接触点输出。细点列表为空或不能得到有限边界值则失败。

这是有限first-limiter-contact规则，不是连续polygon上另作解析极值优化。特意选一侧在网格线上，使正常first-contact可与节点场相容；不能借此预填边界psi答案。limited核心规则为(current_sign*(psi-psi_B)>0)乘内部mask，flag_limiter=True。没有X时不使用X[0]或域角点psi代替这个最终边界值。另一种基于主O连通填充的core函数只有显式给psi_B时才可接受空X：它从主O最近节点seed开始，先把seed写1，再按严格q<1的邻点规则作扫描填充，不是直接对全域作阈值。本题limited消费步骤仍是前述严格磁通条件乘limiter mask；四输出不增加mask任务，也不把两种mask算法混成一种。

## 4. 归一化场和已存在的单射线数学步骤

取实际主O行(R_A,Z_A,psi_A)，q_nodes=(psi-psi_A)/(psi_B-psi_A)。归一化分母必须有限非零；不改用原输入psi0代替有限主O磁通。对q_nodes建立矩形张量积三次插值样条，两个轴degree=3、平滑s=0、端点not-a-knot；使用原域，不外推。它对应RectBivariateSpline的插值数学约定。

对每个k=0,…,79，theta=2pi*k/80。theta从+Z向+R增加，不采用另一种默认角度。起点是主O，初始终点是(R_A+10sin(theta),Z_A+10cos(theta))m，依下述顺序裁剪：

1. 若abs(r1-r0)>1e-6m，rclip=clip(r1,Rmin,Rmax)，令z1=z0+(z1-z0)*abs((rclip-r0)/(r1-r0))，r1=rclip。
2. 随后若abs(z1-z0)>1e-6m，zclip=clip(z1,Zmin,Zmax)，令r1=r0+(r1-r0)*abs((zclip-z0)/(z1-z0))，z1=zclip。

每步沿当前射线方向缩短，不换成分别独立clip两个坐标。按t_l=l/999，l=0,…,999取1000个含端点线样本并评价q_l。令j是首次严格q_j>1的索引，

    f=(q_j-1)/(q_j-q_(j-1))
    crossing=(1-f)*P_j+f*P_(j-1)

只做此相邻两样本线性插值，不二分、不求连续解析根、不用高阶根替换。首次严格越过允许上一样本恰为1；不存在q>1或j==0、相邻差为0/非有限、样条不能构造等情形均不在有限trace定义域，必须显式失败，不能把全False的argmax默认0及最后一个样本拼成假闭合点。

## 5. 新的有限多射线组合、闭合和失败边界

按k递增组合上述80个已有数学射线步骤，输出每个实际crossing的(R,Z)，再精确复制第0点为第80点，得到81×2。没有X坐标列，不做依X点移动半角步，也不制造X占位值。这个有限采样组合和其定义域/失败合同是本题明确编写的glue；不是把某个高层函数的空X支持当作既有事实，也不是修改底层射线或critical kernel。

原四输出均要求实际结果：O/X候选数组、有限psi_B和81×2闭边界。合法空X用空数组而不是null；它本身不使trace失败。无有效O、limiter不严格在原域内、无有限psi_B、归一化失败或任一ray不在上节定义域内，均报告明确失败，不给一个只有HOLD/null的完整成功结果，不以删ray/补零/伪造轴来完成。上述异常的输入/工程报告不等于来源已有所有新保护，也不扩展为一般临界拓扑正规化。

原diverted、单/双null、多null、detH==0、主O等距/其他tie及已有轴有限值定义HOLD保持。正常limited配方不覆盖它们，不新增SOL/strike。参考适配和科学接受另行pending；本页无数值答案、容差、比较器或运行信用。
