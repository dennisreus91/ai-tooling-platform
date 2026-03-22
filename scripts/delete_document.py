import os
import requests

API_KEY = os.getenv("GEMINI_API_KEY")

DOCUMENTS_TO_DELETE = [
    "fileSearchStores/labelsprongmethodiekstore-lmbutvip45as/documents/isso8216edrukpdf-pn11v0n8l2yn",
    "fileSearchStores/labelsprongmethodiekstore-lmbutvip45as/documents/energielabel-tabelpdf-7tmuwhqv6ou5",
    "fileSearchStores/labelsprongmethodiekstore-lmbutvip45as/documents/nta-88002024-nl-1pdf-pgl4oi313fyd",
]

for doc_name in DOCUMENTS_TO_DELETE:
    url = f"https://generativelanguage.googleapis.com/v1beta/{doc_name}?force=true"

    response = requests.delete(
        url,
        headers={"x-goog-api-key": API_KEY}
    )

    if response.status_code == 200:
        print(f"Deleted: {doc_name}")
    else:
        print(f"Failed: {doc_name} -> {response.text}")