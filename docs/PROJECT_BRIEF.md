# PROJECT BRIEF — Engram

## Goal
A local-first, agent-agnostic persistent memory system that gives AI coding agents cross-session project context with minimal context window pollution.

## Core Philosophy
- **Local-first**: Data stays on the user's machine in SQLite.
- **Agent-agnostic**: Works via CLI; any agent capable of running shell commands can use it.
- **On-demand**: Agents pull only the context they need, rather than loading massive files.
- **Hybrid Storage**: SQLite for queryability, generated Markdown for human readability/exports.

## MVP Features
- **4-Table Schema**: Projects, Tasks, Memories, Sessions.
- **CLI Interface**: CRUD for all entities, context-packing commands, and session management.
- **Search**: FTS5 text search for memories.
- **Context packs**: Optimized `< 500` token startup context and `< 800` token task context.
- **Exports**: Markdown snapshots and handoffs.

## Non-Goals
- Cloud sync (MVP).
- Vector/Semantic search (MVP).
- GUI/Dashboard.
- MCP server (post-MVP).
