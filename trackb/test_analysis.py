"""Synthetic formula/qualification checks; these are not measured results."""
from copy import deepcopy
from review import contrasts
from run import placement_ok

base=dict(campaign='synthetic-unit-fixture',question=8,environment='native',repetition=1,build_id='fixture',
          iterations=1000,mode=0,param=256,job='compact',median=4.0,purpose='measurement',
          native_pmu_qualified=True,pmu0_per_work=0.0,pmu1_per_work=0.0,pmu2_per_work=0.0,
          core_cycles_per_work=4.0,core_cycles_per_tick=1.0,core_ratio_p10=.995,core_ratio_p90=1.005)
treatment=dict(base,mode=1,job='scattered',median=9.0,pmu0_per_work=1.0,core_cycles_per_work=9.0)
result=contrasts([base,treatment]);assert len(result)==1 and result[0]['additional_cost_per_stlb_miss']==5.0
assert result[0]['additional_core_cycles_per_stlb_miss']==5.0
# Normalize by actual additional service rate, not an assumed miss per load.
treatment['pmu0_per_work']=0.8
assert contrasts([base,treatment])[0]['additional_cost_per_stlb_miss']==6.25
assert contrasts([base,treatment])[0]['additional_core_cycles_per_stlb_miss']==6.25
drift=dict(treatment,core_cycles_per_tick=.5,core_ratio_p10=.499,core_ratio_p90=.501)
assert contrasts([base,drift])[0]['additional_cost_per_stlb_miss']==''
assert contrasts([base,drift])[0]['additional_core_cycles_per_stlb_miss']==6.25
legacy=dict(treatment,core_cycles_per_work='')
assert contrasts([base,legacy])[0]['additional_cost_per_stlb_miss']==''
for patch in (dict(native_pmu_qualified=False),dict(pmu1_per_work=.1),dict(pmu2_per_work=.1),dict(purpose='pilot validation only')):
    b,t=deepcopy(base),dict(treatment,**patch)
    assert contrasts([b,t])[0]['additional_cost_per_stlb_miss']==''
    assert contrasts([b,t])[0]['additional_core_cycles_per_stlb_miss']==''
b,t=dict(base,environment='enclave',native_pmu_qualified=False),dict(treatment,environment='enclave',native_pmu_qualified=False)
assert contrasts([b,t])[0]['additional_cost_per_stlb_miss']==''
print('Synthetic analysis checks passed: service normalization, clock-drift rejection, core-cycle cost, cache/walk gates, missing counters, enclave coverage and pilot exclusion.')

# Complete direct residency queries must establish every page independently
# of imperfect ancillary numa_maps accounting. These are synthetic fixtures.
mapping={phase:dict(Size='8 kB',Rss='8 kB',AnonHugePages='0 kB',numa_line='N0=1') for phase in ('before','after')}
query={phase:dict(queried_pages=2,nodes={'0':2},errors={}) for phase in ('before','after')}
assert placement_ok(mapping,8192,0,query)
for patch in (dict(queried_pages=1),dict(nodes={'0':1,'1':1}),dict(errors={'-2':1}),dict(nodes={'0':1})):
    bad=deepcopy(query);bad['before'].update(patch)
    assert not placement_ok(mapping,8192,0,bad)
bad=deepcopy(mapping);bad['after']['Rss']='4 kB'
assert not placement_ok(bad,8192,0,query)
print('Synthetic placement checks passed: require complete local per-page queries, no errors, full RSS and no THP.')
