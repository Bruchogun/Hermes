#!/bin/bash

LOG_FILE="/home/brucho/Hermes/cron.log"

echo "=== $(date): Initializing Hermes ===" >> "$LOG_FILE"

cd /home/brucho/Hermes

source .venv/bin/activate

python main.py >> "$LOG_FILE" 2>&1
PYTHON_EXIT_CODE=$?

deactivate

if [ $PYTHON_EXIT_CODE -eq 0 ]; then
    echo "$(date): Hermes finished successfully" >> "$LOG_FILE"
else
    echo "$(date): Hermes failed with exit code $PYTHON_EXIT_CODE" >> "$LOG_FILE"
fi

exit $PYTHON_EXIT_CODE