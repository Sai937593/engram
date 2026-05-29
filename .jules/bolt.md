# Performance Learnings

## 2025-02-18 - Semantic Indexing Batch Performance

When using `fastembed` for generating semantic embeddings, embedding items one by one sequentially via a loop over multiple strings (e.g. `list(embedder.embed([text]))`) is significantly slower than batching.
A benchmark of 100 simple strings embedded using `BAAI/bge-small-en-v1.5` demonstrated:
- Sequential: ~0.3959 seconds
- Batched (`list(embedder.embed(texts))`): ~0.1062 seconds
This results in a ~4x performance improvement.

**Implementation note for resilience:** When introducing batching to an iterator/generator over multiple items, a failure in one item during embedding will crash the entire batched iterator loop and forfeit processing the remainder. In fault-tolerant systems, it is beneficial to attempt processing the entire batch, and catch exceptions at the batch level to fallback to processing sequentially. This preserves exact semantics of skipping only failed items and maintaining robust execution while securing major speed boosts for the 99% happy path.
