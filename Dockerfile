FROM mcr.microsoft.com/playwright/python:v1.52.0-noble
WORKDIR /app
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 KAMY_DATA_DIR=/data
COPY requirements.txt requirements-browser.txt ./
RUN pip install --no-cache-dir -r requirements.txt -r requirements-browser.txt
COPY app.py extensions.py ./
COPY static ./static
COPY assets ./assets
RUN useradd -m -u 10001 kamy && mkdir -p /data/workspaces && chown -R kamy:kamy /app /data
USER kamy
EXPOSE 8000
CMD ["uvicorn","app:app","--host","0.0.0.0","--port","8000"]
