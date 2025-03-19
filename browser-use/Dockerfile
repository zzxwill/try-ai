FROM vefaas-enterprise-ap-southeast-1.cr.volces.com/zhengxi/browser-use-base:latest

# Set up working directory
WORKDIR /app

# Create videos directory with proper permissions
RUN mkdir -p /app/videos && chmod 777 /app/videos

# Create fluxbox configuration directory and init file
RUN mkdir -p /root/.fluxbox && \
    echo "session.screen0.toolbar.visible: false" > /root/.fluxbox/init && \
    echo "session.screen0.toolbar.autoHide: true" >> /root/.fluxbox/init

# Create the browser_use_patch.py file directly in /tmp
RUN echo 'import os, sys, subprocess, logging, time\n' > /tmp/browser_use_patch.py && \
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

# Copy application files
COPY main.py .
COPY run.sh .
RUN chmod +x run.sh

# Set environment variables
ENV DISPLAY=:99
ENV BROWSER_USE_HEADLESS=true
ENV PLAYWRIGHT_SKIP_BROWSER_DOWNLOAD=1
ENV PYTHONPATH="/tmp:/app"
ENV HOME=/root
ENV DEBIAN_FRONTEND=noninteractive

# Application command
ENTRYPOINT ["./run.sh"]