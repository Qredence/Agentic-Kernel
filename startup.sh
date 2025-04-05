#!/bin/bash
gunicorn --bind=0.0.0.0 --timeout 600 --worker-class=uvicorn.workers.UvicornWorker 'chainlit.server:run_chainlit()'
