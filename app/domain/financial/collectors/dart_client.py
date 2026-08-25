import asyncio

import httpx

DART_BASE = "https://opendart.fss.or.kr/api"

class DartApiError(Exception):
    def __init__(self, status: str, message: str):
        self.status = status
        super().__init__(f"[{status}] {message}")

async def dart_get(endpoint: str, params: dict, max_retries: int = 3) -> dict:
    status, msg = None, None
    for attempt in range(max_retries):
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.get(f"{DART_BASE}/{endpoint}", params=params)
        data = resp.json()
        status = data.get("status")
        msg = data.get("message", "")

        if status in ("000", "013"):
            return data
        if status == "020":
            await asyncio.sleep(2 ** attempt)
            continue
        raise DartApiError(status, msg)
    raise DartApiError(status, "요청 제한 초과 - 재시도 실패")