# Skills Fix Plan

## What Is Broken and Why

### Problem 1: `metadata.*` frontmatter fields are not Claude Code fields

The current `agent-skills/SKILL.md` has:

```yaml
metadata:
  resources:
    - references/architecture.md
    - ...
  tags:
    - agentflow
  priority: 10
```

Claude Code does not recognise `metadata.resources`, `metadata.tags`, or `metadata.priority`.
They are silently ignored. Claude never auto-loads the reference files.
That is why Claude falls back to reading Python source files instead of the pre-written docs.

Claude Code supported frontmatter keys: `name`, `description`, `when_to_use`,
`user-invocable`, `disable-model-invocation`, `allowed-tools`, `argument-hint`,
`arguments`, `model`, `effort`, `context`, `agent`, `paths`, `shell`, `hooks`.

### Problem 2: Reference paths in the skill body are ambiguous

The body currently says:

```
Read the matching reference file: `references/architecture.md`
```

Claude reads files relative to the project root, not relative to the SKILL.md file.
After install the correct path is `.claude/skills/agentflow/references/architecture.md`.
The path `references/architecture.md` resolves nowhere, so Claude skips it.

### Problem 3: Same SKILL.md is used for two different install locations

`skills.py` installs `agent-skills/` to two different places:
- Claude  → `.claude/skills/agentflow/`
- Codex   → `.agents/skills/agentflow/`

A single SKILL.md body cannot have the correct absolute path for both at the same time.

### Problem 4: Global skill has no reference files

`~/.claude/skills/agentflow/SKILL.md` (the globally installed skill) contains only the
SKILL.md file, no `references/` folder. When Claude Code is used in a project where
`agentflow skills` was never run, it uses the global skill and has no reference docs to
read, forcing it to explore Python source.

### Problem 5: GitHub Copilot does not read `.github/skills/agentflow/references/`

Copilot only auto-loads:
- `.github/copilot-instructions.md` (repo-wide, no frontmatter)
- `.github/instructions/*.instructions.md` (path-scoped, `applyTo` frontmatter)

The `.github/skills/agentflow/references/` files are never loaded by Copilot.
The current instructions file references them, but Copilot cannot follow up on that.

---

## Current Template Structure

```
skills/
├── agent-skills/
│   ├── SKILL.md          ← shared, broken paths, non-standard frontmatter
│   └── references/       ← 32 reference files, correct content
│       ├── architecture.md
│       └── ...
└── copilot/
    └── agentflow.instructions.md
```

## Target Template Structure

```
skills/
├── agent-skills/
│   └── references/       ← unchanged, 32 reference files (SKILL.md removed from here)
│       ├── architecture.md
│       └── ...
├── claude/
│   └── SKILL.md          ← Claude-specific: correct frontmatter, .claude/skills/agentflow/references/ paths
├── codex/
│   └── SKILL.md          ← Codex-specific: correct frontmatter, .agents/skills/agentflow/references/ paths
└── copilot/
    └── agentflow.instructions.md   ← updated: self-contained, no external file references
```

---

## Changes Required

### Change 1: Remove `SKILL.md` from `agent-skills/`

`agent-skills/SKILL.md` is deleted. `agent-skills/` becomes a references-only directory
that is shared across all agents. Both Claude and Codex copy this folder on install.

### Change 2: Create `claude/SKILL.md`

Frontmatter:
- Remove `metadata.resources`, `metadata.tags`, `metadata.priority`
- Add `user-invocable: false` (auto-triggered domain knowledge, hidden from `/` menu)
- Keep `name` and `description` unchanged

Body: replace every bare `references/foo.md` with
`.claude/skills/agentflow/references/foo.md` so Claude can resolve and `Read` each file.

Example diff in the workflow section:

```
# Before
- Architecture and package flow: `references/architecture.md`

# After
- Architecture and package flow: `.claude/skills/agentflow/references/architecture.md`
```

Apply to all 32 references listed in the workflow section.

### Change 3: Create `codex/SKILL.md`

Same content as `claude/SKILL.md` but every path uses
`.agents/skills/agentflow/references/foo.md`.

Codex frontmatter only needs `name` and `description` (Codex does not support the
extended Claude Code fields, so do not include `user-invocable`).

### Change 4: Update `copilot/agentflow.instructions.md`

Remove the line:
```
For deeper context on any subsystem, read the matching reference under
`.github/skills/agentflow/references/` or `agentflow-docs/docs`:
```

Replace with the actual key content embedded directly in the file: architecture overview,
core abstractions list, public package names, and the most critical conventions. Copilot
reads only this file so it must be self-contained.

