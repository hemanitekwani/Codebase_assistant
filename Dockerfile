# 1. Use a lightweight official Python runtime
FROM python:3.11-slim

# 2. Set environment variables to optimize Python inside Docker
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# 3. Set the working directory inside the container
WORKDIR /app

# 4. CRITICAL: Install Git so your git_blame and git_log tools don't crash!
RUN apt-get update && \
    apt-get install -y --no-install-recommends git && \
    rm -rf /var/lib/apt/lists/*

# 5. Copy and install dependencies first (leverages Docker caching)
COPY requirements.txt .

RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt
# 6. Copy the rest of your application code into the container
COPY . .

# 7. Expose the port your FastAPI server runs on
EXPOSE 8000

# 8. Command to run your Uvicorn backend
CMD ["uvicorn", "api.app:app", "--host", "0.0.0.0", "--port", "8000"]