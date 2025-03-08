#!/bin/bash
set -e

# Function to display usage
usage() {
    echo "Usage: $0 {main|secondary|all} [--dev]"
    echo "  main       - Start the main bot"
    echo "  secondary  - Start the secondary bot"
    echo "  all        - Start all bots"
    echo "  --dev      - Run in development mode (with auto-reload)"
    exit 1
}

# Check if at least one argument is provided
if [ $# -lt 1 ]; then
    usage
fi

# Parse arguments
BOT_TYPE=$1
DEV_MODE=0

if [ $# -gt 1 ] && [ "$2" = "--dev" ]; then
    DEV_MODE=1
fi

# Function to start a bot
start_bot() {
    local bot_type=$1
    local bot_script=""
    
    if [ "$bot_type" = "main" ]; then
        bot_script="bots.main_bot"
    elif [ "$bot_type" = "secondary" ]; then
        bot_script="bots.secondary_bot"
    else
        echo "Unknown bot type: $bot_type"
        exit 1
    fi
    
    echo "Starting $bot_type bot..."
    
    if [ $DEV_MODE -eq 1 ]; then
        # Run with auto-reload in development mode
        python -m watchgod $bot_script.main
    else
        # Run normally
        python -m $bot_script
    fi
}

# Main logic
case "$BOT_TYPE" in
    main)
        start_bot "main"
        ;;
    secondary)
        start_bot "secondary"
        ;;
    all)
        # Start all bots in background
        start_bot "main" &
        MAIN_PID=$!
        
        start_bot "secondary" &
        SECONDARY_PID=$!
        
        # Wait for all bots to finish
        wait $MAIN_PID
        wait $SECONDARY_PID
        ;;
    *)
        usage
        ;;
esac
