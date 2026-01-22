FROM python:3.9-slim

WORKDIR /app

# Install system dependencies if needed (e.g. for some scikit build steps, though slim usually ok for wheels)
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Install python dependencies
RUN pip install --no-cache-dir \
    scikit-learn \
    pandas \
    google-cloud-storage \
    joblib

# Copy training script
# We assume the build context is 'backend/' so train.py is at root of context
COPY train.py /app/train.py

# Entrypoint
ENTRYPOINT ["python", "train.py"]
