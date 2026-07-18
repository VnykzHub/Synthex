---
name: compile-resources
description: /synthex:compile-resources — Generates reference materials from source files or descriptions via InsightCompiler.
disable-model-invocation: true
---

You are the **Compile Resources** command skill for Synthex. When invoked (via the `/synthex:compile-resources` slash command), you generate a consolidated reference document by extracting and compiling information from source files or from descriptions provided interactively, using the Insight Compiler pattern.

## Behavior
- `disable-model-invocation: true` — this skill runs as a script, not an agent prompt. It is triggered by the slash command and may prompt the user for input.

## What this skill produces
A file at `E:/PROJECTS 2026/Synthex/synthex-plugin/resources.md` containing a compiled reference of:

1. **Core concepts** — extracted entities and their definitions, drawn from source materials or user descriptions.
2. **Terminology glossary** — alphabetically sorted terms with concise definitions and cross-references.
3. **Source catalog** — list of all input sources consulted, with format, size, and extraction timestamp.
4. **Relationship map** — directed relationships between core concepts in text or Mermaid diagram form.
5. **Constraint inventory** — all documented constraints with severity and provenance.
6. **Assumption register** — all documented assumptions with verification status.
7. **Contradiction log** — any unresolved contradictions found across sources.

## Invocation workflow
1. Scan `agent-output/artifacts/extractions/` and `agent-output/artifacts/insights/` for existing manifests and insight reports. If none exist, prompt the user to provide source file paths or concept descriptions directly.
2. If extraction manifests exist but no insight report has been compiled, perform a lightweight compilation (entity merging + confidence assignment) inline.
3. If both extractions and insights exist, compile from the insight report as the authoritative layer.
4. Write `resources.md` to the project root with the compiled reference.
5. Log the intent via `log_intent(agent="synthex-cli", action="skill.compile-resources", why="User invoked compile-resources")`.

## Rules
- Always prefer the insight report over raw extractions when both exist. The insight report already performs cross-referencing and conflict resolution.
- If contradictions remain unresolved, surface them prominently in the resource document with clear indication that they are unresolved.
- The resource document is a snapshot. Timestamp it and do not overwrite without creating a backup of the previous version.
- If no source materials exist and the user does not provide descriptions, produce a minimal resource document with a note that no sources were available.
