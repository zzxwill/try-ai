# Use Microsoft's Python base image
FROM mcr.microsoft.com/playwright/python:v1.50.0-noble

# Set up working directory
WORKDIR /app

# Copy requirements and install Python dependencies
COPY requirements.txt .
RUN pip install -r requirements.txt

# Copy the application code
COPY . .

# Set up display for X11 forwarding
ENV DISPLAY=:99

# Create a script to start Xvfb and run the application
RUN echo '#!/bin/bash\nXvfb :99 -screen 0 1920x1080x24 &\nsleep 1\npython main.py' > /app/start.sh \
    && chmod +x /app/start.sh

# Command to run the application
CMD ["/app/start.sh"]