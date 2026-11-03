# Vacuum field to equilibrium or material support

When connecting `psi_vac` to equilibrium or material support, matching names, shapes and `Wb/rad` units are only port checks. Verify the same flux definition, reference and boundary conditions, closure and additional physical inputs in the contracts on both sides. A vacuum field alone does not supply a separatrix, density support, plasma response or heating.

If the documents do not establish the connection, retain the bounded vacuum result. Any additional physical model needs explicit justification, inputs and checks as a [supplementary calculation](glue-gap.md); unresolved user-owned choices remain open. Do not guess a `2*pi` factor or silently insert missing physics. Reassess the connection when the selected public inputs change.
