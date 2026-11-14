"""Synthetic end-to-end HTTP tests: real SQLite and ingestion, fake vectors/models."""
import hashlib
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker

from main import app
from app.core import database, dependencies
from app.core.config import settings
from app.core.auth import validate_auth_config
from app.repositories.vector_repository import VectorRepository

TOKENS = {"alice": "a" * 48, "bob": "b" * 48}

def headers(owner="alice"):
    return {"Authorization": f"Bearer {TOKENS[owner]}"}

class Embeddings:
    async def embed_text(self, text):
        return [1.0, 0.0]
    async def embed_batch(self, texts):
        return [[1.0, 0.0] for _ in texts]

class Vectors:
    def __init__(self):
        self.rows = {}
        self.fail_add = self.fail_delete = False
    def add_chunks(self, chunks, embeddings, metadatas, ids):
        self.rows.update({i: {"text": c, "metadata": m, "score": 1.0}
                          for i, c, m in zip(ids, chunks, metadatas)})
        if self.fail_add:
            raise RuntimeError("synthetic partial write")
    def search(self, query_embedding, owner_id, document_ids, **kwargs):
        return [r for r in self.rows.values() if r["metadata"]["owner_id"] == owner_id
                and r["metadata"]["document_id"] in document_ids]
    def delete_document(self, owner_id, document_id):
        if self.fail_delete:
            raise RuntimeError("synthetic vector outage")
        self.rows = {k: v for k, v in self.rows.items() if not (
            v["metadata"]["owner_id"] == owner_id and v["metadata"]["document_id"] == document_id)}

class LLM:
    def __init__(self):
        self.calls = []
    async def generate(self, system_prompt, messages):
        self.calls.append(messages)
        return messages[-1]["content"]

@pytest.fixture
def env(tmp_path, monkeypatch):
    engine = create_async_engine(f"sqlite+aiosqlite:///{tmp_path}/test.db")
    monkeypatch.setattr(database, "engine", engine)
    monkeypatch.setattr(database, "AsyncSessionLocal", async_sessionmaker(engine, expire_on_commit=False))
    monkeypatch.setattr(settings, "raw_path", str(tmp_path / "raw"))
    monkeypatch.setattr(settings, "auth_token_hashes", {k: hashlib.sha256(v.encode()).hexdigest() for k,v in TOKENS.items()})
    vectors, llm = Vectors(), LLM()
    monkeypatch.setattr(dependencies, "get_embedding_service", lambda: Embeddings())
    monkeypatch.setattr(dependencies, "get_vector_repository", lambda: vectors)
    monkeypatch.setattr(dependencies, "get_llm_service", lambda: llm)
    # Document route captures Depends callable on import, so override those too.
    from app.api.v1 import documents
    app.dependency_overrides[documents.get_embedding_service] = lambda: Embeddings()
    app.dependency_overrides[documents.get_vector_repository] = lambda: vectors
    with TestClient(app) as client:
        yield client, vectors, llm, tmp_path
    app.dependency_overrides.clear()
    import asyncio
    asyncio.run(engine.dispose())

def upload(client, owner="alice", name="same.txt", text="synthetic alpha"):
    return client.post("/api/v1/documents/upload", headers=headers(owner), files={"file": (name, text)})

def chat(client, owner="alice", question="question"):
    return client.post("/api/v1/chat", headers=headers(owner), json={"message": question, "session_id": "same-session"})

def test_fail_closed(env, monkeypatch):
    c, *_ = env
    assert c.get("/api/v1/documents").status_code == 401
    assert c.get("/api/v1/documents", headers={"Authorization":"Bearer wrong"}).status_code == 401
    monkeypatch.setattr(settings, "auth_token_hashes", {})
    with pytest.raises(RuntimeError): validate_auth_config()

def test_two_users_same_filename_and_history(env):
    c,v,llm,path = env
    a = upload(c, text="alice only").json()["document_id"]
    b = upload(c,"bob",text="bob only").json()["document_id"]
    a2 = upload(c,text="alice second").json()["document_id"]
    assert len({a,b,a2}) == 3
    assert sorted(p.name for p in (path/"raw").iterdir()) == [f"{x}.txt" for x in sorted([a,b,a2])]
    assert len(c.get("/api/v1/documents",headers=headers()).json()) == 2
    assert c.delete(f"/api/v1/documents/{a}",headers=headers("bob")).status_code == 404
    assert "bob only" not in chat(c).json()["answer"]
    assert "alice" not in chat(c,"bob").json()["answer"]
    assert len(llm.calls[-1]) == 1  # same client session ID does not leak Alice history
    chat(c)
    assert len(llm.calls[-1]) == 3
    assert c.delete(f"/api/v1/documents/{a}",headers=headers()).status_code == 200
    assert (path/"raw"/f"{a2}.txt").exists() and (path/"raw"/f"{b}.txt").exists()
    assert len(v.rows) == 2
    chat(c)
    assert len(llm.calls[-1]) == 1  # deletion removed prior possibly quoted content
    chat(c,"bob")
    assert len(llm.calls[-1]) == 3  # Bob's history retained

@pytest.mark.parametrize("name", ["../escape.txt", "a\\b.txt", "C:bad.txt", "bad.exe"])
def test_unsafe_names(env,name):
    c,_,_,path = env
    assert upload(c,name=name).status_code == 400
    assert not list((path/"raw").iterdir())

