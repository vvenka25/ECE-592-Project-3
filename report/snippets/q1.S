.Lloop_tb_q1_4:
imul $3,%r8,%r8
imul $3,%r9,%r9
imul $3,%r10,%r10
imul $3,%r11,%r11
# The four-instruction group repeats eight times (32 IMULs).
dec %rsi
jnz .Lloop_tb_q1_4
