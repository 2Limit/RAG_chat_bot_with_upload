"""Real loopback TCP smoke, temporary data and fake models. No external API calls."""
import hashlib
import socket
import tempfile
import threading
import time
from pathlib import Path
import httpx
import uvicorn
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from main import app
from app.core import database, dependencies
from app.core.config import settings
from app.api.v1 import documents
from tests.test_security import Embeddings, Vectors, LLM


def main():
    with tempfile.TemporaryDirectory(prefix="rag-synthetic-") as directory:
        settings.raw_path = str(Path(directory)/"raw")
        settings.auth_token_hashes = {"smoke": hashlib.sha256(b"synthetic-smoke-token").hexdigest()}
        database.engine = create_async_engine(f"sqlite+aiosqlite:///{directory}/test.db")
        database.AsyncSessionLocal = async_sessionmaker(database.engine,expire_on_commit=False)
        vector, llm = Vectors(), LLM()
        dependencies.get_embedding_service = lambda: Embeddings()
        dependencies.get_vector_repository = lambda: vector
        dependencies.get_llm_service = lambda: llm
        app.dependency_overrides[documents.get_embedding_service] = lambda: Embeddings()
        app.dependency_overrides[documents.get_vector_repository] = lambda: vector
        sock = socket.socket(); sock.bind(("127.0.0.1",0))
        server = uvicorn.Server(uvicorn.Config(app,log_level="error",access_log=False))
        thread = threading.Thread(target=lambda:server.run(sockets=[sock]),daemon=True)
        thread.start()
        try:
            for _ in range(100):
                if server.started: break
                time.sleep(.05)
            assert server.started
            with httpx.Client(base_url=f"http://127.0.0.1:{sock.getsockname()[1]}",timeout=5,trust_env=False) as client:
                assert client.get("/").status_code == 200
                assert client.get("/api/v1/documents").status_code == 401
                client.headers["Authorization"] = "Bearer synthetic-smoke-token"
                response=client.post("/api/v1/documents/upload",files={"file":("smoke.txt",b"Synthetic shipping rule: blue boxes only.")})
                assert response.status_code==200,response.text
                doc=response.json()["document_id"]
                response=client.post("/api/v1/chat",json={"message":"shipping rule?","session_id":"smoke"})
                assert response.status_code==200 and "blue boxes" in response.json()["answer"]
                assert client.delete(f"/api/v1/documents/{doc}").status_code==200
                assert client.get("/api/v1/documents").json()==[]
            print("PASS: loopback UI -> auth -> upload -> retrieve/chat -> delete; synthetic data only")
        finally:
            server.should_exit=True
            thread.join(timeout=5)
            sock.close()
            import asyncio
            asyncio.run(database.engine.dispose())
            app.dependency_overrides.clear()

if __name__ == "__main__": main()
