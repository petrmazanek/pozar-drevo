FROM python:3.12-slim

WORKDIR /app

# Instalace závislostí
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Kopírování aplikace
COPY app.py .
COPY src/ ./src/
COPY data/ ./data/
COPY .streamlit/ ./.streamlit/

# Port
EXPOSE 8501

# Healthcheck
HEALTHCHECK CMD curl --fail http://localhost:8501/_stcore/health || exit 1

# Spuštění
ENTRYPOINT ["streamlit", "run", "app.py", "--server.port=8501", "--server.address=0.0.0.0", "--server.headless=true"]
