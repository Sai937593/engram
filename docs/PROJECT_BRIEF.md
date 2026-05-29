# PROJECT BRIEF — Engram

## Goal
A local-first, agent-agnostic persistent memory system that gives AI coding agents cross-session project context with minimal context window pollution.

## Core Philosophy
- **Local-first**: Data stays on the user's machine in SQLite.
- **Agent-agnostic**: Works via the Model Context Protocol (MCP); any agent capable of connecting to custom MCP servers can use it, with a minimal CLI companion for initialization and diagnostics.
- **On-demand**: Agents pull only the context they need dynamically, rather than loading massive files.
- **Hybrid Storage**: SQLite for queryability, generated Markdown for human readability/exports.

## Features
- **MCP-First Architecture**: 17 specialized tools and 4 local resources exposed via STDIO transport.
- **4-Table Core Schema**: Projects, Phases, Tasks, Memories.
- **Trimmed CLI**: Setup, packaged guide, and database health utilities (`init`, `guide`, `db`).
- **Search**: Lexical FTS5 text search combined with local fastembed semantic search.
- **Context packs**: Optimized startup and task context packages delivered programmatically.
- **Exports**: Programmatically generated Markdown snapshots and handoffs.

## Non-Goals
- Cloud sync (out of scope).
- GUI/Dashboard.
