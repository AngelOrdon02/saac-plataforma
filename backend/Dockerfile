FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app ./app
COPY reglas ./reglas
COPY conocimiento ./conocimiento
COPY scripts ./scripts

# Usuario sin privilegios
RUN useradd --create-home saac
USER saac

EXPOSE 8000
# Indexa la base de conocimiento (solo los documentos que cambiaron) y levanta la API
CMD ["sh", "-c", "python -m scripts.indexar_conocimiento && uvicorn app.main:app --host 0.0.0.0 --port 8000 --proxy-headers"]
