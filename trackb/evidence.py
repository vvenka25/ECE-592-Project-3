"""Q4 mapping-audit helper, reused without the plotting dependency."""
import re

def mapping_audit(root,job):
    if job['environment']!='native': return {'environment':'enclave','placement':'EPC node/residency not established by these device mappings'}
    name=job['name']; log=(root/(name+'.log')).read_text()
    base=re.search(r'native data mapping: (0x[0-9a-f]+)',log)
    if not base: raise ValueError('Native mapping address missing: '+name)
    result={}
    for phase in ('before','after'):
        text=(root/(name+'.'+phase+'.smaps')).read_text()
        numa=(root/(name+'.'+phase+'.numa_maps')).read_text().splitlines()
        for block in re.split(r'(?=^[0-9a-f]+-[0-9a-f]+ )',text,flags=re.M):
            lines=block.splitlines()
            if not lines: continue
            m=re.match(r'([0-9a-f]+)-([0-9a-f]+)',lines[0])
            if m and int(m[1],16)<=int(base[1],16)<int(m[2],16):
                fields={x.split(':',1)[0]:x.split(':',1)[1].strip() for x in lines[1:] if ':' in x}
                result[phase]={'mapping':lines[0],**{x:fields.get(x) for x in ('Size','Rss','AnonHugePages','KernelPageSize','MMUPageSize','THPeligible','VmFlags')},
                               'numa_line':next((x for x in numa if x.split()[0]==m[1]),None)}
                break
        if phase not in result: raise ValueError('Native data mapping not found: '+name)
    return result
