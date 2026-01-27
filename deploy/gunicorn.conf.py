bind = "127.0.0.1:8000"
workers = 3
timeout = 120
loglevel = "info"
accesslog = "-"
errorlog = "-"
preload_app = True
wsgi_app = "config.wsgi:application"
