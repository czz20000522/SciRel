科学数据交换与显示边界：一份扩展 EQDSK 记录
============================================

这一章回答两个问题：**一份扩展 EQDSK 文本怎样变成 Python 映射；写回或读失败时，旧状态和旧文件能不能保住？** 它同时说明为什么这不是绘图教程：本章的公开入口只负责文本、字段和数组，不负责坐标轴、单位、色标、等值线或图形对象。

当前章节的资产集只有三个入口：``read_eqdsk``、``write_eqdsk`` 和可变映射封装 ``EQDSK``。它们操作的是本项目声明的扩展方言，不是标准 EFIT gEQDSK，也不分配 COCOS、单位或物理含义。所谓“显示边界”，就是数据合同能支持哪些显示决定、不能支持哪些决定；下面的代码不生成任何图。

一份最小记录长什么样
--------------------

这个方言的固定结构是：48 字符标题，四个 4 字符整数（``cursign, nnr, nnz, nnv``），四个 5 值标量记录，五条长度为 ``nnv`` 的 profile，C 顺序的 ``(nnz, nnr)`` psi 网格，q profile，以及定宽的 limiter/vessel 坐标对。下面的映射刚好满足这些尺寸。

.. code-block:: python

   from pathlib import Path
   from tempfile import TemporaryDirectory
   import numpy as np
   from scirel.io import read_eqdsk, write_eqdsk

   mapping = dict(
       title="MINIMAL EXTENDED EQDSK", cursign=-1, nnr=3, nnz=2, nnv=3,
       rbox=2.0, zbox=2.0, psi_lim=-0.2, Ip=-4.0,
       tor_flux=np.array([1.0, 2.0, 3.0]),
       p_flux=np.array([0.1, 0.2, 0.3]),
       rbphi_flux=np.array([-1.0, 0.0, 1.0]),
       pprime_flux=np.array([0.5, 0.6, 0.7]),
       q_flux=np.array([0.8, 0.9, 1.0]),
       psi=np.array([[0.0, 1.0, 2.0], [3.0, 4.0, 5.0]]),
       nlim_pairs=2, nves_pairs=1,
       lim_pairs=np.array([[0.0, -1.0], [2.0, 1.0]]),
       ves_pairs=np.array([[0.0, 0.0]]),
   )
   with TemporaryDirectory() as directory:
       path = Path(directory) / "minimal.eqdsk"
       write_eqdsk(mapping, path)
       lines = path.read_text().splitlines()
       print("first line:", repr(lines[0]))
       print("line lengths:", [len(line) for line in lines])
       got = read_eqdsk(path)
       print("title:", repr(got["title"]))
       print("dims:", got["cursign"], got["nnr"], got["nnz"], got["nnv"])
       print("psi:", got["psi"].tolist())
       print("R row:", got["R"][0].tolist())
       print("Z col:", got["Z"][:, 0].tolist())
       print("q_flux:", got["q_flux"].tolist())

实际输出：

.. code-block:: text

   first line: 'MINIMAL EXTENDED EQDSK                            -1   3   2   3'
   line lengths: [64, 80, 80, 80, 80, 48, 48, 48, 48, 80, 16, 48, 10, 80, 16]
   title: 'MINIMAL EXTENDED EQDSK                          '
   dims: -1 3 2 3
   psi: [[0.0, 1.0, 2.0], [3.0, 4.0, 5.0]]
   R row: [0.0, 1.0, 2.0]
   Z col: [-1.0, 1.0]
   q_flux: [0.8, 0.9, 1.0]

第一行正好 64 字符：48 字符标题加四个 4 字符整数。第二到第五行是四个标量记录，每行 80 字符，因为每行放 5 个 16 字符字段。四条 profile 各 48 字符（3 个值），q profile 也是 48；psi 有 6 个值，所以先写满 80 字符的一行，再剩 16 字符的一行；计数记录是 10 字符；limiter/vessel 共 6 个坐标值，同样是 80 加 16。读回来的 ``psi`` 形状是 ``(nnz, nnr) = (2, 3)``，不是 ``(3, 2)``。

