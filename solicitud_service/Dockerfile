FROM python:3.10-slim

WORKDIR /app

COPY . /app
RUN pip install --no-cache-dir fastapi uvicorn requests

EXPOSE 9004
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "9000"]
