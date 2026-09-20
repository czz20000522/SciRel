/*
测试结果：
工作目录：this operator directory
命令：cc scientific_operator.c test_scientific_operator.c -lm -o test_scientific_operator && ./test_scientific_operator
环境变量：none
结果：4 passed
对照依据：source-derived fixture + hand-checkable formula + boundary failure
源码对照状态：source_unavailable: 本参考案例验证源码行级公式派生 fixture，未启动 Pleiades 对象运行时
证据来源：pleiades/fields.py:129-153::psi; pleiades/fields.py:154-194::BR,BZ; pleiades/fields.py:196-219::_compute_greens
运行环境：Docker image mcr.microsoft.com/devcontainers/python:1-3.12-bullseye / cc (Debian 10.2.1-6) 10.2.1 20210110
*/

#include "scientific_operator.h"

#include <math.h>
#include <stdio.h>

static int expect_close(const char *name, double actual, double expected)
{
    const double tolerance = 1.0e-12;

    if (fabs(actual - expected) > tolerance) {
        printf("%s mismatch: actual=%0.17g expected=%0.17g\n", name, actual, expected);
        return 0;
    }
    return 1;
}

static int expect_status(const char *name, GreenProjectionStatus actual, GreenProjectionStatus expected)
{
    if (actual != expected) {
        printf("%s status mismatch: actual=%d expected=%d\n", name, (int)actual, (int)expected);
        return 0;
    }
    return 1;
}

/* 验证：三源两点评价 fixture 按源码的 current @ Green 矩阵公式逐项投影。 */
static int test_vector_projection_fixture(void)
{
    const double currents[3] = {2.0, -1.0, 0.5};
    const double gpsi[6] = {
        1.0, 2.0,
        3.0, 4.0,
        -2.0, 1.0
    };
    const double gbr[6] = {
        0.5, 1.0,
        1.5, 2.0,
        2.5, -1.0
    };
    const double gbz[6] = {
        2.0, -1.0,
        0.0, 1.0,
        3.0, 2.0
    };
    double psi[2];
    double br[2];
    double bz[2];
    GreenProjectionStatus status = green_matrix_current_projection(
        currents, 3, gpsi, gbr, gbz, 2, psi, br, bz
    );

    return expect_status("vector fixture", status, GREEN_PROJECTION_OK) &&
           expect_close("psi[0]", psi[0], -2.0) &&
           expect_close("psi[1]", psi[1], 0.5) &&
           expect_close("br[0]", br[0], 0.75) &&
           expect_close("br[1]", br[1], -0.5) &&
           expect_close("bz[0]", bz[0], 5.5) &&
           expect_close("bz[1]", bz[1], -2.0);
}

/* 验证：单个电流源时，C profile 的一行矩阵等价于源码 rank=1 的标量乘法路径。 */
static int test_single_current_matches_scalar_projection(void)
{
    const double currents[1] = {2.5};
    const double gpsi[2] = {4.0, -2.0};
    const double gbr[2] = {0.25, 1.5};
    const double gbz[2] = {-1.0, 3.0};
    double psi[2];
    double br[2];
    double bz[2];
    GreenProjectionStatus status = green_matrix_current_projection(
        currents, 1, gpsi, gbr, gbz, 2, psi, br, bz
    );

    return expect_status("single current", status, GREEN_PROJECTION_OK) &&
           expect_close("single psi[0]", psi[0], 10.0) &&
           expect_close("single psi[1]", psi[1], -5.0) &&
           expect_close("single br[0]", br[0], 0.625) &&
           expect_close("single br[1]", br[1], 3.75) &&
           expect_close("single bz[0]", bz[0], -2.5) &&
           expect_close("single bz[1]", bz[1], 7.5);
}

/* 验证：没有电流源或没有评价点时拒绝输入，避免静默产生空输出。 */
static int test_invalid_size_rejected(void)
{
    const double value[1] = {1.0};
    double output[1] = {0.0};
    GreenProjectionStatus status = green_matrix_current_projection(
        value, 0, value, value, value, 1, output, output, output
    );

    return expect_status("invalid size", status, GREEN_PROJECTION_INVALID_SIZE);
}

/* 验证：非有限输入会被显式拒绝，避免 NaN/Inf 污染后续场量叠加。 */
static int test_nonfinite_rejected(void)
{
    const double currents[1] = {NAN};
    const double matrix[1] = {1.0};
    double output[1] = {0.0};
    GreenProjectionStatus status = green_matrix_current_projection(
        currents, 1, matrix, matrix, matrix, 1, output, output, output
    );

    return expect_status("nonfinite input", status, GREEN_PROJECTION_NONFINITE_INPUT);
}

int main(void)
{
    int passed = 0;
    int total = 0;

    ++total;
    passed += test_vector_projection_fixture();

    ++total;
    passed += test_single_current_matches_scalar_projection();

    ++total;
    passed += test_invalid_size_rejected();

    ++total;
    passed += test_nonfinite_rejected();

    if (passed == total) {
        printf("%d passed\n", passed);
        return 0;
    }

    printf("%d/%d passed\n", passed, total);
    return 1;
}
