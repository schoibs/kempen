FROM python:3.12.11-slim-bookworm

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

RUN addgroup --system campaign \
    && adduser --system --ingroup campaign campaign

COPY requirements.txt ./
RUN pip install --no-cache-dir --requirement requirements.txt

COPY alembic.ini app_config.py infrastructure.py logging_config.py ./
COPY api ./api
COPY campaign_agents ./campaign_agents
COPY clients ./clients
COPY domain ./domain
COPY persistence ./persistence
COPY services ./services
COPY storage ./storage
COPY workers ./workers

USER campaign

EXPOSE 8000

CMD ["uvicorn", "api.app:app", "--host", "0.0.0.0", "--port", "8000"]
