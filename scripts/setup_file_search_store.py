import os
import time
from pathlib import Path

from google import genai

DOCS_DIR = Path("rag_docs")
STORE_DISPLAY_NAME = "labelsprong-methodiek-store"
POLL_INTERVAL_SECONDS = 5
MAX_WAIT_SECONDS = 300


def wait_for_operation(client, operation, file_name: str):
    waited = 0

    while not operation.done:
        if waited >= MAX_WAIT_SECONDS:
            raise TimeoutError(
                f"Timed out while uploading {file_name} after {MAX_WAIT_SECONDS} seconds."
            )

        time.sleep(POLL_INTERVAL_SECONDS)
        waited += POLL_INTERVAL_SECONDS
        operation = client.operations.get(operation=operation)
        print(f"Still processing {file_name}... {waited}s")

    return operation


def main() -> None:
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise RuntimeError("Missing GEMINI_API_KEY")

    client = genai.Client(api_key=api_key)

    existing_store = os.getenv("GEMINI_METHOD_FILE_SEARCH_STORE")
    if existing_store:
        store_name = existing_store
        print(f"Using existing store: {store_name}")
    else:
        store = client.file_search_stores.create(
            config={"display_name": STORE_DISPLAY_NAME}
        )
        store_name = store.name
        print(f"Created store: {store_name}")

    files = [p for p in DOCS_DIR.iterdir() if p.is_file()]

    for path in files:
        print(f"Uploading: {path.name}")

        operation = client.file_search_stores.upload_to_file_search_store(
            file=str(path),
            file_search_store_name=store_name,
            config={"display_name": path.name},
        )

        try:
            operation = wait_for_operation(client, operation, path.name)
            print(f"Finished: {path.name}")
        except Exception as exc:
            print(f"Failed: {path.name} -> {exc}")

    print("\nUse this in Render:")
    print(f"GEMINI_METHOD_FILE_SEARCH_STORE={store_name}")


if __name__ == "__main__":
    main()