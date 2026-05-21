---
name: portfolio-readme
description: Use when writing or rewriting a README.md for a portfolio-quality software project. Focus on recruiter-facing framing, architecture clarity, concise quick start instructions, design decisions, and honest tradeoffs rather than exhaustive file-by-file documentation.
---

# Portfolio README

## Write for a fast scan

Assume the reader gives the repository about 30 seconds.

Lead with:

- project name
- one-sentence value proposition
- compact tech stack
- the problem the project solves

## Use a tight structure

A strong portfolio README usually includes:

1. Header with the project name and one-line summary
2. Short problem and outcome section
3. Architecture diagram, preferably Mermaid if no image exists
4. Tech stack with brief tool-selection reasoning
5. Quick start with only the necessary commands
6. Key design decisions
7. Tradeoffs or what you would improve next
8. Contact links when the repo is intended for recruiting

## Emphasize engineering judgment

Explain why the system is shaped this way.

Good examples:

- why a storage engine was chosen
- why the repo uses `src` layout
- why the validation path is structured a certain way
- why a queue, cache, or orchestration layer exists

Avoid vague claims about learning or passion. Prefer concrete operational outcomes, constraints, and tradeoffs.

## Keep the README readable

- Keep sections short.
- Avoid long installation procedures when a shorter quick start works.
- Do not document every file or directory.
- Do not paste large screenshots of code.
- Prefer one useful architecture visual over many decorative images.

## Update when behavior changes

Treat README work as product documentation, not a one-time marketing pass. If install, usage, or configuration changes, update the README in the same change.
