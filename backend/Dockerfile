FROM python:3.11-slim
RUN apt-get update && apt-get install -y --no-install-recommends ffmpeg && rm -rf /var/lib/apt/lists/*
RUN useradd -m -u 1000 user
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir torch --index-url https://download.pytorch.org/whl/cpu \
 && pip install --no-cache-dir -r requirements.txt
COPY --chown=user . .
RUN mkdir -p uploads && chown -R user /app
USER user
ENV PORT=7860 HF_HOME=/app/.cache
EXPOSE 7860
CMD uvicorn app.main:app --host 0.0.0.0 --port ${PORT}
