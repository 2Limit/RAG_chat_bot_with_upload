# 📄 RAG Chat Bot with Upload

> 문서를 업로드하고, 그 내용을 기반으로 AI와 대화하는 RAG 기반 챗봇 서비스

![Python](https://img.shields.io/badge/Python-3.11+-3776AB?logo=python&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-0.115-009688?logo=fastapi&logoColor=white)
![ChromaDB](https://img.shields.io/badge/ChromaDB-0.5-orange)
![Upstage](https://img.shields.io/badge/Upstage-Solar_Pro-blueviolet)

---

## 🔍 프로젝트 소개

**RAG Chat Bot with Upload**는 사용자가 직접 업로드한 문서를 기반으로 질문에 답변하는 AI 챗봇입니다.

일반적인 LLM은 학습 데이터 이외의 내용에 대해 할루시네이션(Hallucination)을 일으키거나 "모른다"고 답하는 한계가 있습니다. 이 프로젝트는 **RAG(Retrieval-Augmented Generation)** 구조를 통해 모델이 직접 문서를 참조하여 사실 기반의 정확한 답변을 생성하도록 설계되었습니다.

---

## 🎯 문제 정의

| 문제 | 해결 방식 |
|------|-----------|
| LLM의 할루시네이션 | 업로드된 문서만을 근거로 답변하도록 시스템 프롬프트 제한 |
| 최신 정보 반영 불가 | 사용자가 원하는 문서를 직접 업로드하여 실시간 반영 |
| 답변 출처 불명확 | 모든 응답에 출처 문서명과 유사도 점수 함께 반환 |
| 긴 문서 처리 불가 | Chunking + Vector DB로 관련 부분만 정밀 검색 |

---

## ✨ 주요 기능

- **📁 문서 업로드** — `.txt`, `.md`, `.pdf` 형식 지원, 업로드 즉시 검색 가능
- **💬 RAG 기반 답변** — 업로드된 문서에서 관련 내용을 검색 후 LLM으로 답변 생성
- **🗂️ 출처 표시** — 응답마다 참조한 파일명과 유사도 점수 표시
- **🔁 멀티턴 대화** — 최근 3턴의 대화 히스토리를 컨텍스트로 유지
- **🗑️ 문서 삭제** — RDB, Vector DB, 파일 시스템에서 동시 삭제
- **🌐 반응형 웹 UI** — 별도 설치 없이 브라우저에서 바로 사용

---

## 🏗️ 아키텍처

### 전체 구조

```
[Browser]
    │  HTTP (REST)
    ▼
[FastAPI Server]
    ├── Router       → 요청 수신 및 스키마 검증
    ├── Service      → 비즈니스 로직 (RAG 파이프라인 조율)
    └── Repository   → DB 접근 추상화
         ├── SQLite     (대화 히스토리, 문서 메타데이터)
         └── ChromaDB   (문서 임베딩 벡터)

[External API]
    ├── HuggingFace  → 텍스트 임베딩 (intfloat/multilingual-e5-small, 로컬)
    └── Upstage AI   → LLM 답변 생성 (Solar Pro)
```

### 질문 → 답변 흐름

```
사용자 질문 입력
    │
    ▼ 1. 질문 임베딩 (HuggingFace, 로컬)
    │
    ▼ 2. Vector DB 유사 문서 검색 (ChromaDB, Top-5, cosine similarity)
    │
    ▼ 3. 컨텍스트 구성 (검색된 청크 + 대화 히스토리)
    │
    ▼ 4. LLM 호출 (Upstage Solar Pro API)
    │
    ▼ 5. 답변 + 출처 반환 → 대화 히스토리 저장 (SQLite)
```

### 문서 업로드 흐름

```
파일 업로드
    │
    ▼ 1. 파싱  (txt/md: 직접 읽기 / pdf: pypdf)
    ▼ 2. 정제  (빈 줄 제거, 공백 정리)
    ▼ 3. 청킹  (chunk_size=500, overlap=50)
    ▼ 4. 임베딩 배치 처리 (32개씩)
    ▼ 5. ChromaDB 저장 (벡터 + 메타데이터)
    ▼ 6. SQLite에 문서 메타데이터 기록
```

---

## 🛠️ 기술 스택

| 분류 | 기술 | 선택 이유 |
|------|------|-----------|
| Backend | FastAPI | 비동기 처리, 자동 API 문서, Pydantic 검증 |
| Frontend | Vanilla JS | 추가 프레임워크 없이 빠른 구현 |
| Vector DB | ChromaDB | 로컬 영구 저장, 설치 간편, cosine 검색 |
| RDB | SQLite | 초기 개발에 적합, 무설치, 이후 PostgreSQL 마이그레이션 가능 |
| Embedding | sentence-transformers | 로컬 실행으로 API 비용 없음, 한국어 지원 |
| LLM | Upstage Solar Pro | 한국어 특화, OpenAI 호환 인터페이스 |
| ORM | SQLAlchemy (async) | 비동기 DB 접근, 타입 안전 |

---

## 🚀 설치 및 실행 방법

### 사전 요구사항

- Python 3.11 이상
- Upstage AI API 키 ([콘솔에서 발급](https://console.upstage.ai))
- HuggingFace API 키 ([설정에서 발급](https://huggingface.co/settings/tokens))

### 1. 저장소 클론

```bash
git clone https://github.com/{your-username}/RAG_chat_bot_with_upload.git
cd RAG_chat_bot_with_upload
```

### 2. 가상환경 생성 및 패키지 설치

```bash
python -m venv venv

# Windows
venv\Scripts\activate
# macOS/Linux
source venv/bin/activate

pip install -r requirements.txt
```

### 3. 환경 변수 설정

```bash
cp .env.example .env
```

`.env` 파일을 열어 API 키를 입력합니다:

```env
# Upstage AI
UPSTAGE_API_KEY=your_upstage_api_key_here
UPSTAGE_BASE_URL=https://api.upstage.ai/v1

# HuggingFace
HUGGINGFACE_API_KEY=your_huggingface_api_key_here
HUGGINGFACE_EMBEDDING_MODEL=intfloat/multilingual-e5-small

# App
APP_NAME=RAG Chatbot
DEBUG=true

# Database
DATABASE_URL=sqlite+aiosqlite:///./data/chatbot.db
VECTORDB_PATH=./data/vectordb

# RAG 파라미터
RAG_TOP_K=5
RAG_SCORE_THRESHOLD=0.7
RAG_CHUNK_SIZE=500
RAG_CHUNK_OVERLAP=50
```

### 4. 서버 실행

```bash
uvicorn main:app --reload
```

| URL | 설명 |
|-----|------|
| `http://localhost:8000` | 챗봇 웹 UI |
| `http://localhost:8000/docs` | Swagger API 문서 |
| `http://localhost:8000/api/v1/health` | 서버 상태 확인 |

> **첫 실행 시** 임베딩 모델(~120MB)이 자동 다운로드됩니다. 인터넷 연결이 필요합니다.

---

## 📁 프로젝트 구조

```
chatbot/
│
├── main.py                        # FastAPI 앱 진입점, 전역 예외 핸들러
├── requirements.txt
├── .env.example                   # 환경 변수 템플릿
│
├── app/
│   ├── core/
│   │   ├── config.py              # 환경 변수 로드 (pydantic-settings)
│   │   ├── database.py            # SQLAlchemy 비동기 엔진
│   │   └── dependencies.py        # 의존성 주입 (DI) 설정
│   │
│   ├── api/v1/
│   │   ├── chat.py                # POST /chat
│   │   ├── documents.py           # POST /upload, GET/DELETE /documents
│   │   └── health.py              # GET /health
│   │
│   ├── schemas/                   # Pydantic 요청/응답 스키마
│   ├── models/                    # SQLAlchemy ORM 모델 (ChatSession, Document)
│   │
│   ├── services/
│   │   ├── rag_service.py         # RAG 파이프라인 핵심 로직
│   │   ├── chat_service.py        # 대화 흐름 오케스트레이션
│   │   ├── embedding_service.py   # 로컬 임베딩 (sentence-transformers)
│   │   ├── llm_service.py         # Upstage Solar API 호출
│   │   └── document_service.py    # 문서 업로드/삭제 처리
│   │
│   ├── repositories/
│   │   ├── chat_repository.py     # SQLite 대화 CRUD
│   │   └── vector_repository.py   # ChromaDB 벡터 CRUD
│   │
│   └── pipelines/
│       ├── ingestion_pipeline.py  # 문서 → 벡터 저장 파이프라인
│       └── chunking.py            # 텍스트 청킹 전략
│
├── frontend/
│   └── index.html                 # 채팅 UI (문서 업로드 + 멀티턴 대화)
│
├── data/
│   ├── raw/                       # 업로드된 원본 파일
│   ├── vectordb/                  # ChromaDB 영구 저장소
│   └── chatbot.db                 # SQLite DB
│
└── tests/
    └── test_rag.py                # 청킹 단위 테스트
```

---

## 💭 기술적 고민

### RAG vs 파인튜닝, 왜 RAG를 선택했는가?

| 기준 | RAG | 파인튜닝 |
|------|-----|---------|
| 문서 업데이트 반영 | 즉시 가능 | 재학습 필요 |
| 출처 추적 | 가능 | 불가능 |
| 초기 구축 비용 | 낮음 | 높음 (데이터 + GPU) |
| 적합한 상황 | 문서 기반 QA | 특정 스타일/도메인 학습 |

이 프로젝트는 **사용자가 임의의 문서를 업로드**하는 시나리오이므로 RAG가 유일한 현실적 선택입니다. 파인튜닝은 RAG로 커버되지 않는 응답 스타일 개선 단계에서 보완적으로 활용할 수 있습니다.

### 임베딩 모델 선택: API → 로컬

초기에는 HuggingFace Inference API(`BAAI/bge-m3`)를 사용했으나, 무료 엔드포인트 폐지(410 Gone)로 인해 `sentence-transformers` 로컬 실행으로 전환했습니다.

결과적으로 **네트워크 왕복 제거로 임베딩 속도가 향상**되었고, API 비용과 장애 의존성도 함께 제거되었습니다.

### 청킹 전략

```
문단 우선 분할 → 크기 초과 시 문자 단위 강제 분할
chunk_size=500 / overlap=50
```

overlap을 두는 이유는 청크 경계에서 문맥이 잘리는 것을 방지하기 위해서입니다. 예를 들어, "결론은 ~~이다"라는 문장이 앞 청크와 뒤 청크 모두에 포함되어야 두 검색 결과 모두 완전한 맥락을 제공합니다.

### 메타데이터 설계 (ChromaDB)

ChromaDB는 `None` 타입 메타데이터를 허용하지 않습니다 (`str`, `int`, `float`, `bool` 만 허용). 이 제약을 인지하고 텍스트 파일의 page 값을 `0`으로, PDF는 실제 페이지 번호를 저장하도록 설계했습니다.

---

## 🔧 향후 개선 사항

- [ ] **스트리밍 응답** (SSE) — 답변을 토큰 단위로 실시간 출력
- [ ] **Reranking** — Cross-Encoder로 검색 결과 재순위화하여 정확도 향상
- [ ] **응답 캐싱** — 동일 질문에 대한 Redis 캐시로 API 비용 절감
- [ ] **PDF 고급 파싱** — Upstage Document Parse API 연동으로 표/이미지 처리
- [ ] **PostgreSQL 마이그레이션** — 다중 사용자 환경 대응
- [ ] **사용자 인증** — 세션별 문서 격리
- [ ] **RAG 평가 지표** — RAGAS 프레임워크로 Precision@K, 응답 관련성 측정

---

## 👨‍💻 개발자

| 항목 | 내용 |
|------|------|
| 역할 | 기획 / 아키텍처 설계 / 백엔드 / 프론트엔드 / AI 파이프라인 |
| 기간 | 개인 프로젝트 |
| 주요 의사결정 | RAG 구조 설계, 레이어 분리 아키텍처, 임베딩 로컬화, 비동기 DB 도입 |

---

## 📜 라이선스

MIT License
