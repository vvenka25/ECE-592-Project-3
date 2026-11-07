#!/usr/bin/env bash
set -eu
uname -a
lscpu
lscpu -e=CPU,CORE,SOCKET,NODE,ONLINE
getconf PAGESIZE
cat /sys/kernel/mm/transparent_hugepage/enabled
gcc --version
printf '\nCPU affinity and memory policy\n'
grep -E 'Cpus_allowed_list|Mems_allowed_list' /proc/self/status
for path in /sys/devices/system/cpu/cpu*/topology/thread_siblings_list; do
    printf '%s: ' "$path"
    cat "$path"
done
if command -v numactl >/dev/null; then numactl --show; fi
printf '\nSource and binary hashes\n'
find src enclave scripts tests -type f ! -name '*.pyc' -print0 | sort -z | xargs -0 sha256sum
sha256sum Makefile build/rob-native
if test -f build/rob-enclave; then
    sha256sum build/rob-enclave build/rob.signed.so
    ldd build/rob-enclave
fi
printf '\nSGX package metadata (if packaged)\n'
if command -v rpm >/dev/null; then rpm -qa | sort | sed -n '/sgx/Ip'; fi
if command -v dpkg-query >/dev/null; then dpkg-query -W '*sgx*' 2>/dev/null || true; fi
