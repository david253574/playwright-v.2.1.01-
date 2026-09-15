#!/bin/bash
echo "Stopping background worker..."
pkill -f background_worker.py

echo "Cleaning up orphaned Playwright Node processes..."
pkill -f "playwright/driver/node"

echo "Worker stopped."
