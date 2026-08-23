from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.domain.company.dart_client import DartAPIError
from app.domain.company.kospi_client import KospiMasterError
from app.domain.company.service import synchronize_dart_companies

router = APIRouter(
    prefix="/companies",
    tags=["companies"],
)


@router.post("/sync/dart")
async def sync_dart_companies(
    session: Annotated[AsyncSession, Depends(get_db)],
):
    try:
        result = await synchronize_dart_companies(session)
    except (DartAPIError, KospiMasterError) as exc:
        await session.rollback()
        raise HTTPException(
            status_code=502,
            detail=str(exc),
        ) from exc
    except Exception:
        await session.rollback()
        raise

    return {
        "message": "KOSPI 기업 동기화가 완료되었습니다.",
        **result,
    }
