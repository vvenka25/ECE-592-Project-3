CC := gcc
SGX_SDK ?= /opt/intel/sgxsdk
CFLAGS := -O2 -Wall -Wextra -Werror -I. -Ibuild
SDKINC := -I$(SGX_SDK)/include
TRUST := -DTRUSTED $(CFLAGS) $(SDKINC) -I$(SGX_SDK)/include/tlibc -nostdinc -fvisibility=hidden -fpie -fstack-protector
INPUTS := $(wildcard *.c *.h *.edl *.xml *.lds) gen_kernels.py build_id.py Makefile
.PHONY: all native enclave check
all: native
native: build/trackb-native build/platform-info
build:
	mkdir -p $@
build/generated: gen_kernels.py | build
	python3 $< build
	touch $@
build/kernels.o: build/generated
	$(CC) -c build/kernels.S -o $@
build/build_id.h: $(INPUTS) | build
	python3 build_id.py $@ $(INPUTS)
build/trackb-native: main.c engine.c pmu.c bench.h pmu.h build/generated build/kernels.o build/build_id.h Makefile
	$(CC) $(CFLAGS) main.c engine.c pmu.c build/dispatch.c build/kernels.o -o $@
build/platform-info: ../src/platform.c Makefile | build
	$(CC) $(CFLAGS) $< -o $@
build/edges: enclave.edl | build
	$(SGX_SDK)/bin/x64/sgx_edger8r --trusted $< --trusted-dir build --search-path $(SGX_SDK)/include
	$(SGX_SDK)/bin/x64/sgx_edger8r --untrusted $< --untrusted-dir build --search-path $(SGX_SDK)/include
	touch $@
build/engine_t.o: engine.c bench.h Makefile | build
	$(CC) $(TRUST) -c $< -o $@
build/entry_t.o: entry.c bench.h build/edges Makefile
	$(CC) $(TRUST) -c $< -o $@
build/enclave_t.o: build/edges Makefile
	$(CC) $(TRUST) -c build/enclave_t.c -o $@
build/dispatch_t.o: build/generated bench.h Makefile
	$(CC) $(TRUST) -c build/dispatch.c -o $@
build/suite.so: build/engine_t.o build/entry_t.o build/enclave_t.o build/dispatch_t.o build/kernels.o Enclave.lds Makefile
	$(CC) build/engine_t.o build/entry_t.o build/enclave_t.o build/dispatch_t.o build/kernels.o -o $@ -nostdlib -nodefaultlibs -nostartfiles -L$(SGX_SDK)/lib64 -Wl,--no-undefined -Wl,--whole-archive -lsgx_trts -Wl,--no-whole-archive -Wl,--start-group -lsgx_tstdc -lsgx_tcrypto -lsgx_tservice -Wl,--end-group -Wl,-Bstatic -Wl,-Bsymbolic -Wl,-pie,-eenclave_entry -Wl,--export-dynamic -Wl,--defsym,__ImageBase=0 -Wl,--version-script=Enclave.lds
build/debug-key.pem: | build
	openssl genrsa -3 -out $@ 3072
build/suite.signed.so: build/suite.so build/debug-key.pem Enclave.config.xml
	$(SGX_SDK)/bin/x64/sgx_sign sign -key build/debug-key.pem -enclave build/suite.so -out $@ -config Enclave.config.xml
build/trackb-enclave: main.c pmu.c bench.h pmu.h build/build_id.h build/edges build/suite.signed.so build/generated build/kernels.o Makefile
	$(CC) $(CFLAGS) $(SDKINC) -DENCLAVE main.c pmu.c build/dispatch.c build/kernels.o build/enclave_u.c -L$(SGX_SDK)/lib64 -lsgx_urts -o $@
enclave: build/trackb-enclave
ifeq ($(TEST_SGX),1)
check: enclave
endif
check: native
	cd .. && python3 trackb/check.py
