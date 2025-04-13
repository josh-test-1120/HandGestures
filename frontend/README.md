# Depenency installs
Ensure that all project dependencies are loaded into Python
by running the following command:

pip install -r requirements.txt

# Django Scaffold
Currently, you can run the scaffold.py file to setup a new scaffold,
but this was for legacy Django 1.x, and needs some updates for 2.x

# Django Build
Run the following commands to create the database and other build parts
associated with running the server

python manage.py migrate

# Django Server Start
Run the following command to start the Django Server

python manage.py runserver
