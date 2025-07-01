#!/bin/sh
NAME="beancount-trans" # Name of the application
DJANGODIR=/code/beancount-trans # Django project directory

echo "Starting $NAME as `whoami`"

cd $DJANGODIR

export PYTHONPATH=$DJANGODIR:$PYTHONPATH

celery -A project worker --beat --loglevel=info