def test_limits_empty_and_invalid_text(env,monkeypatch):
    c,*_ = env
    monkeypatch.setattr(settings,"max_upload_bytes",8)
    assert upload(c,text="x"*9).status_code == 413
    assert upload(c,text="").status_code == 400
    assert upload(c,text=b"\xff").status_code == 422

def test_failed_ingestion_is_hidden_and_cleanup_retryable(env):
    c,v,llm,path = env
    v.fail_add = v.fail_delete = True
    assert upload(c).status_code == 422
    docs=c.get("/api/v1/documents",headers=headers()).json()
    assert docs[0]["status"] == "failed"
    assert chat(c).json()["sources"] == []
    assert llm.calls == []
    v.fail_delete=False
    assert c.delete(f'/api/v1/documents/{docs[0]["id"]}',headers=headers()).status_code == 200
    assert v.rows == {} and not list((path/"raw").iterdir())

def test_delete_failure_is_tombstoned_and_retryable(env):
    c,v,llm,path = env
    doc=upload(c).json()["document_id"]
    v.fail_delete=True
    assert c.delete(f"/api/v1/documents/{doc}",headers=headers()).status_code == 503
    assert chat(c).json()["sources"] == []
    v.fail_delete=False
    assert c.delete(f"/api/v1/documents/{doc}",headers=headers()).status_code == 200
    assert not list((path/"raw").iterdir())

def test_actual_vector_repository_filters():
    class Collection:
        def query(self,**kwargs):
            self.kwargs=kwargs
            return {"documents":[[]],"metadatas":[[]],"distances":[[]]}
        def delete(self,**kwargs): self.deleted=kwargs
    repo=object.__new__(VectorRepository); repo._collection=Collection()
    repo.search([1.0],"alice",[7])
    assert repo._collection.kwargs["where"] == {"$and":[{"owner_id":"alice"},{"document_id":{"$in":[7]}}]}
    repo.delete_document("alice",7)
    assert repo._collection.deleted["where"] == {"$and":[{"owner_id":"alice"},{"document_id":7}]}

def test_static_onboarding_headers(env):
    c,*_ = env
    response=c.get("/")
    assert response.status_code == 200
    assert "문서 보관함 연결" in response.text
    assert response.headers["cache-control"] == "no-store"
    assert response.headers["x-frame-options"] == "DENY"

def test_request_bound_before_multipart(env,monkeypatch):
    c,*_ = env
    monkeypatch.setattr(settings,"max_upload_bytes",8)
    assert c.post("/api/v1/documents/upload",content=b"x"*70000,headers=headers()).status_code==413
    assert c.post("/api/v1/documents/upload",content=b"x"*70000).status_code==401

@pytest.mark.asyncio
async def test_legacy_database_refused(tmp_path,monkeypatch):
    from sqlalchemy import text
    engine=create_async_engine(f"sqlite+aiosqlite:///{tmp_path}/legacy.db")
    async with engine.begin() as c:
        await c.execute(text("CREATE TABLE documents (id INTEGER PRIMARY KEY, filename TEXT)"))
    monkeypatch.setattr(database,"engine",engine)
    with pytest.raises(RuntimeError,match="Legacy database"):
        await database.init_db()
    await engine.dispose()

@pytest.mark.asyncio
async def test_deletion_invalidates_inflight_answer(env):
    import asyncio
    import httpx
    from sqlalchemy import select
    from app.models.chat import ChatMessage
    c,v,llm,path = env
    doc=upload(c,text="sensitive synthetic excerpt").json()["document_id"]
    started, release = asyncio.Event(), asyncio.Event()
    original = llm.generate
    async def paused_generate(system_prompt,messages):
        started.set()
        await release.wait()
        return await original(system_prompt,messages)
    llm.generate=paused_generate
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app),base_url="http://test",trust_env=False) as client:
        pending=asyncio.create_task(client.post("/api/v1/chat",headers=headers(),json={"message":"question","session_id":"same-session"}))
        await asyncio.wait_for(started.wait(),2)
        deletion=await client.delete(f"/api/v1/documents/{doc}",headers=headers())
        assert deletion.status_code==200
        release.set()
        response=await asyncio.wait_for(pending,2)
        assert response.status_code==409
        assert "sensitive synthetic" not in response.text
    async with database.AsyncSessionLocal() as db:
        assert (await db.scalars(select(ChatMessage))).all()==[]


def test_exclusive_create_failure_preserves_existing_file(env):
    c,v,llm,path=env
    collision=path/"raw"/"1.txt"
    collision.write_text("pre-existing unrelated synthetic file")
    assert upload(c).status_code==422
    assert collision.read_text()=="pre-existing unrelated synthetic file"
    doc=c.get("/api/v1/documents",headers=headers()).json()[0]
    assert c.delete(f'/api/v1/documents/{doc["id"]}',headers=headers()).status_code==200
    assert collision.read_text()=="pre-existing unrelated synthetic file"
    new=upload(c).json()["document_id"]
    assert new>doc["id"]


def test_ui_discloses_irreversible_history_clear(env):
    c,*_=env
    page=c.get("/").text
    assert "내 모든 대화 기록도 초기화" in page
    assert "삭제가 일부 실패해도 대화 기록은 복구되지 않습니다" in page
    assert "epoch !== conversationEpoch" in page
