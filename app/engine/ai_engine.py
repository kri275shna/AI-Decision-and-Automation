import os
import json
import httpx
from pydantic import ValidationError
from app.schemas.schemas import AIStructuredOutput
from app.utils.logger import logger

GROQ_API_KEY = os.getenv("GROQ_API_KEY")
GROQ_API_URL = "https://api.groq.com/openai/v1/chat/completions"
MODEL_NAME = "llama3-8b-8192"

class AIEngine:
    def __init__(self, api_key=None):
        self.api_key = api_key or GROQ_API_KEY

    def evaluate_ticket(self, input_data: dict, context: list) -> dict:
        if not self.api_key:
            logger.warning("No GROQ_API_KEY found, using mock evaluation for testing.")
            return self._mock_evaluate(input_data)

        prompt = self._build_prompt(input_data, context)
        
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "model": MODEL_NAME,
            "messages": [
                {
                    "role": "system",
                    "content": "You are an AI support ticket classifier and decision engine. You must output STRICT JSON matching the schema provided. Do not hallucinate. If you are unsure or the context is insufficient, set uncertainty to true and confidence low."
                },
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            "response_format": {"type": "json_object"},
            "temperature": 0.0
        }
        
        try:
            with httpx.Client(timeout=10.0) as client:
                response = client.post(GROQ_API_URL, headers=headers, json=payload)
                response.raise_for_status()
                data = response.json()
                
                content = data["choices"][0]["message"]["content"]
                
                parsed_json = json.loads(content)
                validated_output = AIStructuredOutput(**parsed_json)
                return validated_output.model_dump()
                
        except httpx.HTTPError as e:
            logger.error(f"Groq API Error: {str(e)}")
            raise Exception(f"LLM API failure: {str(e)}")
        except (json.JSONDecodeError, ValidationError) as e:
            logger.error(f"Structured output validation failed: {str(e)}")
            raise Exception(f"Invalid JSON or schema from LLM: {str(e)}")
        except Exception as e:
            logger.error(f"Unexpected AI Engine error: {str(e)}")
            raise Exception(f"Unexpected AI Engine error: {str(e)}")

    def _build_prompt(self, input_data, context):
        schema = AIStructuredOutput.model_json_schema()
        
        context_str = "\n".join([f"- {c}" for c in context]) if context else "No context available."
        
        prompt = f"""
Analyze the following customer support ticket and decide the best action based on the retrieved knowledge base context.

Ticket Details:
{json.dumps(input_data, indent=2)}

Knowledge Base Context:
{context_str}

Output JSON matching this EXACT schema:
{json.dumps(schema, indent=2)}

Rules:
- decision: Must be one of ['approve', 'reject', 'escalate', 'manual_review']
- uncertainty: true if ticket is ambiguous, otherwise false
- category: Determine based on the ticket
- reason: Brief explanation
"""
        return prompt

    def _mock_evaluate(self, input_data):
        return {
            "decision": "manual_review",
            "confidence": 0.5,
            "reason": "Mocked response",
            "uncertainty": True,
            "category": "unknown"
        }

ai_engine = AIEngine()
