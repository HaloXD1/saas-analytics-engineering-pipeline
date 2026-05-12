FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

COPY pyproject.toml README.md ./
COPY app ./app
COPY config ./config
COPY docs ./docs
COPY src ./src
COPY tests ./tests

RUN python -m pip install --upgrade pip \
    && python -m pip install -e ".[dev]"

EXPOSE 8501

CMD ["streamlit", "run", "app/streamlit_dashboard.py", "--server.address=0.0.0.0", "--server.port=8501"]
