# PROJECT BRIEF — Engram

## Goal
A local-first, agent-agnostic persistent memory system that gives AI coding agents cross-session project context with minimal context window pollution.

## Core Philosophy
- **Local-first**: Data stays on the user's machine in SQLite.
- **Agent-agnostic**: Works via CLI; any agent capable of running shell commands can use it.
- **On-demand**: Agents pull only the context they need, rather than loading massive files.
- **Hybrid Storage**: SQLite for queryability, generated Markdown for human readability/exports.

## Core Features
- **5-Table Schema**: Projects, Phases, Tasks, Memories, Audit Log.
- **CLI & MCP Interfaces**: CRUD for all entities, context-packing commands, and direct local MCP server integration for agent tooling.
- **Hybrid Retrieval**: FTS5 text search combined with local semantic vector embeddings for robust memory recall.
- **Context Packs**: Optimized `< 500` token startup context and `< 800` token task context.
- **Exports**: Markdown snapshots and handoffs.

## Non-Goals
- Cloud sync (in current scope).
- GUI/Dashboard.
