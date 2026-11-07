# Constant-offset LEA diagnostic; not an isolated PRF capacity

This complete 16-job campaign retains 7,920 raw measurements of the first
Q5 treatment, `lea 1(reg),reg`. Its source snapshot and copied binaries define
that treatment. It must not be pooled with the later scaled-index LEA build.

One- and four-chain curves follow the NOP window. For example, native
repetition 2 at N=448 reports about 468.64 user core cycles/iteration for the
one-chain variant, despite executing 896 constant-offset LEAs per iteration.
The final checksum is consistent with all architectural updates. Thus the
ordinary one-cycle execution-dependency/allocation assumption is not supported
for this instruction form; the exact optimization is not established here.

The observed shared upper-range transition does not isolate PRF exhaustion.
It is not evidence for a PRF size of 496, 512, twice N, or the published ROB
capacity. The revised treatment computes 3*x using scaled-index
`lea (reg,reg,2),reg`, avoiding a pure constant-offset update. Its semantics,
dependency cost and allocation controls require separate validation.
