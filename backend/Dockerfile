FROM python:3.11-slim
WORKDIR /app
COPY pyproject.toml poetry.lock* ./
RUN pip install --no-cache-dir poetry && poetry install --only main --no-root --no-cache
COPY . .
EXPOSE 8000
CMD ["poetry", "run", "start"]
