import os

# LinDA datasources API host IP address
API_HOST = "127.0.0.1"
SITE_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
MEDIA_ROOT = os.path.join(SITE_ROOT, 'media')
MEDIA_URL = '/media/'