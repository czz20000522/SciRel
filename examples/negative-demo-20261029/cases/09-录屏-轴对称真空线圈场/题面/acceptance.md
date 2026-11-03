# Acceptance

The complete input contract is in inputs.json and requirements.md.

Required checks:

- every required file exists and is readable;
- all field arrays have shape [201,76] and finite values;
- profiles are exact slices of the field arrays;
- BR is zero on the axis within the declared field tolerance;
- psi has Wb/rad units and is not silently multiplied by 2*pi;
- mirror ratio uses the entire 201-point axis and the stated denominator budget;
- summary.status is one of the declared typed states;
- when axis_center_Bmag_T <= mirror_ratio_denominator_error_budget_T, the result keeps finite field/profile outputs, sets axis_mirror_ratio to null, and uses MIRROR_RATIO_UNDEFINED_LOW_DENOMINATOR;
- run_receipt records the actual public SciRel call, runtime and cleanup.

This is a task-level execution contract. Scientific acceptance and comparison to a
separately held benchmark remain independent decisions.
