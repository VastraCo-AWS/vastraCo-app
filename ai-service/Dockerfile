FROM python:3.12-slim

RUN apt-get update && apt-get upgrade -y --no-install-recommends && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY src/ ./src/
#test
RUN groupadd -r -g 1000 app && useradd -r -u 1000 -g app app
USER app

EXPOSE 3004
CMD ["uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "3004"]
