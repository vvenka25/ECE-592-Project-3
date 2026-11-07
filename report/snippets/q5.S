.Lloop_tb_q5_lea8_d0_208:
mov (%rdi),%rdi
lea (%r8,%r8,2),%r8
lea (%r9,%r9,2),%r9
# Rotate over all eight accumulators: 208 LEAs/gap.
mov (%rsi),%rsi
# 208 further scaled-index LEAs; repeated text omitted.
dec %rdx
jnz .Lloop_tb_q5_lea8_d0_208
