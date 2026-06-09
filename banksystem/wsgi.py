import os
from pathlib import Path

from django.core.wsgi import get_wsgi_application
from whitenoise import WhiteNoise

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'banksystem.settings')

_django_app = get_wsgi_application()

FRONTEND_DIR = str(Path(__file__).resolve().parent.parent / 'Front-end')
application = WhiteNoise(_django_app, root=FRONTEND_DIR, prefix='fe')
