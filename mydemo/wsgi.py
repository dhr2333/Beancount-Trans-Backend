"""
WSGI config for mydemo project.

It exposes the WSGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/4.0/howto/deployment/wsgi/
"""

import os

from django.core.wsgi import get_wsgi_application

# os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'mydemo.settings')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'conf.prod')

application = get_wsgi_application()
