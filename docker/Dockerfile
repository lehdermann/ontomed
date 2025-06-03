FROM python:3.11-slim

# Metadata
LABEL maintainer="OntoMed Team"
LABEL description="OntoMed API server"
LABEL version="0.1.0"

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONPATH=/app \
    PORT=8000

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    libpq-dev \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Ensure PYTHONPATH includes the 'semantic' package
ENV PYTHONPATH=/app

# Copy only requirements first to leverage Docker cache
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy source code
COPY api/ /app/api/
COPY llm/ /app/llm/
COPY prompt/ /app/prompt/
COPY semantic/ /app/semantic/
COPY core/ /app/core/

# Expose port
EXPOSE ${PORT}

# Set entrypoint
WORKDIR /app/api
CMD ["python", "server.py", "--host", "0.0.0.0", "--port", "8000"]
