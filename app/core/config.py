from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # App
    app_name: str = "RAG Chatbot"
    app_version: str = "0.1.0"
    debug: bool = False
    auth_token_hashes: dict[str, str] = {}
    raw_path: str = "./data/raw"
    max_upload_bytes: int = 10 * 1024 * 1024
    max_document_chars: int = 1_000_000
    max_pdf_pages: int = 200

    # Upstage
    upstage_api_key: str = ""
    upstage_base_url: str = "https://api.upstage.ai/v1/solar"

    # HuggingFace
    huggingface_api_key: str = ""
    huggingface_embedding_model: str = "BAAI/bge-m3"

    # Database
    database_url: str = "sqlite+aiosqlite:///./data/chatbot.db"

    # Vector DB
    vectordb_path: str = "./data/vectordb"
    vectordb_collection: str = "documents"

    # RAG
    rag_top_k: int = 5
    rag_score_threshold: float = 0.7
    rag_chunk_size: int = 500
    rag_chunk_overlap: int = 50

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


# 앱 전체에서 import해서 사용하는 싱글톤 설정 객체
settings = Settings()
