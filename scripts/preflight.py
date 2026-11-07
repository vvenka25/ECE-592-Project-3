#!/usr/bin/env python3
"""Read-only platform record; does not reserve cores or change host settings."""
import argparse
import json
import os
from pathlib import Path
import subprocess
p=argparse.ArgumentParser(); p.add_argument('cpu',type=int); a=p.parse_args()
if a.cpu not in os.sched_getaffinity(0): p.error('CPU is not permitted by this process affinity mask')
base=Path(f'/sys/devices/system/cpu/cpu{a.cpu}')
def read(path):
    try: return Path(path).read_text().strip()
    except OSError as e: return f'unavailable: {e}'
node_paths=list(base.glob('node[0-9]*'))
result={'cpu':a.cpu,'allowed_cpus':sorted(os.sched_getaffinity(0)),
        'node':int(node_paths[0].name[4:]) if node_paths else None,
        'siblings':read(base/'topology/thread_siblings_list'),
        'sibling_control':'uncontrolled unless separately reserved; affinity alone is insufficient',
        'thp_policy':read('/sys/kernel/mm/transparent_hugepage/enabled'),
        'thp_pmd_size_bytes':read('/sys/kernel/mm/transparent_hugepage/hpage_pmd_size'),
        'perf_event_paranoid':read('/proc/sys/kernel/perf_event_paranoid'),
        'sgx_devices':{str(x):os.access(x,os.R_OK|os.W_OK) for x in (Path('/dev/sgx_enclave'),Path('/dev/sgx/enclave'))},
        'frequency':{name:read(base/'cpufreq'/name) for name in ('scaling_governor','scaling_cur_freq','cpuinfo_max_freq')},
        'cpu_stat':'\n'.join(x for x in read('/proc/stat').splitlines() if x.startswith('cpu')),
        'cache_instances':[{x.name:read(x) for x in entry.iterdir() if x.is_file() and x.name in ('level','type','size','shared_cpu_list','coherency_line_size')} for entry in (base/'cache').glob('index*')]}
if Path('build/platform-info').exists():
    proc=subprocess.run(['build/platform-info',str(a.cpu)],capture_output=True,text=True)
    result['cpuid']=proc.stdout+proc.stderr
print(json.dumps(result,indent=2))
