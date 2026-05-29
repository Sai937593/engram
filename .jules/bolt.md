2024-05-29 - Optimize database query loading all project memories
- Found that `build_task_context` was inefficiently loading all project memories into python list and then filtering by `task_id`.
- Replaced with `list_by_task` query on the `Memory` model that directly fetches memories linked to a specific task using SQL filtering (`WHERE task_id = ?`).
- This change resulted in a 87% improvement in test baseline run time (from 1.4818 seconds down to 0.1908 seconds for a database containing 10,000 project memories and 100 task linked memories).
