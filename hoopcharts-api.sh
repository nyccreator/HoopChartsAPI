#!/bin/bash

# Start Flask app
gunicorn app:app &

# Start ngrok
ngrok http --domain=normal-dinosaur-yearly.ngrok-free.app 8000

