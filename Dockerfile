FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc libpq-dev \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

RUN python manage.py collectstatic --noinput

# Render assigns the actual listen port via $PORT at container start (not a
# fixed value like 8000), and runserver is Django's single-threaded dev
# server — not fit for production traffic. Gunicorn + the shell form of CMD
# (so $PORT and the migrate step run) match what render.yaml's native-runtime
# path uses. Migrations run here (container start) rather than at image build
# time, since the database isn't reachable during the build step.
EXPOSE 8000
CMD python manage.py migrate --noinput && gunicorn smartserve.wsgi:application --bind 0.0.0.0:${PORT:-8000}
