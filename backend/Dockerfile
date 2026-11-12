FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY peoplepilot ./peoplepilot
COPY migrations ./migrations
COPY alembic.ini ./alembic.ini
COPY alembic ./alembic

# Run as an unprivileged user.
RUN useradd --create-home --uid 10001 pp
USER pp
