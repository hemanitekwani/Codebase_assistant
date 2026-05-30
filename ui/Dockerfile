# 1. Use the same lightweight Python runtime
FROM python:3.11-slim

# 2. Prevent Python from writing pyc files and buffering stdout
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# 3. Set the working directory
WORKDIR /app

# 4. Copy and install UI dependencies
# Note: Ensure your requirements.txt contains 'streamlit' and 'httpx'

COPY requirements-ui.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements-ui.txt

    

# 5. Copy your application files
COPY . .

# 6. Expose Streamlit's default port
EXPOSE 8501

# 7. Command to run Streamlit and bind it to allow external traffic
CMD ["streamlit", "run", "ui/app.py", "--server.address=0.0.0.0", "--server.port=8501"]