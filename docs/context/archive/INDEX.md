# Archive Index

Lightweight retrieval index for archived work logs. Updated during `/ship` archival.
Agent reads this file at bootstrap to find relevant past context without scanning all archives.

> **Rule**: Read this index (~few lines per entry). Only open an archived log if its module/pattern matches your current task.

## By Module

<!-- Format: - <file-or-module>: [<archived-log>] <key-decision-or-lesson> -->
- validate.sh: [codex-template-import-cleanup-namespacing-2026-03-07.md] text integrity checks validated against real repo bytes
- deploy_brain.*: [codex-template-import-cleanup-namespacing-2026-03-06.md] wrapper files delegate to agentcortex/bin/
- AGENTS.md: [codex-master-2026-03-06.md] namespace reorganization preserves fixed anchors
- agentcortex/: [codex-template-import-cleanup-namespacing-2026-03-06.md] canonical namespace for framework assets

## By Pattern

<!-- Format: - [<pattern-tag>]: <archived-log>(s) -->
- [namespace-migration]: codex-template-import-cleanup-namespacing-2026-03-06.md
- [text-integrity]: codex-template-import-cleanup-namespacing-2026-03-07.md
- [windows-compat]: codex-template-import-cleanup-namespacing-2026-03-07.md
- [worklog-normalization]: codex-template-import-cleanup-namespacing-2026-03-06.md
- [cross-platform-validation]: codex-template-import-cleanup-namespacing-2026-03-07.md

## By Decision

<!-- Format: - D: "<decision summary>" → <archived-log> -->
- D: "Use grep over rg for portability in validation gates" → codex-template-import-cleanup-namespacing-2026-03-07.md
- D: "Work Log key = filesystem-safe normalization of branch name" → codex-template-import-cleanup-namespacing-2026-03-06.md
- D: "Fixed anchors (AGENTS.md, .agent/, docs/) stay at repo root" → codex-template-import-cleanup-namespacing-2026-03-06.md
- D: "New integrity checks must validate against real repo bytes before baselining" → codex-template-import-cleanup-namespacing-2026-03-07.md
