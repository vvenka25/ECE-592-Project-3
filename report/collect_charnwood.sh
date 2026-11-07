#!/usr/bin/env bash
set -euo pipefail

# Run from a host-local source extraction, with a currently permitted CPU.
# The collector records topology and chooses that CPU's local NUMA node.
if [[ $# != 2 ]]; then
    printf 'Usage: bash report/collect_charnwood.sh CPU FRESH_OUTPUT_DIRECTORY\n' >&2
    exit 2
fi
case "$(hostname -f)" in
    charnwood|charnwood.*) ;;
    *) printf 'This helper is for Charnwood; refusing to mislabel another host.\n' >&2; exit 2 ;;
esac
task_root=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
cd "$task_root"
task_cpu=$1
task_output=$2
if [[ -e "$task_output" ]]; then
    printf 'Choose a fresh output directory; existing evidence is preserved.\n' >&2
    exit 2
fi
python3 scripts/preflight.py "$task_cpu"
make -C trackb native
TEST_CPU="$task_cpu" make -C trackb check
for task_question in Q3 Q1 Q2 Q5 Q8; do
    task_extra=()
    if [[ "$task_question" == Q5 ]]; then task_extra=(--iterations 10000); fi
    python3 trackb/run.py --question "$task_question" --cpu "$task_cpu" \
        --core-scheduling private --environment native \
        --out "$task_output/$task_question" "${task_extra[@]}" --execute
    python3 trackb/review.py "$task_output/$task_question"
    if [[ "$task_question" == Q5 ]]; then
        # Reproduce the recorded interval; override after inspecting your own
        # coarse result if the measured transition changes.
        python3 trackb/run.py --question Q5 --stage fine \
            --lo "${TRACKB_Q5_LO:-120}" --hi "${TRACKB_Q5_HI:-160}" \
            --iterations 10000 --cpu "$task_cpu" --core-scheduling private \
            --environment native --out "$task_output/Q5-fine" --execute
        python3 trackb/review.py "$task_output/Q5-fine"
    fi
done
printf 'Collections finished. Interpret Q5 only after checking its coarse/fine controls.\n'
printf 'Return the complete output directory, including manifests, raw CSVs and snapshots.\n'
