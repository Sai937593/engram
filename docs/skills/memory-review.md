# Memory Review Skill

The Memory Review skill defines the process of evaluating, updating, and sanitizing the persistent project memory database (`.engram/memory.db`) during phase completion. Its goal is to maintain a high-signal memory repository, preventing stale or redundant information from polluting future context windows.

---

## 1. Why Memory Review Matters

A clean memory store ensures that:
- AI agents in future sessions receive **precise, correct, and current** project guardrails and lessons.
- The context window remains small and high-signal, avoiding performance degradation or hallucinatory behavior.
- Outdated decisions, superseded lessons, and obsolete constraints are systematically retired.

---

## 2. Phase-Level Memory Outcomes

Phase review should record what changed in project memory:

1. **`created`**: Added durable project memories.
2. **`updated`**: Corrected or refined existing memories.
3. **`deleted`**: Removed stale or incorrect memories.
4. **`no_change`**: No durable memory updates were needed.

---

## 3. Step-by-Step Memory Review Workflow

AI agents should perform memory review as phase-completion follow-up, not as a task-finish gate:

### Step 1: Audit Phase Learnings
Review completed phase tasks and identify durable project-level learnings:
- Check if new constraints or decisions should be stored via `engram_memory_create`.
- Check if old, outdated memories should be updated or deleted.

### Step 2: Apply Memory CRUD Changes
Use normal memory tools to apply updates:
- `engram_memory_create`
- `engram_memory_update`
- `engram_memory_delete`
- `engram_memory_update_many`
- `engram_memory_delete_many`

### Step 3: Complete the Phase
After phase verification and memory cleanup, complete phase workflow:
```bash
# Complete the phase
engram_phase_complete
```
