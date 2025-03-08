FROM python:3.9-slim

# Set working directory
WORKDIR /app

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app

# Install cron and other dependencies
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    cron \
    tzdata \
    && rm -rf /var/lib/apt/lists/*

# Set timezone
ENV TZ=Asia/Tokyo
RUN ln -snf /usr/share/zoneinfo/$TZ /etc/localtime && echo $TZ > /etc/timezone

# Copy requirements file
COPY requirements.txt .

# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy project files
COPY . .

# Make scripts executable
RUN chmod +x /app/docker/entrypoint.sh
RUN chmod +x /app/docker/start_bot.sh

# Set up cron jobs
COPY docker/cron/crontab /etc/cron.d/bot-crontab
RUN chmod 0644 /etc/cron.d/bot-crontab && \
    crontab /etc/cron.d/bot-crontab

# Set entrypoint
ENTRYPOINT ["/app/docker/entrypoint.sh"]

# Default command (can be overridden)
CMD ["main"]
