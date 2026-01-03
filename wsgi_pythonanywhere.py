import os
import sys

# Add your project directory to sys.path
project_home = '/home/yourusername/hotel_demo_wednesday_backup_2025-11-13'  # Replace with your actual path
if project_home not in sys.path:
    sys.path.insert(0, project_home)

# Set environment variable to use production settings
os.environ['DJANGO_SETTINGS_MODULE'] = 'hotel_mgmt.settings_production'

# Activate virtual environment
activate_this = '/home/yourusername/.virtualenvs/hotel_env/bin/activate_this.py'  # Replace with your venv path
exec(open(activate_this).read(), {'__file__': activate_this})

from django.core.wsgi import get_wsgi_application
application = get_wsgi_application()