import hashlib

from app.domain.portfolio.schema.llm_schema import LlmAnalysisResult

_CACHE_TTL_SECONDS = 60 * 60 * 24
_cache: dict[str, tuple[LlmAnalysisResult, float]] = {}

def _make_cache_key(analysis_prompt: str, reason_prompt: str) -> str:
    combined = analysis_prompt + "||" + reason_prompt
    return hashlib.sha256(combined.encode("utf-8")).hexdigest()