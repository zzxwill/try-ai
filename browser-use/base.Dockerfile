# Use Microsoft's Python base image
FROM mcr.microsoft.com/playwright/python:v1.50.0-noble

# Install necessary system packages for better video recording and window capture
RUN --mount=type=cache,target=/var/cache/apt \
    apt-get update && \
    apt-get install -y --no-install-recommends \
    xvfb \
    x11-utils \
    x11-xserver-utils \
    xauth \
    ffmpeg \
    pulseaudio \
    libnss3 \
    libatk1.0-0 \
    libatk-bridge2.0-0 \
    libcups2 \
    libdrm2 \
    libxkbcommon0 \
    libxcomposite1 \
    libxdamage1 \
    libxfixes3 \
    libxrandr2 \
    libgbm1 \
    libasound2t64 \
    xdotool \
    imagemagick \
    procps \
    scrot \
    dbus-x11 \
    fluxbox \
    openbox \
    libgl1-mesa-dri \
    mesa-utils \
    x11vnc \
    feh \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Fix imagemagick policy to allow screenshots
RUN if [ -f /etc/ImageMagick-6/policy.xml ]; then \
    sed -i 's/rights="none" pattern="@\*"/rights="read|write" pattern="@\*"/' /etc/ImageMagick-6/policy.xml; \
    fi

# If ImageMagick is newer version (7+), check other path
RUN if [ -f /etc/ImageMagick/policy.xml ]; then \
    sed -i 's/rights="none" pattern="@\*"/rights="read|write" pattern="@\*"/' /etc/ImageMagick/policy.xml; \
    fi

# Create fluxbox configuration to avoid warnings
RUN mkdir -p /root/.fluxbox && \
    echo "session.screen0.toolbar.visible: false" > /root/.fluxbox/init && \
    echo "session.screen0.toolbar.autoHide: true" >> /root/.fluxbox/init

# Create a symbolic link to ensure import command is in PATH
RUN which import || (which convert && ln -s $(which convert) /usr/local/bin/import)

# Copy requirements first for better caching
COPY requirements.txt .

# Set up required directories and permissions
RUN mkdir -p /tmp/.X11-unix && chmod 1777 /tmp/.X11-unix && \
    mkdir -p /tmp/test-screenshots && \
    mkdir -p /run/dbus && chmod 755 /run/dbus

# Create test HTML page for visual verification
RUN echo '<!DOCTYPE html><html><head><title>Test Content</title>' > /tmp/test.html && \
    echo '<style>body{background-color:#3498db;color:white;font-family:Arial;' >> /tmp/test.html && \
    echo 'display:flex;justify-content:center;align-items:center;height:100vh;margin:0;}' >> /tmp/test.html && \
    echo 'h1{font-size:48px;}</style></head>' >> /tmp/test.html && \
    echo '<body><h1>Test Content - This is not a black screen!</h1></body></html>' >> /tmp/test.html

# Install only production Python dependencies
RUN --mount=type=cache,target=/root/.cache/pip \
    pip install --no-cache-dir -r requirements.txt && \
    pip cache purge

# Create browser-use patching script
RUN echo 'import os, sys, subprocess, logging, time, asyncio\n\n' > /tmp/browser_use_patch.py && \
    echo 'logging.basicConfig(level=logging.INFO, format="%(levelname)s [%(name)s] %(message)s")\n' >> /tmp/browser_use_patch.py && \
    echo 'logger = logging.getLogger("browser_use_patch")\n\n' >> /tmp/browser_use_patch.py && \
    echo '# Monkey patch subprocess.check_output to handle xdotool failures\n' >> /tmp/browser_use_patch.py && \
    echo 'original_check_output = subprocess.check_output\n\n' >> /tmp/browser_use_patch.py && \
    echo 'def patched_check_output(cmd, *args, **kwargs):\n' >> /tmp/browser_use_patch.py && \
    echo '    try:\n' >> /tmp/browser_use_patch.py && \
    echo '        return original_check_output(cmd, *args, **kwargs)\n' >> /tmp/browser_use_patch.py && \
    echo '    except subprocess.CalledProcessError as e:\n' >> /tmp/browser_use_patch.py && \
    echo '        if isinstance(cmd, str) and ("xdotool search" in cmd):\n' >> /tmp/browser_use_patch.py && \
    echo '            logger.warning(f"xdotool command failed, returning empty result: {cmd}")\n' >> /tmp/browser_use_patch.py && \
    echo '            return b""\n' >> /tmp/browser_use_patch.py && \
    echo '        raise e\n\n' >> /tmp/browser_use_patch.py && \
    echo 'subprocess.check_output = patched_check_output\n\n' >> /tmp/browser_use_patch.py && \
    echo 'logger.info("Browser-use patching completed: xdotool failures will be handled gracefully")\n' >> /tmp/browser_use_patch.py

# Environment variables
ENV DISPLAY=:99
ENV BROWSER_USE_HEADLESS=true
ENV PLAYWRIGHT_SKIP_BROWSER_DOWNLOAD=1
ENV PYTHONPATH="/tmp:"