``title`` 读回来带尾部空格，因为方言把标题补齐到 48 字符；这不是解析器多加的空白。``R`` 的第一行是 ``[0, 1, 2]``，``Z`` 的第一列是 ``[-1, 1]``：这两个轴不是文件里独立存储的数组，而是读取时由 ``rbox``、``zbox`` 和网格尺寸重建的。

这一节不能推出：这 15 行文本不是一个完整的平衡解；``psi``、``q_flux`` 和坐标只是按方言搬运的数值；没有单位、COCOS 或磁轴语义；读回形状正确也不证明物理内容正确。

定宽、字段顺序和严格模式
------------------------

写出去再读回来，最直接的检查是逐字段相等。下面的代码同时检查 psi、limiter 坐标和 q profile，并在文件尾部追加一条记录，比较严格与非严格模式。

.. code-block:: python

   from pathlib import Path
   from tempfile import TemporaryDirectory
   import numpy as np
   from scirel.io import EQDSKFormatError, read_eqdsk, write_eqdsk

   mapping = dict(
       title="MINIMAL EXTENDED EQDSK", cursign=-1, nnr=3, nnz=2, nnv=3,
       rbox=2.0, zbox=2.0, psi_lim=-0.2, Ip=-4.0,
       tor_flux=np.array([1.0, 2.0, 3.0]),
       p_flux=np.array([0.1, 0.2, 0.3]),
       rbphi_flux=np.array([-1.0, 0.0, 1.0]),
       pprime_flux=np.array([0.5, 0.6, 0.7]),
       q_flux=np.array([0.8, 0.9, 1.0]),
       psi=np.array([[0.0, 1.0, 2.0], [3.0, 4.0, 5.0]]),
       nlim_pairs=2, nves_pairs=1,
       lim_pairs=np.array([[0.0, -1.0], [2.0, 1.0]]),
       ves_pairs=np.array([[0.0, 0.0]]),
   )
   with TemporaryDirectory() as directory:
       path = Path(directory) / "roundtrip.eqdsk"
       write_eqdsk(mapping, path)
       got = read_eqdsk(path)
       print("psi equal:", np.array_equal(got["psi"], mapping["psi"]))
       print("lim equal:", np.array_equal(got["lim_pairs"], mapping["lim_pairs"]))
       print("q equal:", np.array_equal(got["q_flux"], mapping["q_flux"]))
       original = path.read_text()
       path.write_text(original + "TRAILING\n")
       try:
           read_eqdsk(path)
       except EQDSKFormatError as error:
           print(type(error).__name__, error)
       relaxed = read_eqdsk(path, strict=False)
       print("relaxed psi:", relaxed["psi"].tolist())

实际输出：

.. code-block:: text

   psi equal: True
   lim equal: True
   q equal: True
   EQDSKFormatError unexpected trailing records after coordinates: 1
   relaxed psi: [[0.0, 1.0, 2.0], [3.0, 4.0, 5.0]]

三个 ``True`` 说明这些字段经过固定宽度文本后仍逐位相等；它们不是浮点近似比较。严格模式在声明区之后发现一条多余记录就报 ``EQDSKFormatError``；``strict=False`` 允许尾部记录，但仍然要求每个声明的 profile、网格和坐标值都存在。也就是说，非严格模式放宽的只是“尾部多余”，不是“缺失字段”或“定宽坐标格式”。

这一节不能推出：文本往返一致不等于物理保真；写入时使用 ``16.9E`` 字段，能表示的数值范围有限；严格/非严格只改变尾部策略，不改变字段次序、尺寸或原点约定；它也不提供 EFIT 的磁轴标量或 COCOS 解释。

失败时不要破坏旧状态
--------------------

