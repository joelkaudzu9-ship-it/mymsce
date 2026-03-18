# gunicorn.conf.py
import multiprocessing

# Bind to host and port
bind = "0.0.0.0:10000"

# Number of workers
workers = multiprocessing.cpu_count() * 2 + 1

# Increase timeout to 120 seconds (handles email sending)
timeout = 120

# Log level
loglevel = "info"

# Access log
accesslog = "-"
errorlog = "-"