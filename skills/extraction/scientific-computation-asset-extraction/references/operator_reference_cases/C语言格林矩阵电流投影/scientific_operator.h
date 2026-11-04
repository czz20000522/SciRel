#ifndef SCIENTIFIC_OPERATOR_H
#define SCIENTIFIC_OPERATOR_H

#include <stddef.h>

typedef enum {
    GREEN_PROJECTION_OK = 0,
    GREEN_PROJECTION_NULL_POINTER = 1,
    GREEN_PROJECTION_INVALID_SIZE = 2,
    GREEN_PROJECTION_NONFINITE_INPUT = 3
} GreenProjectionStatus;

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
);

#endif
