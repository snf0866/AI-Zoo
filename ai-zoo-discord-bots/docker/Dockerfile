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
    # Playwright/Chromium dependencies
    libglib2.0-0 \
    libnss3 \
    libnspr4 \
    libatk1.0-0 \
    libatk-bridge2.0-0 \
    libcups2 \
    libdrm2 \
    libdbus-1-3 \
    libxcb1 \
    libxkbcommon0 \
    libx11-6 \
    libxcomposite1 \
    libxdamage1 \
    libxext6 \
    libxfixes3 \
    libxrandr2 \
    libgbm1 \
    libpango-1.0-0 \
    libcairo2 \
    libasound2 \
    libatspi2.0-0 \
    libxshmfence1 \
    fonts-liberation \
    && rm -rf /var/lib/apt/lists/*

# Set timezone
ENV TZ=Asia/Tokyo
RUN ln -snf /usr/share/zoneinfo/$TZ /etc/localtime && echo $TZ > /etc/timezone

# Copy requirements file
COPY requirements.txt .

# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Install Playwright browser (Chromium) for headless browsing
RUN playwright install chromium --with-deps

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
