FROM PYTHON:3.12-slim



ENV MONGO_DB_USERNAME=admin \
    MONGO_DB_PASSWORD=password \
    MONGO_DB_HOST=mongodb \
    MONGO_DB_PORT=27017 \
    MONGO_DB_NAME=admin


WORKDIR /app


RUN pip install --no-cache-dir -r requirements.txt



COPY ./CODEBASE_ASSISTANT

CMD ["python", "main.py"]


