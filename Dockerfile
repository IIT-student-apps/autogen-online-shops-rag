# Use an official Python runtime as a parent image
FROM python:3.11-slim

# Set the working directory in the container
WORKDIR /app

# Install wget for network diagnostics
RUN apt-get update && apt-get install -y wget && rm -rf /var/lib/apt/lists/*

# Copy the requirements file into the container at /app
COPY requirements.txt .

# Install any needed packages specified in requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application code into the container at /app
COPY . .

# Make port 8000 available for FastAPI
EXPOSE 8000
# Make port 8501 available for Streamlit
EXPOSE 8501

# Define environment variable
ENV NAME World

# Default command is removed, will be specified in docker-compose.yml
# CMD ["python", "app/main.py"] 