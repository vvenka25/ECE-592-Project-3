.Lloop_rob_independent_224_b1_a0:
mov (%rdi),%rdi
# 224 actual one-byte NOPs (0x90); repeated text omitted.
mov (%rsi),%rsi
# 224 further one-byte NOPs; repeated text omitted.
dec %rdx
jnz .Lloop_rob_independent_224_b1_a0
