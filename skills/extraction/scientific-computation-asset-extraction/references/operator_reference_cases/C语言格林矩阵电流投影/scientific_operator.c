#include "scientific_operator.h"

#include <math.h>
#include <stddef.h>

static int all_finite(const double *values, size_t count)
{
    size_t i;

    for (i = 0; i < count; ++i) {
        if (!isfinite(values[i])) {
            return 0;
        }
    }
    return 1;
}

GreenProjectionStatus green_matrix_current_projection(
    const double *currents,
    size_t n_currents,
    const double *gpsi,
    const double *gbr,
    const double *gbz,
    size_t n_points,
    double *psi,
    double *br,
    double *bz
)
{
    size_t i;
    size_t j;
    size_t matrix_count;

    if (currents == NULL || gpsi == NULL || gbr == NULL || gbz == NULL ||
        psi == NULL || br == NULL || bz == NULL) {
        return GREEN_PROJECTION_NULL_POINTER;
    }

    if (n_currents == 0 || n_points == 0 ||
        n_currents > ((size_t)-1) / n_points) {
        return GREEN_PROJECTION_INVALID_SIZE;
    }

    matrix_count = n_currents * n_points;
    if (!all_finite(currents, n_currents) ||
        !all_finite(gpsi, matrix_count) ||
        !all_finite(gbr, matrix_count) ||
        !all_finite(gbz, matrix_count)) {
        return GREEN_PROJECTION_NONFINITE_INPUT;
    }

    for (j = 0; j < n_points; ++j) {
        psi[j] = 0.0;
        br[j] = 0.0;
        bz[j] = 0.0;
    }

    /*
     * 源码摘取：rank=2 投影语义来自 pleiades/fields.py:151-153、
     * 172-173、193-194。Agent 补充：C profile 显式采用 row-major
     * 布局，矩阵元素索引为 source_index * n_points + point_index。
     */
    for (i = 0; i < n_currents; ++i) {
        const double current = currents[i];

        for (j = 0; j < n_points; ++j) {
            const size_t k = i * n_points + j;

            psi[j] += current * gpsi[k];
            br[j] += current * gbr[k];
            bz[j] += current * gbz[k];
        }
    }

    if (!all_finite(psi, n_points) ||
        !all_finite(br, n_points) ||
        !all_finite(bz, n_points)) {
        return GREEN_PROJECTION_NONFINITE_INPUT;
    }

    return GREEN_PROJECTION_OK;
}
