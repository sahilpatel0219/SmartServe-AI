release: python manage.py migrate
web: gunicorn smartserve.wsgi:application --bind 0.0.0.0:$PORT
