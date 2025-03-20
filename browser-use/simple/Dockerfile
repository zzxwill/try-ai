# Use Microsoft's Python base image with stable Ubuntu
FROM mcr.microsoft.com/playwright/python:v1.50.0-noble

WORKDIR /app

COPY requirements.txt .
RUN pip install -r requirements.txt

RUN apt-get update && apt-get install -y fonts-dejavu

# Create startup script
RUN echo '#!/bin/bash\nplaywright install\npython index.py' > start.sh && \
    chmod +x start.sh

COPY index.py .
CMD ["./start.sh"]