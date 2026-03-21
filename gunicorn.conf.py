# gunicorn.conf.py - MINIMAL MEMORY SETUP
bind = "0.0.0.0:10000"
workers = 1
threads = 1
timeout = 60
worker_class = "sync"
max_requests = 200
max_requests_jitter = 50