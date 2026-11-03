# Clarify choices that change the science

Read this when the supplied request supports competing physical interpretations.

Restate the intended result in the user's vocabulary, using facts already supplied. Ask only when an unresolved choice changes the calculation or acceptance: units/time alignment/calibration; sign or coordinate conventions; model/closure/boundary; reference case or criterion. Resolve contract facts by reading the contract first.

Ask one to three related questions at a time, starting with the largest effect. Explain the physical alternatives and which result changes. A defensible default is useful for a reversible display choice; it must not silently choose a model, missing unit or acceptance rule. Do not ask the user to choose functions, asset IDs, code layout or a graph.

If the user cannot supply a fact, preserve it as unknown. Compute explicit conditional branches when they can be bounded; otherwise state the missing input and the bounded result still possible. Changing a conclusion-relevant assumption requires rerunning its affected calculations.

Example: “balance analysis” could mean reconstructing equilibrium from measurements or estimating zero-dimensional performance. Those have different inputs and claims. Settle that distinction before querying for the nearest named function. The [FRC example](example-frc-flame.md) illustrates it without claiming a real result.
