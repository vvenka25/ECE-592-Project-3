/* From trackb/engine.c, node(i): */
if(cfg.question==8 && cfg.mode==1) return arena+i*4096+(i%64)*64;
return arena+i*64;
