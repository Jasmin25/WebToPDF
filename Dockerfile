# Use an official Python runtime based on Debian bullseye as a parent image
FROM python:slim-bullseye

# Set the working directory in the container to /app
WORKDIR /app

# Copy the current directory contents into the container at /app
COPY . /app

# Install any needed packages specified in requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Download and install wkhtmltopdf
RUN apt-get update && \
    apt-get install -y wget xfonts-75dpi xfonts-base && \
    wget https://github.com/wkhtmltopdf/packaging/releases/download/0.12.6.1-2/wkhtmltox_0.12.6.1-2.bullseye_amd64.deb && \
    apt install -y ./wkhtmltox_0.12.6.1-2.bullseye_amd64.deb && \
    rm ./wkhtmltox_0.12.6.1-2.bullseye_amd64.deb

# Make port 5000 available to the world outside this container
EXPOSE 5000

# Define environment variable to inform Python that it is running inside a container
ENV PYTHONUNBUFFERED=1

# Run app.py when the container launches
CMD ["python", "app.py"]
