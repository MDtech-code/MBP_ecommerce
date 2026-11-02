runserver:
	python manage.py runserver_plus --cert-file ../certs/localhost.pem --key-file ../certs/localhost-key.pem 0.0.0.0:8000

celery:
	python -m celery -A config worker --pool=threads --loglevel=debug

beat:
	python -m celery -A config beat --loglevel=info

shell:
	python manage.py shell_plus

migrate:
	python manage.py migrate

makemigrations:
	python manage.py makemigrations