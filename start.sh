#!/bin/bash
# SPDX-FileCopyrightText: 2025 Luis Villa <luis@lu.is>
#
# SPDX-License-Identifier: BlueOak-1.0.0

# Start script for News Fixed - runs cron scheduler and web server

# Start supercronic in the background (cron scheduler)
echo "Starting supercronic scheduler..."
/usr/local/bin/supercronic /app/crontab &

# Start gunicorn in the foreground (web server)
echo "Starting gunicorn web server..."
exec /usr/local/bin/uv run gunicorn --bind 0.0.0.0:8080 --workers 2 --chdir /app/code/src web:app
