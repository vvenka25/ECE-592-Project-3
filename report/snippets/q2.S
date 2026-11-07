.Lloop_tb_q2_overlap_64:
mov (%r8),%r8
imul $3,%r8,%rax
xor %r11,%r9
imul $3,%r9,%r9
# 63 further younger IMULs are omitted here.
xor %rax,%r10
lfence
dec %rsi
jnz .Lloop_tb_q2_overlap_64
