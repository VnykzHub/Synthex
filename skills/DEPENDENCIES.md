# Synthex Skill Dependencies

> Auto-generated from `related_skills` frontmatter fields. Regenerate after any skill merge or addition.

```mermaid
graph TD
  preflight --> research-loop
  data-lineage --> experiment-auditor
  experiment-auditor --> research-loop
  research-loop --> reproducibility-checker
  research-loop --> literature-survey
  research-loop --> report
  report --> presentation
  report --> whitepaper
  knowledge-graph --> report
  knowledge-graph --> data-lineage
  scoring-framework --> experiment-auditor
  scoring-framework --> peer-validator
  reproducibility-checker --> report
  structure-validator --> preflight
  task-tracking --> delegate
  task-tracking --> pipeline
  task-orchestrator --> delegate
  task-orchestrator --> pipeline
  artifact-factory --> report
  artifact-factory --> structure-validator
  data-interpreter --> data-lineage
  data-interpreter --> knowledge-graph
  phase-templates --> delegate
  phase-templates --> pipeline
  review-cycle --> scoring-framework
  review-cycle --> peer-validator
  registry-manager --> task-tracking
  registry-manager --> preflight
  prototyping --> artifact-factory
  prototyping --> report
  frontend-dev --> presentation
  frontend-dev --> report
  3d-modeling --> presentation
  3d-modeling --> report
  recover --> delegate
  recover --> audit
```

## Key

| Edge | Meaning |
|------|---------|
| A --> B | Skill A's output is typically consumed by or feeds into skill B |
