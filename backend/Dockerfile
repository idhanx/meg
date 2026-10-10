FROM python:3.13-slim
WORKDIR /app
COPY pyproject.toml ./pyproject.toml
COPY backend/meg ./backend/meg
RUN pip install .
CMD ["uvicorn", "meg.api:app", "--host", "0.0.0.0", "--port", "8000"]
