# Use Microsoft's Python base image
FROM mcr.microsoft.com/playwright/python:v1.40.0-focal

# Set up working directory
WORKDIR /app

# Install X11 and display utilities
RUN apt-get update && apt-get install -y \
    xvfb \
    x11-utils \
    x11-xserver-utils \
    xauth \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt .
RUN pip install -r requirements.txt || pip install langchain-openai python-dotenv playwright langchain openai

# Copy the application code
COPY . .

# Create videos directory
RUN mkdir -p /app/videos && chmod 777 /app/videos

# Set up display for X11 forwarding
ENV DISPLAY=:99

# Xvfb configuration
ENV XVFB_WHD="1920x1080x24"
ENV XVFB_SCREEN=":99"

# Create a script to start Xvfb and run the application
RUN echo '#!/bin/bash\nXvfb ${XVFB_SCREEN} -screen 0 ${XVFB_WHD} -nolisten tcp -nolisten unix &\necho "Waiting for Xvfb..."\nsleep 2\necho "Starting main.py..."\npython main.py\n' > /app/start.sh \
    && chmod +x /app/start.sh

# Create a volume for storing recordings
VOLUME /app/videos

# Command to run the application
CMD ["/app/start.sh"]