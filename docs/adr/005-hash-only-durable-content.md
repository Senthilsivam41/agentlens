# ADR-005: Hash-Only Durable Content

**Status:** Accepted

Prompts and outputs exist only in encrypted transient transport for at most 15 minutes. Durable records contain HMAC-SHA256 hashes, embeddings, data-quality facts, and derived features. Logs must never contain raw content.

