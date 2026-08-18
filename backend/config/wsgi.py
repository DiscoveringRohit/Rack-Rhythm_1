"""
WSGI config for config project.

It exposes the WSGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/6.1/howto/deployment/wsgi/
"""

import os
from django.core.wsgi import get_wsgi_application

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')

django_app = get_wsgi_application()

def application(environ, start_response):
    request_method = environ.get('REQUEST_METHOD', '').upper()
    origin = environ.get('HTTP_ORIGIN') or environ.get('HTTP_REFERER') or '*'

    if request_method == 'OPTIONS':
        status = '200 OK'
        headers = [
            ('Content-Type', 'text/plain'),
            ('Content-Length', '0'),
            ('Access-Control-Allow-Origin', origin),
            ('Access-Control-Allow-Methods', 'GET, POST, PUT, PATCH, DELETE, OPTIONS'),
            ('Access-Control-Allow-Headers', 'Accept, Accept-Encoding, Authorization, Content-Type, DNT, Origin, User-Agent, X-CSRFToken, X-Requested-With'),
            ('Access-Control-Allow-Credentials', 'true'),
            ('Access-Control-Max-Age', '86400'),
        ]
        start_response(status, headers)
        return [b'']

    def custom_start_response(status, headers, exc_info=None):
        new_headers = list(headers)
        has_cors = any(h[0].lower() == 'access-control-allow-origin' for h in new_headers)
        if not has_cors and origin:
            new_headers.append(('Access-Control-Allow-Origin', origin))
            new_headers.append(('Access-Control-Allow-Credentials', 'true'))
            new_headers.append(('Access-Control-Allow-Headers', 'Accept, Accept-Encoding, Authorization, Content-Type, DNT, Origin, User-Agent, X-CSRFToken, X-Requested-With'))
            new_headers.append(('Access-Control-Allow-Methods', 'GET, POST, PUT, PATCH, DELETE, OPTIONS'))
        return start_response(status, new_headers, exc_info)

    return django_app(environ, custom_start_response)
