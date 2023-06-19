#!/usr/bin/env bash
NAME="beancount-trans" # Name of the application
#DJANGODIR=/code/beancount-trans # Django project directory
DJANGODIR=/code/beancount-trans
USER=root # the user to run as
GROUP=root # the group to run as
NUM_WORKERS=1 # how many worker processes should Gunicorn spawn
#DJANGO_SETTINGS_MODULE=djangoblog.settings # which settings file should Django use
DJANGO_WSGI_MODULE=mydemo.wsgi # WSGI module name


echo "Starting $NAME as `whoami`"

# Activate the virtual environment
cd $DJANGODIR

export PYTHONPATH=$DJANGODIR:$PYTHONPATH
#pip install -Ur requirements.txt -i http://pypi.douban.com/simple/  --trusted-host pypi.douban.com && \
#        pip install gunicorn  -i http://pypi.douban.com/simple/ --trusted-host pypi.douban.com
python manage.py makemigrations && \
  python manage.py migrate && \
  python manage.py collectstatic --noinput  && \
# Start your Django Unicorn
# Programs meant to be run under supervisor should not daemonize themselves (do not use --daemon)
exec gunicorn ${DJANGO_WSGI_MODULE}:application \
--name $NAME \
--workers $NUM_WORKERS \
--user=$USER --group=$GROUP \
--bind 0.0.0.0:8000 \
--log-level=debug \
--log-file=- \
--worker-class gevent \
--threads 4