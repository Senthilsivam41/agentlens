# Agent Lens Repository Memory

**Last updated:** 2026-08-11

This directory is the durable project handoff for completed work, current repository state, locked decisions, and upcoming phases.

## Start Here

Every implementation session must read this index, `current-status.md`, and
`next-plans.md` before changing the repository. Use `decisions.md` when a task
affects architecture, security, privacy, tenancy, or deployment. Consult
`completed-actions.md` to avoid repeating validated work.

## Memory Files

- [Completed actions](completed-actions.md): append-only evidence log of finished work.
- [Current status](current-status.md): replaceable snapshot of the repository and active phase.
- [Next plans](next-plans.md): prioritized phase sequence, dependencies, gates, and status.
- [Decisions](decisions.md): accepted product and architecture decisions.

## Canonical Project Documents

- [Product and technical architecture](../docs/agentlens-architecture.md)
- [Development roadmap](../docs/agentlens-development-roadmap.md)
- [Repository README](../README.md)

## Update Rules

1. Update memory after every completed phase or material product/architecture decision.
2. Append completed work to `completed-actions.md`; never rewrite its history.
3. Replace stale facts in `current-status.md` after every material repository change.
4. Update phase states in `next-plans.md` using only `not-started`, `in-progress`, `blocked`, or `complete`.
5. Add accepted decisions to `decisions.md`; mark superseded decisions instead of deleting them.
6. Record evidence. Never mark planned, partial, or unvalidated work complete.
7. Treat `current-status.md` and `next-plans.md` as the implementation handoff for the next session.
