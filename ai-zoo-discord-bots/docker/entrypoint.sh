#!/bin/bash
set -e

# Function to start cron service
start_cron() {
    echo "Starting cron service..."
    cron -f
}

# Function to start a bot
start_bot() {
    BOT_TYPE=$1
    echo "Starting $BOT_TYPE bot..."
    
    if [ "$BOT_TYPE" = "main" ]; then
        python -m bots.main_bot
    elif [ "$BOT_TYPE" = "secondary" ]; then
        python -m bots.secondary_bot
    else
        echo "Unknown bot type: $BOT_TYPE"
        exit 1
    fi
}

# Function to run a scheduled message
run_scheduled_message() {
    echo "Running scheduled message..."
    python -m bots.scheduled_message "$@"
}

# Main entrypoint logic
case "$1" in
    main|secondary)
        start_bot "$1"
        ;;
    cron)
        start_cron
        ;;
    scheduled_message)
        shift
        run_scheduled_message "$@"
        ;;
    *)
        echo "Usage: $0 {main|secondary|cron|scheduled_message [message]}"
        exit 1
        ;;
esac
