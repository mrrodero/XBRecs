export DJANGOPORT := 8001

CMD = python3 manage.py
APP = application

runserver:
	$(CMD) runserver $(DJANGOPORT)

update_models:
	$(CMD) makemigrations $(APP)
	$(CMD) migrate

create_super_user:
	$(CMD) shell -c "from django.contrib.auth import get_user_model; User = get_user_model(); User.objects.create_superuser('alumnodb', 'admin@myproject.com', 'alumnodb')"

populate:
	$(CMD) populate

test_app:
	$(CMD) test application.tests

rebuild_index:
	$(CMD) rebuild_index

init_db:
	dropdb -U alumnodb -h localhost tfg
	createdb -U alumnodb -h localhost tfg
	make update_models
	make create_super_user
	make populate
	make test_app