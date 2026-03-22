import os
import requests

API_KEY = os.getenv("GEMINI_API_KEY")
STORE_NAME = os.getenv("GEMINI_METHOD_FILE_SEARCH_STORE")

if not API_KEY:
    raise RuntimeError("Missing GEMINI_API_KEY")

if not STORE_NAME:
    raise RuntimeError("Missing GEMINI_METHOD_FILE_SEARCH_STORE")

url = f"https://generativelanguage.googleapis.com/v1beta/{STORE_NAME}/documents"

response = requests.get(
    url,
    headers={"x-goog-api-key": API_KEY}
)

response.raise_for_status()
data = response.json()

print("\n📂 Documenten in store:\n")

for doc in data.get("documents", []):
    print(f"- {doc.get('displayName')} ({doc.get('name')})")