#!/usr/bin/env python3
"""Review batch controls, retaining zero-work timings in ticks per invocation."""
import argparse
import csv
import hashlib
import json
from pathlib import Path
import statistics as stats

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

from review_sweep import mapping_audit, write_csv


def review(root, out):
    manifest = json.loads((root / 'manifest.json').read_text())
    if manifest['stage'] != 'overhead':
        raise ValueError('Expected an overhead campaign')
    points = {}; raw = {}; mappings = {}; inputs = [root / 'manifest.json', root / 'metadata.txt']
    builds = set(); machines = set(); signatures = set()
    total = faulted = switched = 0
    for job in manifest['jobs']:
        name = job['name']; params = job['parameters']; env = job['environment']
        if job.get('status') != 'success':
            raise ValueError('Incomplete job: ' + name)
        if params['lo'] != 0 or params['hi'] != 0:
            raise ValueError('Expected N=0 overhead controls')
        signatures.add(tuple(params[k] for k in ('kib', 'stride', 'width', 'align', 'pages', 'seed', 'samples')))
        path = root / (name + '.csv'); inputs.append(path)
        with path.open() as f:
            rows = list(csv.DictReader(f))
        if len(rows) != job['sample_count'] or len(rows) != 2 * params['samples']:
            raise ValueError('Sample-count mismatch: ' + name)
        total += len(rows)
        expected = dict(cpu_id=manifest['cpu'], footprint_bytes=params['kib'] * 1024,
                        span_bytes=params['kib'] * 1024 * (params['stride'] // 64), node_stride=params['stride'],
                        seed=params['seed'], order_seed=manifest['order_seed'], nop_bytes=params['width'],
                        loop_alignment=params['align'], iterations=params['iters'], nops_per_gap=0)
        for r in rows:
            if any(int(r[k]) != v for k, v in expected.items()):
                raise ValueError('Raw parameters differ from manifest: ' + name)
            if r['method'] != 'rob-v2' or r['status'] != 'ok' or r['timer_unit'] != 'tsc_ticks':
                raise ValueError('Resolve invalid or migration samples: ' + name)
            if r['environment'] != ('native' if env == 'native' else 'sgx-hw-debug'):
                raise ValueError('Environment mismatch: ' + name)
            if r['page_policy'] != (params['pages'] if env == 'native' else 'epc'):
                raise ValueError('Page-policy mismatch: ' + name)
            builds.add(r['build_id']); machines.add(r['machine_id'])
            faulted += int(r['minor_faults']) + int(r['major_faults']) > 0
            switched += int(r['voluntary_cs']) + int(r['involuntary_cs']) > 0
        mappings[name] = mapping_audit(root, job)
        for suffix in ('.log', '.platform-before.json', '.platform-after.json',
                       '.before.smaps', '.after.smaps', '.before.numa_maps', '.after.numa_maps',
                       '.before.status', '.after.status'):
            inputs.append(root / (name + suffix))
        for dep in (0, 1):
            rr = sorted((r for r in rows if int(r['dependent']) == dep), key=lambda r: int(r['sample_id']))
            if [int(r['sample_id']) for r in rr] != list(range(params['samples'])):
                raise ValueError('Incomplete or duplicate condition: ' + name)
            key = env, dep, params['iters']
            if key in points:
                raise ValueError('Keep repeat jobs separate: ' + name)
            values = [int(r['elapsed_ticks']) for r in rr]
            if any(v <= 0 for v in values):
                raise ValueError('Nonpositive elapsed time: ' + name)
            q = stats.quantiles(values, n=10, method='inclusive') if len(values) > 1 else [values[0]] * 9
            third = max(1, len(values) // 3)
            early, late = stats.median(values[:third]), stats.median(values[-third:])
            points[key] = dict(job=name, environment=env, dependent=dep, iterations=params['iters'],
                               samples=len(values), median_total_ticks=stats.median(values),
                               minimum_total_ticks=min(values), p10_total_ticks=q[0], p90_total_ticks=q[8],
                               maximum_total_ticks=max(values), early_median_total_ticks=early,
                               late_median_total_ticks=late, late_vs_early_percent=100 * (late / early - 1),
                               median_ticks_per_load=stats.median(values) / (2 * params['iters']) if params['iters'] else '')
            raw[key] = values
    if len(builds) != 1 or len(machines) != 1 or len(signatures) != 1:
        raise ValueError('Separate different builds, machines or workload settings')
    envs = [env for env in ('native', 'enclave') if any(k[0] == env for k in points)]
    slopes = []
    for env in envs:
        for dep in (0, 1):
            if (env, dep, 0) not in points:
                raise ValueError('Missing zero-work control')
            zero = points[env, dep, 0]['median_total_ticks']
            iterations = sorted(k[2] for k in points if k[:2] == (env, dep) and k[2] > 0)
            if len(iterations) < 2:
                raise ValueError('Need at least two nonzero batches')
            for (e, d, n), p in points.items():
                if (e, d) != (env, dep): continue
                p.update(zero_work_median_total_ticks=zero,
                         zero_work_scale_ticks_per_load=zero / (2 * n) if n else '',
                         zero_work_scale_percent_of_median=100 * zero / p['median_total_ticks'] if n else '',
                         diagnostic_zero_subtracted_ticks_per_load=(p['median_total_ticks'] - zero) / (2 * n) if n else '')
            lo, hi = iterations[-2:]
            a, b = points[env, dep, lo], points[env, dep, hi]
            slopes.append(dict(environment=env, dependent=dep, iterations_before=lo, iterations_after=hi,
                               median_total_ticks_before=a['median_total_ticks'], median_total_ticks_after=b['median_total_ticks'],
                               incremental_ticks_per_load=(b['median_total_ticks'] - a['median_total_ticks']) / (2 * (hi - lo))))
    out.mkdir(parents=True, exist_ok=True)
    write_csv(out / 'summary.csv', [points[k] for k in sorted(points)])
    write_csv(out / 'long-batch-slopes.csv', slopes)
    audit = dict(stage='overhead', samples=total, migration_samples=0, samples_with_faults=faulted,
                 samples_with_context_switches=switched, build_ids=sorted(builds),
                 sibling_state_claim=manifest['sibling_state_claim'],
                 sibling_cpu_ticks={j['name']: j['sibling_cpu_ticks'] for j in manifest['jobs']},
                 mapping_audit=mappings,
                 input_sha256={str(p): hashlib.sha256(p.read_bytes()).hexdigest() for p in inputs},
                 summary_rule='All samples retained. Zero work is reported per invocation, never per load.',
                 interpretation='Zero subtraction and long-batch slopes are diagnostics; no correction is applied to primary measurements.')
    (out / 'audit.json').write_text(json.dumps(audit, indent=2) + '\n')
    context = f"{next(iter(machines))}; N=0, {manifest['jobs'][0]['parameters']['kib']} KiB; CPU {manifest['cpu']}, requested memory node {manifest.get('numa_node_requested')}"
    fig, axes = plt.subplots(len(envs), 2, figsize=(11, 3.8 * len(envs)), squeeze=False)
    for row, env in enumerate(envs):
        for dep in (0, 1):
            pp = [points[k] for k in sorted(points) if k[:2] == (env, dep)]
            for col in (0, 1):
                selected = [p for p in pp if col == 0 or p['iterations'] > 0]
                x = [p['iterations'] for p in selected]
                scale = [1 if col == 0 else 2 * p['iterations'] for p in selected]
                ax = axes[row, col]; color = f'C{dep}'
                ax.plot(x, [p['median_total_ticks'] / s for p, s in zip(selected, scale)], 'o-', color=color,
                        label='dependent' if dep else 'independent')
                ax.fill_between(x, [p['p10_total_ticks'] / s for p, s in zip(selected, scale)],
                                [p['p90_total_ticks'] / s for p, s in zip(selected, scale)], color=color, alpha=.15)
        for col in (0, 1):
            ax = axes[row, col]
            ax.set_xscale('symlog', linthresh=1000) if col == 0 else ax.set_xscale('log')
            if col == 0: ax.set_yscale('log')
            ax.set(title=env + (' total timing, including zero work' if col == 0 else ' per-load timing, nonzero work'),
                   xlabel='Iterations per invocation', ylabel='Host TSC ticks per invocation' if col == 0 else 'Host TSC ticks per load')
            ax.grid(alpha=.25); ax.legend(fontsize=8)
    fig.suptitle(context + '\nAll-sample medians and observed p10–p90; no overhead subtraction; panel y-scales differ', fontsize=10)
    fig.tight_layout()
    for ext in ('png', 'pdf'): fig.savefig(out / ('batch-timing.' + ext), dpi=180)
    plt.close(fig)
    fig, axes = plt.subplots(1, len(envs), figsize=(5.5 * len(envs), 3.8), squeeze=False)
    for ax, env in zip(axes[0], envs):
        for dep in (0, 1):
            values = raw[env, dep, 0]
            ax.plot(range(len(values)), values, 'o-', markersize=3, label='dependent dispatch' if dep else 'independent dispatch')
        ax.set(title=env, xlabel='Sample ID within condition', ylabel='Host TSC ticks per zero-work invocation')
        ax.grid(alpha=.25); ax.legend(fontsize=8)
    fig.suptitle(context + '\nZero-work observations: no timed pointer loads; panel y-scales differ', fontsize=10)
    fig.tight_layout()
    for ext in ('png', 'pdf'): fig.savefig(out / ('zero-work-samples.' + ext), dpi=180)
    plt.close(fig)
    print(f'{total} samples retained; 0 migration; {faulted} with faults; {switched} with context-switch deltas')
    for key in sorted(points):
        p = points[key]
        print(f"{p['environment']} dep={p['dependent']} iterations={p['iterations']}: median {p['median_total_ticks']:.0f} ticks/invocation; ticks/load={p['median_ticks_per_load']}")
    print('Saved review artifacts to ' + str(out))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('directory', type=Path); parser.add_argument('--output', type=Path)
    args = parser.parse_args()
    review(args.directory, args.output or args.directory / 'review')