读失败和写失败是两种不同的状态问题。``EQDSK`` 封装在读取时先解析到局部结果，成功后才清空并更新自己；``write_eqdsk`` 在打开目标文件之前完成结构校验，所以校验失败不会截断旧文件。下面的代码分别制造一次截断读取和一次不可表示的原点写入。

.. code-block:: python

   from pathlib import Path
   from tempfile import TemporaryDirectory
   import numpy as np
   from scirel.io import EQDSK, EQDSKFormatError, write_eqdsk

   mapping = dict(
       title="MINIMAL EXTENDED EQDSK", cursign=-1, nnr=3, nnz=2, nnv=3,
       rbox=2.0, zbox=2.0, psi_lim=-0.2, Ip=-4.0,
       tor_flux=np.array([1.0, 2.0, 3.0]),
       p_flux=np.array([0.1, 0.2, 0.3]),
       rbphi_flux=np.array([-1.0, 0.0, 1.0]),
       pprime_flux=np.array([0.5, 0.6, 0.7]),
       q_flux=np.array([0.8, 0.9, 1.0]),
       psi=np.array([[0.0, 1.0, 2.0], [3.0, 4.0, 5.0]]),
       nlim_pairs=2, nves_pairs=1,
       lim_pairs=np.array([[0.0, -1.0], [2.0, 1.0]]),
       ves_pairs=np.array([[0.0, 0.0]]),
   )
   with TemporaryDirectory() as directory:
       path = Path(directory) / "state.eqdsk"
       write_eqdsk(mapping, path)
       state = EQDSK(path)
       old_psi = state["psi"].copy()
       print("before:", repr(state["title"]), old_psi.sum())
       lines = path.read_text().splitlines()
       path.write_text("\n".join(lines[:-1]) + "\n")
       try:
           state.read_eqdsk(path)
       except EQDSKFormatError as error:
           print("read error:", error)
       print("after:", repr(state["title"]), state["psi"].sum(),
             np.array_equal(state["psi"], old_psi))
       write_eqdsk(mapping, path)
       original = path.read_text()
       bad = dict(mapping)
       bad["R"], bad["Z"] = np.meshgrid(
           np.linspace(1.0, 3.0, 3), np.linspace(-1.0, 1.0, 2)
       )
       try:
           write_eqdsk(bad, path)
       except EQDSKFormatError as error:
           print("write error:", error)
       print("unchanged:", path.read_text() == original)

实际输出：

.. code-block:: text

   before: 'MINIMAL EXTENDED EQDSK                          ' 15.0
   read error: truncated limiter/vessel coordinates: expected 6 values
   after: 'MINIMAL EXTENDED EQDSK                          ' 15.0 True
   write error: R/Z grid is not representable: extended dialect fixes R origin at 0 and Z at +/-zbox/2
   unchanged: True

读取失败后，``state`` 的标题和 ``psi`` 仍然是旧值，``psi`` 的和仍是 ``15.0``；封装没有先清空自己再解析。写入失败的原因不是磁盘错误，而是调用者附带的 ``R/Z`` 网格从 ``R=1`` 开始，而方言固定 ``R`` 原点为 0、``Z`` 以 ``-zbox/2`` 到 ``+zbox/2`` 重建；这个原点无法表示，所以在打开目标文件之前就被拒绝，旧文件逐字节不变。

这一节不能推出：这保证的是“校验失败不截断”和“读失败保留旧映射”，不是任意 I/O 失败下的原子写入；文件系统错误仍会直接传播；它也不是跨进程事务或备份机制。要保留旧文件，调用者仍应自己管理版本和备份。

显示边界：数组、坐标和不在合同里的东西
--------------------------------------

最后把读回的数据当成“要显示的东西”看一眼。下面的代码只打印数组结构和坐标范围，不画图；它要说明的是，显示所需的哪些信息已经由方言固定，哪些根本不在合同里。

