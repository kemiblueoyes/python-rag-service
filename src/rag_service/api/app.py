# Used to only confirms  that the Python service starts and responds correctly
from fastapi import FastAPI

app = FastAPI(
    title="Python RAG Service",
    version="0.1.0",
)


@app.get("/health")
def health_check() -> dict[str, str]:
    return {"status": "ok"}
