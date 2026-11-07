# Native prototype pilot — validation only

This campaign was collected during implementation, before the Q2 block-boundary correction. Its source snapshot and copied binary identify the exact prototype. Do not pool it with later build identities or treat it as a completed two-machine experiment.

Q3's shuffled branch patterns produce substantially more native branch-miss events than alternating/constant controls, while the branchless shuffled/alternating controls are close. Q1 shows approximately three core cycles/IMUL on one dependency chain and one on four chains at fixed multiply count. These are pilot observations, not final exercise comparisons.

**Q2 diagnostic failure:** independent and nominally serialized cold K=64 throughput were almost equal. A serialized chain could overlap the *next* iteration's pointer load, hiding the intended within-block contrast. The final generator adds a common end-of-block LFENCE to all three variants, with an extra pre-work fence only in the fenced control. See `results/trackb-q2-block-pilot` for the corrected validation. This prototype's Q2 data must not be used as positive evidence of the final OOO experiment.

Q5's one-chain slowdown near the upper pilot range disagrees with its four-chain/NOP controls. It is a dependency/execution diagnostic, **not a measured PRF boundary**. The pilot does not establish PRF size; use the complete coarse/fine resource controls and qualified attribution before reporting a speculative integer-GPR allocation budget or total capacity.

This early Q5 prototype used one-byte NOPs. The final implementation uses one four-byte NOP per filler, matching LEA byte length as well as instruction count; keep the configurations/build identities separate.

Q8's native pilot counters show approximately one STLB service per scattered access, very few completed walks, and low L1 data-miss rates in both compact and scattered cases. This supports the intended miss-class/cache-control design. The short pilot is not the final repeated miss-cost estimate and enclave counter coverage remains unvalidated.
