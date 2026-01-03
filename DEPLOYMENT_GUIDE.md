# Hotel Management System - PythonAnywhere Deployment Guide

## 🚀 Complete Deployment Steps

### **Step 1: Sign Up for PythonAnywhere**
1. Go to [www.pythonanywhere.com](https://www.pythonanywhere.com)
2. Create a free or paid account
3. Note your username (you'll need this)

### **Step 2: Upload Your Code**

#### Option A: Via GitHub (Recommended)
1. First, push all your local changes to GitHub:
   ```bash
   git add .
   git commit -m "Add PythonAnywhere deployment files"
   git push origin main
   ```

2. On PythonAnywhere, open a Bash console and run:
   ```bash
   git clone https://github.com/gemi-dot/hotel-management-demo.git hotel_project
   cd hotel_project
   ```

#### Option B: Direct Upload
1. Use PythonAnywhere's file browser to upload your project files
2. Upload to `/home/yourusername/hotel_project/`

### **Step 3: Set Up Virtual Environment**
In the PythonAnywhere Bash console:
```bash
mkvirtualenv --python=/usr/bin/python3.10 hotel_env
pip install django
pip install bleach
pip install openpyxl
pip install -r requirements.txt
```

### **Step 4: Configure Database**
```bash
cd /home/yourusername/hotel_project
python manage.py makemigrations
python manage.py migrate
python manage.py collectstatic --noinput
python manage.py createsuperuser
```

### **Step 5: Web App Configuration**
1. Go to PythonAnywhere Dashboard → Web tab
2. Click "Add a new web app"
3. Choose "Manual configuration"
4. Select Python 3.10

#### Configure these settings:
- **Source code**: `/home/yourusername/hotel_project`
- **Working directory**: `/home/yourusername/hotel_project`
- **WSGI file**: `/home/yourusername/hotel_project/wsgi_pythonanywhere.py`
- **Virtualenv**: `/home/yourusername/.virtualenvs/hotel_env`

### **Step 6: Update Settings**
Edit `settings_production.py` and replace:
- `yourusername` with your actual PythonAnywhere username
- Generate a new SECRET_KEY for production

### **Step 7: Static Files Configuration**
In Web tab → Static files section:
- **URL**: `/static/`
- **Directory**: `/home/yourusername/hotel_project/staticfiles/`

### **Step 8: Test and Launch**
1. Click "Reload" in Web tab
2. Visit `https://yourusername.pythonanywhere.com`
3. Test all functionality

## 🔧 Troubleshooting

### Common Issues:
1. **500 Error**: Check error logs in Web tab
2. **Static files not loading**: Run `python manage.py collectstatic` again
3. **Database issues**: Ensure migrations are run

### Useful Commands:
```bash
# Check logs
tail -f /var/log/yourusername.pythonanywhere.com.error.log

# Update code from GitHub
cd /home/yourusername/hotel_project
git pull origin main

# Restart app
# Go to Web tab and click Reload
```

## 📱 Post-Deployment Tasks

1. **Create test data**:
   ```bash
   python manage.py shell
   # Create rooms, guests, bookings for testing
   ```

2. **Fix room statuses**:
   ```bash
   python manage.py sync_room_status
   ```

3. **Fix booking totals**:
   ```bash
   python manage.py fix_booking_totals
   ```

4. **Test all features**:
   - Room management
   - Booking creation
   - Payment processing
   - Reports generation

## 🔐 Security Checklist

- [ ] Change SECRET_KEY in production
- [ ] Set DEBUG = False
- [ ] Configure proper ALLOWED_HOSTS
- [ ] Set up HTTPS (included with PythonAnywhere)
- [ ] Create strong admin passwords
- [ ] Regular database backups

## 📊 Monitoring

- Check error logs regularly
- Monitor performance in PythonAnywhere dashboard
- Set up alerts for critical issues

Your hotel management system will be live at:
**https://yourusername.pythonanywhere.com**