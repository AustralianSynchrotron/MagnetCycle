#!/bin/bash
source venv/bin/activate
gunicorn -k flask_sockets.worker main:app
