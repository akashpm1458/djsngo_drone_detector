# Troubleshooting Guide

## Common Issues and Solutions

### 1. Dropdown Not Showing in Edge Client

**Symptoms:**
- Detection method dropdown is not visible on the edge client page
- Cannot select between ML Model and Signal Processing

**Solutions:**

1. **Clear browser cache:**
   - Press `Ctrl+Shift+R` (Windows/Linux) or `Cmd+Shift+R` (Mac) to hard refresh
   - Or clear browser cache completely

2. **Check browser console:**
   - Open browser developer tools (F12)
   - Check Console tab for JavaScript errors
   - Look for any red error messages

3. **Verify the page is loading correctly:**
   - Navigate to: http://localhost:8000/edge_client/detect
   - Check if the "Detection Method" section is visible
   - The dropdown should be in a light blue box at the top

4. **Check if detection config API is working:**
   - Open browser console (F12)
   - Run: `fetch('/edge_client/api/detection-config/active').then(r => r.json()).then(console.log)`
   - Should return JSON with status and config data

5. **Restart Django server:**
   ```bash
   # Stop the server (Ctrl+C)
   # Then restart
   ./start_django.sh
   ```

### 2. Dashboard Not Opening

**Symptoms:**
- Getting 404 error when accessing dashboard
- Dashboard page is blank
- URL not found error

**Solutions:**

1. **Check the correct URL:**
   - Dashboard should be at: **http://localhost:8000/api/dashboard/**
   - Alternative (redirects): http://localhost:8000/monitoring/dashboard/

2. **Verify URL routing:**
   ```bash
   # Check if URLs are registered
   python manage.py show_urls | grep dashboard
   ```

3. **Check for errors in Django logs:**
   - Look at the terminal where Django is running
   - Check for any error messages when accessing the dashboard

4. **Verify migrations are applied:**
   ```bash
   python manage.py migrate
   ```

5. **Check if monitoring app is installed:**
   - Verify `monitoring` is in `INSTALLED_APPS` in `settings.py`

6. **Clear browser cache and try again**

### 3. Detection Config API Not Working

**Symptoms:**
- Dropdown shows "Loading..." but never updates
- JavaScript errors in console about API calls

**Solutions:**

1. **Check if detection configs exist:**
   ```bash
   python manage.py shell
   ```
   Then in Python shell:
   ```python
   from core.models import DetectionConfig
   DetectionConfig.objects.all()
   ```

2. **Initialize detection configs:**
   ```bash
   python manage.py init_detection_configs
   ```

3. **Check API endpoint directly:**
   - Open: http://localhost:8000/edge_client/api/detection-config/active
   - Should return JSON, not an error page

4. **Verify CORS settings** (if accessing from different domain):
   - Check `CORS_ALLOWED_ORIGINS` in `settings.py`

### 4. ML Model Not Working

**Symptoms:**
- ML Model option selected but signal processing is used instead
- Error messages about ONNX model

**Solutions:**

1. **Check if onnxruntime is installed:**
   ```bash
   pip list | grep onnxruntime
   ```
   If not installed:
   ```bash
   pip install onnxruntime
   ```

2. **Verify model file exists:**
   - Check if `drone_33d_mlp.onnx` is in the `django_echoshield` directory
   - Or specify full path in detection config

3. **Check Django logs:**
   - Look for error messages about model loading
   - Check `logs/echoshield.log` if logging to file

4. **Create ML model config:**
   - Go to Django admin: http://localhost:8000/admin/
   - Navigate to Detection Configurations
   - Create new config with:
     - Method: "ML Model (ONNX)"
     - Use ML Model: Checked
     - ML Model Path: `drone_33d_mlp.onnx`
   - Set as active

### 5. Static Files Not Loading

**Symptoms:**
- CSS not applied
- JavaScript not working
- Images missing

**Solutions:**

1. **Collect static files:**
   ```bash
   python manage.py collectstatic --noinput
   ```

2. **Check STATIC_ROOT in settings.py:**
   - Should point to a directory where static files are collected

3. **In development, ensure DEBUG=True:**
   - Django serves static files automatically in DEBUG mode

4. **Check STATIC_URL:**
   - Should be `/static/` in settings.py

### 6. Database Errors

**Symptoms:**
- Migration errors
- Database locked errors
- Model errors

**Solutions:**

1. **Run migrations:**
   ```bash
   python manage.py migrate
   ```

2. **Check database file permissions:**
   - Ensure `db.sqlite3` is writable

3. **Reset database (WARNING: Deletes all data):**
   ```bash
   rm db.sqlite3
   python manage.py migrate
   python manage.py init_detection_configs
   ```

### 7. Redis/Celery Issues

**Symptoms:**
- Celery tasks not running
- Background processing not working

**Solutions:**

1. **Check if Redis is running:**
   ```bash
   redis-cli ping
   # Should return: PONG
   ```

2. **Start Redis if not running:**
   ```bash
   redis-server
   ```

3. **Check Celery worker:**
   ```bash
   celery -A echoshield inspect active
   ```

4. **Restart Celery:**
   ```bash
   ./start_celery.sh
   ```

## Debugging Tips

### Enable Debug Mode

1. **Check Django settings:**
   - Ensure `DEBUG=True` in `.env` or `settings.py`
   - This shows detailed error pages

2. **Check browser console:**
   - Open Developer Tools (F12)
   - Check Console for JavaScript errors
   - Check Network tab for failed API calls

3. **Check Django logs:**
   - Look at terminal output where Django is running
   - Check `logs/echoshield.log` if file logging is enabled

### Common Error Messages

**"No active configuration found":**
- Run: `python manage.py init_detection_configs`
- Or create one via Django admin

**"Module not found":**
- Activate virtual environment: `source venv/bin/activate`
- Install dependencies: `pip install -r requirements.txt`

**"Port 8000 already in use":**
- Stop other Django processes
- Or change port in `start_django.sh`

**"CSRF verification failed":**
- Ensure you're accessing via the correct URL
- Check CSRF settings in `settings.py`

## Getting Help

If issues persist:

1. Check the logs:
   - Django server logs (terminal output)
   - Browser console (F12)
   - `logs/echoshield.log` file

2. Verify setup:
   ```bash
   ./check_setup.sh
   ```

3. Review the setup guide:
   - See `SETUP_GUIDE.md` for detailed setup instructions

4. Check URL patterns:
   ```bash
   python manage.py show_urls
   ```

