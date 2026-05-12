# LESSONS

## Lessons
- **Data Model Alignment**: Ensure CLI commands (add/update/get) support all fields defined in the data model (e.g., `acceptance`, `phase`). Inconsistent exposure leads to "hidden" data.
- **CLI Aesthetics**: Using `rich.table.Table` with explicit `header_style` and `border_style` significantly improves agent readability and human UX.
- **On-demand Context**: Generated Markdown exports (snapshots/handoffs) should prioritize density over verbosity to keep context windows lean.
