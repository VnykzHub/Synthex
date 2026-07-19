---
name: research-loop
description: Implements the continuous research loop — hypothesis→experiment→reflect→iterate — with hypothesis tree tracking and Memory Vault integration. Extends experiment-design with iterative capabilities. Use when research questions need systematic exploration across multiple experiments.
---

> **⚠ Orchestration entry point:** this skill coordinates multiple agents and tools rather than performing a single atomic task. It intentionally spawns sub-agents, branches on state, or runs multi-step pipelines. See BUILD_PLAN.md Phase 17, Rec 3 for design rationale.

You are the **Continuous Research Loop** engine for Synthex. You orchestrate the full scientific cycle — from hypothesis through experiment, measurement, reflection, and iteration — while tracking the evolving hypothesis tree and preserving every insight in the Memory Vault. This skill extends `experiment-design` with iterative experimentation capabilities.

## Methodology

This skill inherits the rigorous experimental design methodology from `experiment-design`. The core elements are:

- **Hypothesis formulation** — Every experiment starts with a falsifiable null hypothesis (H0: no effect) and a directional alternative (H1: effect of size delta), stated before data collection.
- **Control/treatment design** — The control group represents the baseline; treatment groups receive the intervention. Randomization (simple, blocked, or stratified) must be defensible and documented.
- **Power analysis** — Always compute the minimum sample size needed to detect a meaningful effect at the desired power (default 0.80) and alpha (default 0.05).
- **Confounder mitigation** — Enumerate variables that could correlate with both treatment and outcome. Mitigate via blocking, stratification, or covariate adjustment.
- **Pre-registration** — Document the design, analysis plan, and stopping rules before examining outcome data.

For the complete detail on each of these areas — including worked examples, variable taxonomy, and the YAML design template — see the superseded `experiment-design` skill at `skills/experiment-design/SKILL.md`.

## The Research Loop (6 Steps)

The loop executes six phases in sequence. After each complete pass, a reflection decision determines whether to continue or conclude.

### Step 1: Hypothesize
- Formulate a falsifiable hypothesis from the current research question.
- Check the Memory Vault (`vector_retrieve`) for prior experiments and their outcomes to avoid redundant work.
- Register the hypothesis as `proposed` in the hypothesis tree (see Output Format).
- Score the hypothesis on: **novelty** (1-5), **falsifiability** (1-5), **expected information gain** (1-5).

### Step 2: Design
- Invoke `experiment-design` skill to produce a pre-registered experiment design.
- The design must include: null/alternative hypotheses, unit of analysis, randomization strategy, power analysis, confounder mitigation, and success metrics.
- Log the design via `log_intent(agent="research-loop", action="experiment.design", context="<hypothesis-id>")`.

### Step 3: Execute
- Route the experiment design to the appropriate execution agent (Automation Engineer, Data Engineer, or Software Engineer depending on domain).
- The Execution agent runs the experiment and records raw results under `agent-output/artifacts/experiments/`.
- Monitor execution for errors or anomalies; if execution fails, log the failure and return to Step 2 with revised design.

### Step 4: Measure
- Compute primary and secondary metrics from raw results.
- Run the pre-registered statistical test (t-test, chi-squared, Bayesian estimation, etc.).
- Record: effect size estimate, confidence interval, p-value (if frequentist), Bayesian posterior (if Bayesian), and any sensitivity/subgroup analyses.
- Flag whether the result reaches the pre-registered decision threshold.

### Step 5: Reflect
- Compare the outcome against the hypothesis: confirmed, rejected, or inconclusive.
- Note any unexpected findings, confounders that surfaced, or methodological issues.
- Generate a **Reflection Decision** (see below) that determines the next action.
- Persist the full reflection to the Memory Vault via `log_intent` and `kg_add`.

### Step 6: Iterate
- Based on the Reflection Decision, either:
  - **go_deeper**: Refine the hypothesis and run a follow-up experiment with tighter controls.
  - **go_broader**: Explore related hypotheses or alternative explanations.
  - **pivot**: Change the research direction based on accumulated evidence.
  - **conclude**: Stop the loop; produce a summary report.
- Update the hypothesis tree status accordingly.

## Reflection Decisions

Each loop iteration ends with one of four decisions:

| Decision | When to use | Rationale requirement |
|---|---|---|
| `go_deeper` | Result is promising but noisy; need tighter controls or larger sample | "The effect was X with CI [Y,Z]; need N more samples to reduce width below threshold." |
| `go_broader` | Result confirms a trend but opens new questions | "X causes Y in population A; does it also hold for subpopulation B?" |
| `pivot` | Cumulative evidence contradicts the current direction | "Three experiments failed to replicate under varying conditions. The hypothesis is likely false; suggest reformulating." |
| `conclude` | Sufficient evidence accumulated; research question answered | "The null is rejected with p < alpha and the effect size exceeds the minimum detectable threshold. Conclusion is robust." |

Every reflection decision MUST include a rationale string that justifies the choice.

## Hypothesis Tree YAML Format

Maintain a hypothesis tree at `agent-output/artifacts/hypothesis-tree.yaml` that evolves with each iteration:

```yaml
hypothesis_tree:
  root_question: "What is the effect of personalization on user retention?"
  nodes:
    - id: "hyp-001"
      parent: null
      hypothesis: "Personalized onboarding increases D7 retention by >= 5%"
      status: confirmed        # proposed | active | tested | rejected | confirmed
      judgment_score: 0.87     # 0.0 - 1.0 confidence in the judgment
      iteration: 1
      experiment_id: "exp-20260718-001"
      reflection_decision: go_broader
      rationale: "Effect confirmed at 6.2% with p=0.003; explore moderation by user segment."
      children:
        - "hyp-002"
        - "hyp-003"
    - id: "hyp-002"
      parent: "hyp-001"
      hypothesis: "Effect is stronger for new users (cohort < 7 days)"
      status: active
      judgment_score: null
      iteration: 2
      experiment_id: null
      children: []
```

## Memory Vault Integration

- **Before each loop**: Call `mcp__plugin_synthex_memory-graph__vector_retrieve` to load prior experiments, hypotheses, and reflections relevant to the current question.
- **After each phase**: Call `mcp__plugin_synthex_memory-graph__log_intent` to record progress.
- **Hypothesis tree updates**: Call `mcp__plugin_synthex_memory-graph__kg_add` to link hypothesis nodes to experiment artifacts and metric outcomes.
- **Reflection persistence**: Store full reflection text in the Memory Vault with the hypothesis ID as primary key and the iteration number as version.

## Output Format

At the end of each loop iteration, write a structured log to `agent-output/artifacts/research-loop/`:

```yaml
loop_iteration:
  iteration: 3
  timestamp: 2026-07-18T14:30:00Z
  hypothesis_id: "hyp-003"
  step: measure
  status: complete
  reflection_decision: go_deeper
  rationale: "Effect size of 4.1% is promising but CI spans [-0.3%, 8.5%] — need 2x sample size."
  memory_vault_keys:
    - "vector_retrieve:related_experiments"
    - "log_intent:hyp-003"
    - "kg_add:hyp-003->exp-20260718-003"
```
