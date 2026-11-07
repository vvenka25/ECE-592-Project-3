# Three-counter diagnostic; final cost uses simultaneous core cycles

This initial campaign supports the intended native miss/cache treatment, but
its compact 256-node repetition-2 TSC median shifts from about 3.70 to 6.85
ticks/load while translation/cache event rates remain comparable. Therefore
the original event/cache gate alone did not establish clock comparability
for the subtracted TSC cost. No sample is removed or relabeled.

The final `q8-clock-charnwood-private` campaign adds simultaneous active core
cycles. It estimates about 9.00 additional core cycles per added STLB service;
TSC estimates are emitted only when the declared clock/preemption proxy also
passes. Earlier analysis scripts and results are preserved as the actual
history, rather than presented as final clock-controlled estimates.
