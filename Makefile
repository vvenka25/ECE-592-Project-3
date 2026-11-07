CC := gcc
SGX_SDK ?= /opt/intel/sgxsdk
CFLAGS := -O2 -Wall -Wextra -Werror -Isrc -Ibuild
SDKINC := -I$(SGX_SDK)/include
TRUST := -DTRUSTED $(CFLAGS) $(SDKINC) -I$(SGX_SDK)/include/tlibc -nostdinc -fvisibility=hidden -fpie -fstack-protector
.PHONY: all native enclave clean check
all: native
native: build/rob-native build/platform-info
build:
	mkdir -p build
build/generated: scripts/gen_kernels.py | build
	python3 $< build
	touch $@
build/kernels.o: build/generated
	$(CC) -c build/kernels.S -o $@
BUILD_INPUTS := $(wildcard src/* enclave/* scripts/*.py scripts/*.sh) Makefile
build/build_id.h: $(BUILD_INPUTS) | build
	python3 scripts/build_id.py $@ $(BUILD_INPUTS)
build/rob-native: src/main.c src/common.c src/common.h Makefile build/build_id.h build/generated build/kernels.o
	$(CC) $(CFLAGS) src/main.c src/common.c build/dispatch.c build/kernels.o -o $@
build/edges: enclave/Rob.edl | build
	$(SGX_SDK)/bin/x64/sgx_edger8r --trusted $< --trusted-dir build --search-path $(SGX_SDK)/include
	$(SGX_SDK)/bin/x64/sgx_edger8r --untrusted $< --untrusted-dir build --search-path $(SGX_SDK)/include
	touch $@
build/platform-info: src/platform.c Makefile | build
	$(CC) $(CFLAGS) $< -o $@
build/trusted.o: src/common.c src/common.h | build
	$(CC) $(TRUST) -c $< -o $@
build/entry.o: enclave/entry.c src/common.h build/edges
	$(CC) $(TRUST) -c $< -o $@
build/Rob_t.o: build/edges
	$(CC) $(TRUST) -c build/Rob_t.c -o $@
build/dispatch_t.o: src/common.h build/generated
	$(CC) $(TRUST) -c build/dispatch.c -o $@
build/trusted.o build/entry.o build/Rob_t.o build/dispatch_t.o: Makefile
build/rob.so: build/trusted.o build/entry.o build/Rob_t.o build/dispatch_t.o build/kernels.o enclave/Rob.lds
	$(CC) build/trusted.o build/entry.o build/Rob_t.o build/dispatch_t.o build/kernels.o -o $@ -nostdlib -nodefaultlibs -nostartfiles -L$(SGX_SDK)/lib64 -Wl,--no-undefined -Wl,--whole-archive -lsgx_trts -Wl,--no-whole-archive -Wl,--start-group -lsgx_tstdc -lsgx_tcrypto -lsgx_tservice -Wl,--end-group -Wl,-Bstatic -Wl,-Bsymbolic -Wl,-pie,-eenclave_entry -Wl,--export-dynamic -Wl,--defsym,__ImageBase=0 -Wl,--version-script=enclave/Rob.lds
build/debug-key.pem: | build
	openssl genrsa -3 -out $@ 3072
build/rob.signed.so: build/rob.so build/debug-key.pem enclave/Rob.config.xml
	$(SGX_SDK)/bin/x64/sgx_sign sign -key build/debug-key.pem -enclave build/rob.so -out $@ -config enclave/Rob.config.xml
# SDK lib64 supplies link-time stubs; hardware execution must load the PSW
# runtime from the system loader paths, as Intel's SampleEnclave does.
build/rob-enclave: src/main.c src/common.h Makefile build/build_id.h build/edges build/rob.signed.so
	$(CC) $(CFLAGS) $(SDKINC) -DENCLAVE src/main.c build/Rob_u.c -L$(SGX_SDK)/lib64 -lsgx_urts -o $@
enclave: build/rob-enclave
ifeq ($(TEST_SGX),1)
check: enclave
endif
check: native
	python3 tests/check.py
clean:
	rm -rf build
