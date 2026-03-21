# gunicorn.conf.py
import sys
import os

# Print Python path for debugging
print("=" * 50)
print("Gunicorn starting...")
print(f"Python version: {sys.version}")
print(f"Current directory: {os.getcwd()}")
print(f"Files in current directory: {os.listdir('.')}")
print("=" * 50)

bind = "0.0.0.0:10000"
workers = 1
threads = 1
timeout = 60
worker_class = "sync"
max_requests = 200
max_requests_jitter = 50

# Add error logging
errorlog = "-"
accesslog = "-"
loglevel = "debug"