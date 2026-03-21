import os

def get_llm_response(prompt):
    if not os.getenv("OPENAI_API_KEY"):
        return "Mock response (no API key)"
    
    # hier straks je echte LLM call
    return "Real response (placeholder)"
