# Use official Python image
FROM python:3.10-slim

# System dependencies for Playwright and SQLite
RUN apt-get update && \
    apt-get install -y wget curl git build-essential libglib2.0-0 libnss3 libgconf-2-4 libfontconfig1 libxss1 libasound2 libxtst6 libatk-bridge2.0-0 libgtk-3-0 && \
    rm -rf /var/lib/apt/lists/*

# Set workdir
WORKDIR /app

# Copy requirements and install Python dependencies
COPY requirements.txt ./
RUN pip install --upgrade pip && pip install --no-cache-dir -r requirements.txt

# Install Playwright and browsers
RUN pip install --no-cache-dir playwright && playwright install --with-deps

# Copy the rest of the code
COPY . .

# Expose FastAPI port
EXPOSE 8000

# Set environment variables (optional, for production)
ENV PYTHONUNBUFFERED=1

# Default command: run FastAPI app with uvicorn
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"] 