.. code-block:: python

   from pathlib import Path
   from tempfile import TemporaryDirectory
   import numpy as np
   from scirel.io import read_eqdsk, write_eqdsk

   mapping = dict(
       title="MINIMAL EXTENDED EQDSK", cursign=-1, nnr=3, nnz=2, nnv=3,
       rbox=2.0, zbox=2.0, psi_lim=-0.2, Ip=-4.0,
       tor_flux=np.array([1.0, 2.0, 3.0]),
       p_flux=np.array([0.1, 0.2, 0.3]),
       rbphi_flux=np.array([-1.0, 0.0, 1.0]),
       pprime_flux=np.array([0.5, 0.6, 0.7]),
       q_flux=np.array([0.8, 0.9, 1.0]),
       psi=np.array([[0.0, 1.0, 2.0], [3.0, 4.0, 5.0]]),
       nlim_pairs=2, nves_pairs=1,
       lim_pairs=np.array([[0.0, -1.0], [2.0, 1.0]]),
       ves_pairs=np.array([[0.0, 0.0]]),
   )
   with TemporaryDirectory() as directory:
       path = Path(directory) / "display.eqdsk"
       write_eqdsk(mapping, path)
       got = read_eqdsk(path)
       print("psi shape:", got["psi"].shape)
       print("R range:", got["R"].min(), got["R"].max())
       print("Z range:", got["Z"].min(), got["Z"].max())
       expected_R, _ = np.meshgrid(
           np.linspace(0.0, 2.0, 3), np.linspace(-1.0, 1.0, 2)
       )
       print("R reconstructed:", np.array_equal(got["R"], expected_R))
       print("psi:")
       print(got["psi"])

实际输出：

.. code-block:: text

   psi shape: (2, 3)
   R range: 0.0 2.0
   Z range: -1.0 1.0
   R reconstructed: True
   psi:
   [[0. 1. 2.]
    [3. 4. 5.]]

``psi`` 是 ``(nnz, nnr)`` 的二维数组；``R`` 覆盖 ``0`` 到 ``2``，``Z`` 覆盖 ``-1`` 到 ``1``，并且 ``R`` 与 ``linspace(0, rbox, nnr)`` 的网格逐位相同。这些信息足以让调用者自己决定怎么画，但合同没有给出单位、COCOS、轴标签、等值线级别、颜色映射或图形对象。``cursign``、``psi_lim``、``Ip`` 等标量也不附带物理语义。

如果调用者把图的原点平移到别处，或者把 ``R`` 当成任意起点存储的坐标，就会和方言的固定原点约定冲突；写入端正是用 ``R/Z`` 网格或 ``r_origin/z_origin`` 来提前发现这种不可表示的情况。显示时也应遵守同一个原点，否则数组没变，图的物理位置已经变了。

这一节不能推出：本章不是绘图教程，当前资产集没有绘图函数；读出的数组不是“可直接发表的图”；没有单位/COCOS 就不能擅自给坐标轴加 SI 标签；这不是 EFIT gEQDSK、GENRAY 或任何标准平衡格式的兼容声明；文本交换边界也不验证平衡求解的物理正确性。

什么时候用哪个入口
------------------

- 一次性把文件解析成字典：:doc:`../reference/generated/scirel.io.read-eqdsk`。
- 一次性把已验证的映射写成文本：:doc:`../reference/generated/scirel.io.write-eqdsk`。
- 需要在多次读写之间保留可变映射，并让读失败不破坏旧状态：:doc:`../reference/generated/scirel.io.eqdsk-class`。
- 解析或校验失败时捕获 ``EQDSKFormatError``；文件系统错误按普通 I/O 异常处理。

本章的边界是结构交换：它保证字段次序、尺寸、定宽表示、原点约定和失败状态，不保证标准 EFIT 兼容、单位/COCOS 分配、轮廓选择、绘图或物理平衡。需要这些信息时，应在调用者一侧显式建立，并记录所用的方言和原点约定；完整签名、参数和失败行为见上面的 API 参考页。
