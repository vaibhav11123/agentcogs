FROM python:3.12-slim
RUN pip install --no-cache-dir --upgrade pip

# Ingest imports the SDK ledger. The image build context is the repo root.
WORKDIR /sdk
COPY pyproject.toml PYPI.md LICENSE ./
COPY src ./src
RUN pip install --no-cache-dir .

WORKDIR /app
COPY backend/pyproject.toml ./
RUN pip install --no-cache-dir -e .
COPY backend/ ./
EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "2"]
