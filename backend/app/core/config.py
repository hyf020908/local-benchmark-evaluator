from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv


PROJECT_ROOT = Path(__file__).resolve().parents[3]
BACKEND_ROOT = PROJECT_ROOT / "backend"
BENCHMARKS_ROOT = PROJECT_ROOT.parent

load_dotenv(PROJECT_ROOT / ".env")


class Settings:
    app_name: str = os.getenv("APP_NAME", "Local Benchmark Evaluator")
    app_env: str = os.getenv("APP_ENV", "development")
    host: str = os.getenv("BACKEND_HOST", "0.0.0.0")
    port: int = int(os.getenv("BACKEND_PORT", "8000"))
    cors_origins: list[str] = [
        item.strip()
        for item in os.getenv(
            "CORS_ORIGINS",
            "http://127.0.0.1:5173,http://localhost:5173",
        ).split(",")
        if item.strip()
    ]
    outputs_dir: Path = Path(os.getenv("OUTPUTS_DIR", PROJECT_ROOT / "outputs"))
    benchmarks_root: Path = Path(os.getenv("BENCHMARKS_ROOT", BENCHMARKS_ROOT))
    hf_cache_dir: Path = Path(os.getenv("HF_CACHE_DIR", PROJECT_ROOT / ".cache" / "huggingface"))


settings = Settings()
settings.outputs_dir.mkdir(parents=True, exist_ok=True)
settings.hf_cache_dir.mkdir(parents=True, exist_ok=True)
# Keep Hugging Face cache inside the project tree so the runtime layout stays self-contained.
os.environ.setdefault("HF_HOME", str(settings.hf_cache_dir))
os.environ.setdefault("HUGGINGFACE_HUB_CACHE", str(settings.hf_cache_dir / "hub"))
os.environ.setdefault("HF_HUB_CACHE", str(settings.hf_cache_dir / "hub"))
os.environ.setdefault("HF_DATASETS_CACHE", str(settings.hf_cache_dir / "datasets"))
