# Task Tracking — Reference

## Status Transition Diagram

```
BACKLOG ──→ READY ──→ IN_PROGRESS ──→ REVIEW ──→ DONE
  ↑           ↑            │              │
  └─── blocked ────────────┴──→ BLOCKED ←─┘
                                    │
                                    ↓
                                  CANCELLED
```

- **READY** requires: assigned owner, priority label, and acceptance criteria.
- **IN_PROGRESS** auto-sets the `started_at` timestamp.
- **REVIEW** blocks merge until all required reviewers approve.
- **DONE** requires a completed PR merged to the target branch.
- **BLOCKED** records a `blocked_reason` and `blocked_since` timestamp.
- **CANCELLED** allowed only from BLOCKED or BACKLOG (never IN_PROGRESS or REVIEW).

## Priority Escalation Rules

| Priority | Response Time | Max Age | Auto-Escalation |
|----------|---------------|---------|-----------------|
| P0 (critical) | 1 hour | 4 hours | Notify on-call after 2h |
| P1 (high) | 4 hours | 24 hours | Escalate to lead after 8h |
| P2 (medium) | 24 hours | 5 days | Escalate after 3 days |
| P3 (low) | 5 days | 30 days | Review at weekly triage |

- P0 tasks trigger Slack/PagerDuty notification on creation.
- Tasks exceeding Max Age auto-escalate to the next higher priority.
- Unresolved P0 = incident requiring a postmortem.

## Task Lifecycle with PR/Merge States

```
                    ┌── PR_DRAFT ──┐
                    │              │
                    ↓              │
IN_PROGRESS → PR_OPEN ───────→ PR_APPROVED → PR_MERGED → DONE
                    │                                  ↑
                    ↓                                  │
              CHANGES_REQUESTED ────────────────────────┘
                    │
                    ↓
                BLOCKED
```

- `PR_DRAFT`: Work in progress, not ready for review.
- `PR_OPEN`: Review requested. Auto-assigns CODEOWNERS reviewers.
- `CHANGES_REQUESTED`: Auto-transitions task to BLOCKED.
- `PR_APPROVED`: All required checks pass before merge is enabled.
- `PR_MERGED`: Only then does task transition to DONE.
- Track `pr_url` and `merge_sha` on each task record for audit trail.
