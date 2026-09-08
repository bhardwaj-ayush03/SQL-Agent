from pydantic_settings import BaseSettings, SettingsConfigDict
import os
from dotenv import load_dotenv
load_dotenv()

class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # --- LLM providers ---
    groq_api_key: str = os.getenv('GROQ_API_KEY')
    groq_model: str = "llama-3.3-70b-versatile"

    openrouter_api_key: str = os.getenv('OPEN_ROUTER')
    openrouter_model: str = "meta-llama/llama-3.3-70b-instruct:free"

    # --- Retry / correction ---
    max_sql_retries: int = 2

    # --- DuckDB ---
    duckdb_path: str = ":memory:"  

    # --- Embeddings ---
    embedding_model: str = "sentence-transformers/all-MiniLM-L6-v2"

    # --- App ---
    app_env: str = "dev"


settings = Settings()