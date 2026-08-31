FROM python:3.11-slim AS builder

WORKDIR /build

# 의존성만 먼저 설치해서 소스 변경 시에도 이 레이어는 캐시되게 함
# (pyproject.toml의 packages.find가 app*만 잡으므로 app/만 있으면 설치 가능)
COPY pyproject.toml ./
COPY app ./app
RUN pip install --no-cache-dir --user .


FROM python:3.11-slim

WORKDIR /app

COPY --from=builder /root/.local /root/.local
ENV PATH=/root/.local/bin:$PATH \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app

# batch, alembic은 setuptools 패키징 대상이 아니라서 소스 그대로 복사해서 실행
COPY app ./app
COPY batch ./batch
COPY alembic ./alembic
COPY alembic.ini ./

EXPOSE 8000

# 기본은 API 서버. 배치 워커 컨테이너는 docker-compose에서 command를 오버라이드해서
# 같은 이미지를 그대로 재사용함 (python -m batch.worker).
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
