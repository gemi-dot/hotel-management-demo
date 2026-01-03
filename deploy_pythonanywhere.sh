#!/bin/bash
# PythonAnywhere Deployment Script

echo "🚀 Starting Hotel Management System deployment to PythonAnywhere..."

# Set variables (customize these)
USERNAME="yourusername"  # Replace with your PythonAnywhere username
PROJECT_NAME="hotel_demo_wednesday_backup_2025-11-13"
VENV_NAME="hotel_env"

echo "📁 Setting up directories..."
mkdir -p /home/$USERNAME/$PROJECT_NAME
cd /home/$USERNAME/$PROJECT_NAME

echo "🔄 Cloning/updating code from GitHub..."
# If first time deployment
# git clone https://github.com/gemi-dot/hotel-management-demo.git .
# If updating existing deployment
git pull origin main

echo "🐍 Creating virtual environment..."
mkvirtualenv --python=/usr/bin/python3.10 $VENV_NAME
workon $VENV_NAME

echo "📦 Installing Python packages..."
pip install -r requirements.txt

echo "🔧 Running Django management commands..."
python manage.py makemigrations
python manage.py migrate
python manage.py collectstatic --noinput

echo "👤 Creating superuser (if needed)..."
# python manage.py createsuperuser --noinput --username admin --email admin@example.com

echo "🔄 Fixing room statuses..."
python manage.py sync_room_status

echo "🔄 Fixing booking totals..."
python manage.py fix_booking_totals

echo "✅ Deployment completed!"
echo "📋 Next steps:"
echo "1. Go to PythonAnywhere Web tab"
echo "2. Set source code directory: /home/$USERNAME/$PROJECT_NAME"
echo "3. Set working directory: /home/$USERNAME/$PROJECT_NAME"
echo "4. Set WSGI file: /home/$USERNAME/$PROJECT_NAME/wsgi_pythonanywhere.py"
echo "5. Set virtualenv: /home/$USERNAME/.virtualenvs/$VENV_NAME"
echo "6. Reload your web app"