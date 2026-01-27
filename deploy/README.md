# Deployment notes (Gunicorn + Nginx)

Edit the paths and user/group in the service and nginx config to match your server layout.

- Gunicorn service: `deploy/gunicorn.service`
- Gunicorn config: `deploy/gunicorn.conf.py`
- Nginx site: `deploy/nginx.conf`

Typical steps on Ubuntu:

1. Copy configs to the system locations:
   - `/etc/systemd/system/gunicorn.service`
   - `/etc/nginx/sites-available/adn4research`
2. Enable nginx site and reload:
   - `sudo ln -s /etc/nginx/sites-available/adn4research /etc/nginx/sites-enabled/`
   - `sudo nginx -t && sudo systemctl reload nginx`
3. Enable and start gunicorn:
   - `sudo systemctl daemon-reload`
   - `sudo systemctl enable --now gunicorn`
4. Collect static files (in your venv):
   - `python manage.py collectstatic`

Make sure `.env` has `DEBUG=False`, `ALLOWED_HOSTS`, and `CSRF_TRUSTED_ORIGINS` set correctly.
