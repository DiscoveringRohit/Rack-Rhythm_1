import os
import sys

# Ensure backend directory is in sys.path
BASE_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'backend')
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')

from django.core.wsgi import get_wsgi_application
application = get_wsgi_application()
