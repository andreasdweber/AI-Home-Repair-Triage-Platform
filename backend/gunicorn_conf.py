# Gunicorn configuration file for production deployment on Render
# https://docs.gunicorn.org/en/stable/settings.html

import multiprocessing

# Bind to 0.0.0.0 to allow external connections
bind = "0.0.0.0:8000"

# Number of worker processes
# Render recommends 2-4 workers for most apps
workers = multiprocessing.cpu_count() * 2 + 1

# Worker class - use uvicorn for async support with FastAPI
worker_class = "uvicorn.workers.UvicornWorker"

# Timeout for worker processes (seconds)
timeout = 120

# Keep-alive connections
keepalive = 5

# Logging
accesslog = "-"  # Log to stdout
errorlog = "-"   # Log to stderr
loglevel = "info"

# Graceful timeout for worker restart
graceful_timeout = 30

# Maximum requests per worker before restart (prevents memory leaks)
max_requests = 1000
max_requests_jitter = 50
