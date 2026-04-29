# AI Support Ticket Classifier & Decision Engine

This is a production-grade AI-powered backend system built with FastAPI and MySQL. It uses FAISS for vector search (RAG) and Groq for fast LLM inference.

## Architecture

The system follows a modular architecture:
- **API Layer**: Handles incoming HTTP requests and routes them to the workflow engine.
- **Workflow Engine**: Orchestrates the process across states (INIT -> PROCESSING -> AI_EVALUATION -> MANUAL_REVIEW / SUCCESS / FAILED). Uses a custom in-memory queue for task processing with exponential backoff for retries.
- **AI Engine (Groq)**: Prompts an LLM (Llama 3 via Groq API) to evaluate support tickets. It forces strict JSON output based on a Pydantic schema and gracefully handles unstructured data.
- **RAG Engine (FAISS)**: Converts the input ticket to an embedding and retrieves relevant context from a local knowledge base to inject into the LLM prompt.
- **Decision Engine**: Combines the AI's confidence and decision with configurable rules to produce a final outcome.
- **Database (MySQL)**: Stores complete state, history, and audit logs.

## Setup Instructions

1. **Clone the repository**

2. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

3. **Set environment variables**:
   ```bash
   # Use MySQL in production, SQLite for local testing
   export DATABASE_URL="mysql+pymysql://root:password@localhost/ai_platform"
   export GROQ_API_KEY="your_groq_api_key_here"
   ```

4. **Run the server**:
   ```bash
   uvicorn main:app --reload
   ```

5. **Run tests**:
   ```bash
   pytest
   ```

## Groq + FAISS Integration

- **FAISS**: The `RAGEngine` uses `SentenceTransformer` ('all-MiniLM-L6-v2') to convert text into embeddings. The local FAISS index stores these vectors. When a ticket arrives, its context is queried against FAISS to pull relevant knowledge base articles.
- **Groq**: The `AIEngine` leverages Groq's fast inference endpoint. It is strictly prompted to return `response_format: {"type": "json_object"}`. The prompt includes the RAG context and the strict Pydantic JSON schema structure. If the AI is unsure, it flags `uncertainty=true` to force a manual review.

## Sample API Requests

### 1. Create a Support Ticket
```bash
curl -X POST "http://localhost:8000/api/requests" \
     -H "Content-Type: application/json" \
     -H "idempotency-key: 123456" \
     -d '{
           "subject": "Broken item",
           "description": "My item arrived completely shattered",
           "customer_id": "cust_123"
         }'
```

### 2. Explain API Output Example
```bash
curl -X GET "http://localhost:8000/api/requests/req_abcdef123456/explain"
```
**Response:**
```json
{
  "request_id": "req_abcdef123456",
  "input_data": {
    "subject": "Broken item",
    "description": "My item arrived completely shattered",
    "customer_id": "cust_123",
    "priority": "normal"
  },
  "retrieved_context": [
    "Refund policy: Users can request a refund within 30 days of purchase. The item must be damaged or defective. Action: approve refund."
  ],
  "ai_output": {
    "decision": "approve",
    "confidence": 0.95,
    "reason": "Customer received a damaged item, fitting the refund criteria.",
    "uncertainty": false,
    "category": "refund_request"
  },
  "rules_triggered": [],
  "final_decision": "approve",
  "confidence_score": 0.95,
  "failure_reasons": null,
  "current_state": "SUCCESS"
}
```

