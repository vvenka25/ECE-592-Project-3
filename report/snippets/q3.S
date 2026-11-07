.Lloop_tb_q3_branch:
movzbl (%r10,%rax),%edx
test %edx,%edx
jz .Lzero_tb_q3_branch
add $1,%r8
jmp .Ljoin_tb_q3_branch
.Lzero_tb_q3_branch:
add $1,%r9
jmp .Ljoin_tb_q3_branch
.Ljoin_tb_q3_branch:
