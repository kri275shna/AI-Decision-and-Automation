import os
import faiss
import numpy as np
from sentence_transformers import SentenceTransformer

class RAGEngine:
    def __init__(self):
        self.dimension = 384
        self.index = faiss.IndexFlatL2(self.dimension)
        self.model = SentenceTransformer('all-MiniLM-L6-v2')
        self.documents = []
        
        self._initialize_knowledge_base()

    def _initialize_knowledge_base(self):
        kb = [
            "Refund policy: Users can request a refund within 30 days of purchase. The item must be damaged or defective. Action: approve refund.",
            "Account locked: If an account is locked due to multiple failed login attempts, the user must reset their password via email. Action: escalate to tech support.",
            "Missing item: If an item is missing from an order, ask for the order number and check warehouse logs. Action: manual review.",
            "Subscription cancel: Users can cancel subscriptions anytime from their billing dashboard. Action: approve cancellation.",
            "Feature request: Forward all feature requests to the product team. Action: escalate."
        ]
        self.add_documents(kb)

    def add_documents(self, docs):
        if not docs:
            return
        embeddings = self.model.encode(docs)
        self.index.add(np.array(embeddings, dtype=np.float32))
        self.documents.extend(docs)

    def retrieve(self, query, top_k=2):
        if self.index.ntotal == 0:
            return []
        query_vector = self.model.encode([query])
        distances, indices = self.index.search(np.array(query_vector, dtype=np.float32), top_k)
        
        results = []
        for i, idx in enumerate(indices[0]):
            if idx != -1 and idx < len(self.documents):
                if distances[0][i] < 1.5: 
                    results.append(self.documents[idx])
        return results

rag_engine = RAGEngine()
