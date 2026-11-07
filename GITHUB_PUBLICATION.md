# GitHub publication

Target: https://github.com/vvenka25/ECE-592-Project-3

The publication is prepared in `/tmp/hw3-github-publication-9ikgh9m7`, separately
from the original project and submission artifacts. It includes all relevant
source/build/generation/collection/analysis scripts, project Markdown, AI-use
log, checklists, PDF/LaTeX report, figures, and existing activity/validation logs.
The raw-data archive restores 5,330 repeated-observation/configuration/audit/
historical-source files under their original paths after per-file hash checks.

The original full Q4 archive and final ZIP are unchanged locally. The public
tree uses a separately named source-only Q4 derivative, excludes all generated
ELF copies and private signing keys, and verifies 805 immutable non-build Q4
files. Original experimental source, observations and plots are unchanged.

Clean data restoration, idempotence, overwrite refusal, native build/functional/
assembly/placement tests, all six comparison regenerations, report compilation
and source-only submission packaging pass. See `results/github-publication/`.

The connector's initial write attempt returned HTTP 403, "Resource not
accessible by integration." GitHub CLI authentication on Artemisia is required
for the Git push; no repository file was created by that rejected attempt.
Run `gh auth login --hostname github.com --git-protocol https --web` on
Artemisia, then let Codex continue the upload. Credentials belong in the CLI's
authentication flow and should not be pasted into the chat or project files.