The `.github/skills/agentflow/references/` folder is still installed (for human devs to
browse), but the instructions file no longer claims Copilot will read it.

### Change 5: Update `_TARGETS` in `skills.py`

The current targets use a single `agent-skills` folder artifact per agent. The updated
targets use two artifacts: one folder artifact for `references/` and one file artifact
for the agent-specific `SKILL.md`.

```python
_TARGETS: tuple[_AgentTarget, ...] = (
    _AgentTarget(
        name="Codex",
        artifacts=(
            _InstallArtifact(
                kind="folder",
                install_relpath=".agents/skills/agentflow",
                source_relpath="agent-skills",  # copies references/ subdir
                manifest=True,
            ),
            _InstallArtifact(
                kind="file",
                install_relpath=".agents/skills/agentflow/SKILL.md",
                source_relpath="codex/SKILL.md",
            ),
        ),
    ),
    _AgentTarget(
        name="Claude",
        artifacts=(
            _InstallArtifact(
                kind="folder",
                install_relpath=".claude/skills/agentflow",
                source_relpath="agent-skills",  # copies references/ subdir
                manifest=True,
            ),
            _InstallArtifact(
                kind="file",
                install_relpath=".claude/skills/agentflow/SKILL.md",
                source_relpath="claude/SKILL.md",
            ),
        ),
    ),
    _AgentTarget(
        name="GitHub",
        artifacts=(
            _InstallArtifact(
                kind="file",
                install_relpath=".github/instructions/agentflow.instructions.md",
                source_relpath="copilot/agentflow.instructions.md",
            ),
            _InstallArtifact(
                kind="folder",
                install_relpath=".github/skills/agentflow",
                source_relpath="agent-skills",  # copies references/ for human browsing
                manifest=True,
            ),
        ),
    ),
)
```

No changes needed to `_install_one`, `_install_all`, or `_write_manifest`. The existing
logic already handles mixed folder + file artifacts correctly:

- The `existing` check runs before any copy, so a SKILL.md inside a not-yet-created
  folder is not falsely flagged.
- On `--force`, `shutil.rmtree` removes the folder first; the SKILL.md path no longer
  exists so its `dest.exists()` returns False and the unlink is skipped cleanly.
- The `copytree` runs first (folder artifact), then `copyfile` (file artifact) writes
  SKILL.md into the already-created folder.

### Change 6: Fix the global skill at `~/.claude/skills/agentflow/SKILL.md`

The global skill has no `references/` folder. Its body should not instruct Claude to
read files that do not exist globally.

Replace the "Read the matching reference file" workflow with a compact self-contained
body that covers the most critical facts: package names, core abstractions, config
keys, and a note that running `agentflow skills --agent claude` in a project installs
the full reference bundle.

This is a one-time manual edit to `~/.claude/skills/agentflow/SKILL.md`, not part of
the CLI template.

---

## `skills.py` Code Changes Summary

| Location | Change |
|---|---|
| `_TARGETS[0]` (Codex) | Add second artifact: `codex/SKILL.md` → `.agents/skills/agentflow/SKILL.md` |
| `_TARGETS[1]` (Claude) | Add second artifact: `claude/SKILL.md` → `.claude/skills/agentflow/SKILL.md` |
| `_TARGETS[2]` (GitHub) | No SKILL.md artifact needed; references folder still installed for human browsing |
| `_install_one` | No change |
| `_install_all` | No change |
| `_write_manifest` | No change |

---

## Template File Changes Summary

| Action | File |
|---|---|
| Delete | `agent-skills/SKILL.md` |
| Create | `claude/SKILL.md` (fixed frontmatter, `.claude/skills/agentflow/references/` paths) |
| Create | `codex/SKILL.md` (fixed frontmatter, `.agents/skills/agentflow/references/` paths) |
| Update | `copilot/agentflow.instructions.md` (self-contained, remove dead file references) |
| Keep as-is | `agent-skills/references/` (all 32 files unchanged) |

---

## Implementation Order

1. Delete `agent-skills/SKILL.md`
2. Create `claude/SKILL.md`
3. Create `codex/SKILL.md`
4. Update `copilot/agentflow.instructions.md`
5. Update `_TARGETS` in `skills.py`
6. Manually update `~/.claude/skills/agentflow/SKILL.md` (global, no references folder)
7. Test: run `agentflow skills --agent claude --force` in a scratch project, verify
   `.claude/skills/agentflow/SKILL.md` exists with correct paths and
   `.claude/skills/agentflow/references/architecture.md` is readable
