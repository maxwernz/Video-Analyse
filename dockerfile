# Dockerfile

# Use a Python 3.12 base image (or a Windows-based image if available)
FROM ubuntu:20.04

# Install necessary packages for Wine, Python, and build tools
RUN dpkg --add-architecture i386 && \
    apt update && \
    apt install -y software-properties-common && \
    apt update && \
    apt install -y python3 python3-pip python3-venv wine64 wine32-development wget

# Install PyInstaller
RUN pip3 install --upgrade pip
RUN pip3 install pyinstaller

# Set up the working directory
WORKDIR /app

# Copy the application code
COPY . .

# Install Python dependencies
RUN pip3 install -r requirements.txt

# Run PyInstaller to build the app as an executable
RUN wine pyinstaller build.spec --noconfirm

# Zip the output (this will save it to a .zip file in the /app/dist directory)
RUN apt install -y zip && \
    zip -r dist/VideoAnalyse.zip dist/Video\ Analyse/*
