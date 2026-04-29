# Tradeoffs and Decisions

## Architecture Choices

1. **In-Memory Queue vs. Redis**
   - *Requirement*: DO NOT use Redis. Implement an in-memory queue.
   - *Tradeoff*: An in-memory queue using Python's `queue.PriorityQueue` is fast and easy to set up. However, it is not distributed. If the FastAPI server crashes, any pending tasks in the queue are lost unless we reload them from the database on startup. For a truly scalable production system, an external broker (RabbitMQ/Kafka/Redis) is preferable. We mitigated data loss by persisting the `INIT` state in MySQL before enqueuing.

2. **FAISS Local Vector Store**
   - *Tradeoff*: We used `faiss-cpu` with an in-memory index built at startup. This is excellent for low-latency retrieval and prototyping. However, scaling across multiple server instances requires a shared vector database (like Pinecone, Qdrant, or pgvector).

3. **Groq LLM**
   - *Tradeoff*: Groq provides incredibly fast inference, which is ideal for synchronous or near-synchronous API responses. We used `llama3-8b-8192` for cost and speed. A larger model (like 70B) would provide better reasoning at the cost of slight latency.

4. **Synchronous SQLAlchemy vs. Async**
   - *Tradeoff*: We used synchronous SQLAlchemy. While FastAPI is asynchronous, we run our queue worker in a background thread which naturally handles synchronous database operations well. Moving to fully `asyncio` with `asyncpg` would improve throughput but increases code complexity.

5. **Decision Engine Logic**
   - *Tradeoff*: The rule engine uses simple operator mapping (`<`, `>`, `==`). A more sophisticated system would parse complex ASTs or use a library like `business-rules`. Our approach is lightweight and easily configurable via DB.
