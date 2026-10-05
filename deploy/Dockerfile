FROM python:3.12-slim
WORKDIR /app
RUN pip install --no-cache-dir fastapi uvicorn
COPY server.py theme.css index.html browse.html timeline.html kg.html archive.html hypothesis.html arbitration.html /app/
ENV GENSHIN_BASE=/data
VOLUME ["/data"]
EXPOSE 8000
CMD ["uvicorn", "server:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "1"]
