#!/bin/bash

# Start Flask app
gunicorn app:app &

# Store the PID of the last background process (gunicorn)
pid1=$!

# Start ngrok
ngrok http --region=us --hostname=normal-dinosaur-yearly.ngrok-free.app 8000 &

# Store the PID of the second background process (ngrok)
pid2=$!

# Wait for the background process (ngrok) to finish
wait $pid2

# Terminate gunicorn process
kill $pid1