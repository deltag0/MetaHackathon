FROM python:3.13-slim

WORKDIR /app

RUN pip install uv

COPY pyproject.toml .
COPY uv.lock* .

RUN uv sync --no-dev

COPY . .

EXPOSE 5000

CMD ["uv", "run", "python", "run.py"]
