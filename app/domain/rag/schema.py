"""rag 내부 데이터 구조 정의"""
from datetime import date

from pydantic import BaseModel, ConfigDict


class ReportEvidence(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    corp_code: str
    corp_name: str
    stock_code: str | None

    chunk_id: int
    report_id: int
    report_name: str
    filing_date: date | None

    major_section: str | None
    minor_section: str | None
    chunk_order: int

    content: str
    similarity: float


class PurposeEvidence(BaseModel):
    purpose: str
    query: str
    chunks: list[ReportEvidence]


class CompanyRagEvidence(BaseModel):
    corp_code: str
    corp_name: str | None = None
    stock_code: str | None = None
    searches: list[PurposeEvidence]