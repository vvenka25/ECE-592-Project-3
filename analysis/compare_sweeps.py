#!/usr/bin/env python3
"""Compare two matched nonzero ROB sweeps without pooling their samples."""
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


def load(root):
    manifest = json.loads((root / 'manifest.json').read_text())
    points = {}; raw = {}; mappings = {}; builds = set(); machines = set()
    inputs = [root / 'manifest.json', root / 'metadata.txt']
    counts = dict(samples=0, samples_with_faults=0, samples_with_context_switches=0, minor_faults=0, major_faults=0)
    for job in manifest['jobs']:
        name = job['name']; p = job['parameters']; env = job['environment']
        if job.get('status') != 'success' or p['iters'] <= 0:
            raise ValueError('Expected complete nonzero-work jobs: ' + name)
        path = root / (name + '.csv'); inputs.append(path)
        with path.open() as f: rows = list(csv.DictReader(f))
        ns = list(range(p['lo'], p['hi'] + 1, p['step']))
        if len(rows) != job['sample_count'] or len(rows) != len(ns) * 2 * p['samples']:
            raise ValueError('Incomplete sample count: ' + name)
        expected = dict(cpu_id=manifest['cpu'], footprint_bytes=p['kib'] * 1024,
                        span_bytes=p['kib'] * 1024 * (p['stride'] // 64), iterations=p['iters'],
                        node_stride=p['stride'], seed=p['seed'], order_seed=manifest['order_seed'],
                        nop_bytes=p['width'], loop_alignment=p['align'])
        for r in rows:
            if any(int(r[k]) != v for k, v in expected.items()):
                raise ValueError('Raw parameters differ from manifest: ' + name)
            if r['method'] != 'rob-v2' or r['status'] != 'ok' or r['timer_unit'] != 'tsc_ticks':
                raise ValueError('Resolve invalid or migration samples: ' + name)
            if r['environment'] != ('native' if env == 'native' else 'sgx-hw-debug'):
                raise ValueError('Environment mismatch: ' + name)
            if r['page_policy'] != (p['pages'] if env == 'native' else 'epc'):
                raise ValueError('Page-policy mismatch: ' + name)
            builds.add(r['build_id']); machines.add(r['machine_id'])
            counts['samples'] += 1
            counts['minor_faults'] += int(r['minor_faults']); counts['major_faults'] += int(r['major_faults'])
            counts['samples_with_faults'] += int(r['minor_faults']) + int(r['major_faults']) > 0
            counts['samples_with_context_switches'] += int(r['voluntary_cs']) + int(r['involuntary_cs']) > 0
        mappings[name] = mapping_audit(root, job)
        inputs += [root / (name + suffix) for suffix in ('.log', '.before.smaps', '.after.smaps',
                   '.before.numa_maps', '.after.numa_maps', '.before.status', '.after.status',
                   '.platform-before.json', '.platform-after.json')]
        for n in ns:
            for dep in (0, 1):
                rr = sorted((r for r in rows if int(r['nops_per_gap']) == n and int(r['dependent']) == dep),
                            key=lambda r: int(r['sample_id']))
                if [int(r['sample_id']) for r in rr] != list(range(p['samples'])):
                    raise ValueError('Incomplete or duplicate condition: ' + name)
                v = [int(r['elapsed_ticks']) / (2 * int(r['iterations'])) for r in rr]
                flags = [any(int(r[k]) for k in ('minor_faults', 'major_faults', 'voluntary_cs', 'involuntary_cs')) for r in rr]
                unflagged = [x for x, flag in zip(v, flags) if not flag]
                q = stats.quantiles(v, n=10, method='inclusive') if len(v) > 1 else [v[0]] * 9
                key = name, n, dep
                if key in points: raise ValueError('Duplicate job name: ' + name)
                points[key] = dict(median=stats.median(v), minimum=min(v), maximum=max(v), p10=q[0], p90=q[8],
                                   unflagged_median=stats.median(unflagged) if unflagged else '',
                                   unflagged_samples=len(unflagged))
                raw[key] = dict(values=v, flags=flags)
    if len(builds) != 1 or len(machines) != 1:
        raise ValueError('Separate different builds or machines')
    return dict(manifest=manifest, points=points, raw=raw, builds=sorted(builds), machines=sorted(machines),
                counts=counts, mappings=mappings,
                input_sha256={str(p): hashlib.sha256(p.read_bytes()).hexdigest() for p in inputs})


def compare(first, repeat, out, sample_ns):
    data = [load(first), load(repeat)]; a, b = data
    for key in ('stage', 'cpu', 'numa_node_requested', 'binary_sha256'):
        if a['manifest'][key] != b['manifest'][key]: raise ValueError('Campaign mismatch: ' + key)
    jobs = lambda m: {j['name']: (j['environment'], j['parameters']) for j in m['jobs']}
    if jobs(a['manifest']) != jobs(b['manifest']) or a['points'].keys() != b['points'].keys():
        raise ValueError('Workload parameters do not match')
    if a['builds'] != b['builds'] or a['machines'] != b['machines']:
        raise ValueError('Different builds or machines')
    job_list = sorted(a['manifest']['jobs'], key=lambda j: j['name'])
    if sample_ns and any((j['name'], n, 0) not in a['points'] for j in job_list for n in sample_ns):
        raise ValueError('Selected sample spacing absent from a job')
    output = []; steps = []
    for (name, n, dep), p in sorted(a['points'].items()):
        q = b['points'][name, n, dep]
        output.append(dict(job=name, nops_per_gap=n, dependent=dep,
                           **{'first_' + k: v for k, v in p.items()}, **{'repeat_' + k: v for k, v in q.items()},
                           median_change_percent=100 * (q['median'] / p['median'] - 1)))
    for job in job_list:
        name = job['name']; ns = sorted(n for j, n, d in a['points'] if j == name and d == 0)
        for metric in ('median', 'minimum', 'unflagged_median'):
            result = dict(job=name, environment=job['environment'], metric=metric)
            for label, campaign in zip(('first', 'repeat'), data):
                points = campaign['points']
                changes = [(points[name, hi, 0][metric] - points[name, lo, 0][metric], lo, hi)
                           for lo, hi in zip(ns, ns[1:]) if points[name, lo, 0][metric] != '' and points[name, hi, 0][metric] != '']
                if not changes: raise ValueError('No comparable adjacent points')
                delta, lo, hi = max(changes)
                result.update({label + '_n_before': lo, label + '_n_after': hi, label + '_change': delta})
            steps.append(result)
    out.mkdir(parents=True, exist_ok=True)
    write_csv(out / 'point-comparison.csv', output); write_csv(out / 'largest-step-comparison.csv', steps)
    (out / 'audit.json').write_text(json.dumps(dict(
        first={k: v for k, v in a.items() if k not in ('points', 'raw')},
        repeat={k: v for k, v in b.items() if k not in ('points', 'raw')},
        selected_sample_spacings=sample_ns,
        interpretation='Campaigns remain separate, with all samples retained. Largest steps are descriptive, not automatic capacity estimates.'), indent=2) + '\n')
    envs = [env for env in ('native', 'enclave') if any(j['environment'] == env for j in job_list)]
    context = f"{a['machines'][0]}; CPU {a['manifest']['cpu']}, requested memory node {a['manifest'].get('numa_node_requested')}"
    fig, axes = plt.subplots(len(envs), 2, figsize=(12, 4 * len(envs)), squeeze=False)
    for row, env in enumerate(envs):
        for dep in (0, 1):
            ax = axes[row, dep]
            for index, (label, campaign) in enumerate(zip(('first', 'repeat'), data)):
                for job in job_list:
                    if job['environment'] != env: continue
                    name = job['name']; pp = campaign['points']
                    ns = sorted(n for j, n, d in pp if j == name and d == dep)
                    legend = f"{label}, order seed {campaign['manifest']['order_seed']}"
                    if len(job_list) > len(envs): legend += ', ' + job['parameters']['tag']
                    ax.plot(ns, [pp[name, n, dep]['median'] for n in ns], 'o-', markersize=3, color=f'C{index}', label=legend)
                    ax.fill_between(ns, [pp[name, n, dep]['p10'] for n in ns], [pp[name, n, dep]['p90'] for n in ns], color=f'C{index}', alpha=.12)
            ax.set(title=env + (' dependent' if dep else ' independent'), xlabel='NOP instructions per gap', ylabel='Host TSC ticks per load')
            ax.grid(alpha=.25); ax.legend(fontsize=8)
    fig.suptitle(context + '\nSeparate all-sample medians and observed p10–p90; panel y-scales differ', fontsize=11)
    fig.tight_layout()
    for ext in ('png', 'pdf'): fig.savefig(out / ('curves.' + ext), dpi=180)
    plt.close(fig)
    if sample_ns:
        if len(job_list) != len(envs): raise ValueError('Raw-sample panels require one job per environment')
        fig, axes = plt.subplots(len(envs), 2, figsize=(12, 3.6 * len(envs)), sharey='row', squeeze=False)
        for row, env in enumerate(envs):
            job = next(j for j in job_list if j['environment'] == env)
            for col, (label, campaign) in enumerate(zip(('first', 'repeat'), data)):
                ax = axes[row, col]
                for index, n in enumerate(sample_ns):
                    point = campaign['raw'][job['name'], n, 0]; values = point['values']; flags = point['flags']
                    ax.plot(range(len(values)), values, 'o-', markersize=3, color=f'C{index}', label=f'N={n}')
                    flagged = [i for i, flag in enumerate(flags) if flag]
                    ax.scatter(flagged, [values[i] for i in flagged], color=f'C{index}', marker='x', s=55, zorder=4)
                ax.set(title=env + ', ' + label, xlabel='Sample ID within condition', ylabel='Host TSC ticks per independent load')
                ax.grid(alpha=.25); ax.legend(fontsize=8)
        fig.suptitle(context + '\nAll selected independent samples; × marks a recorded fault/context-switch delta; conditions collected separately', fontsize=10)
        fig.tight_layout()
        for ext in ('png', 'pdf'): fig.savefig(out / ('transition-samples.' + ext), dpi=180)
        plt.close(fig)
    for result in steps: print(result)
    print('Saved separate-campaign comparison to ' + str(out))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('first', type=Path); parser.add_argument('repeat', type=Path)
    parser.add_argument('--output', type=Path); parser.add_argument('--samples-at', nargs='+', type=int, default=[])
    args = parser.parse_args()
    compare(args.first, args.repeat, args.output or args.repeat / 'review' / 'comparison', args.samples_at)
