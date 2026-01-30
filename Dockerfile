FROM python:3.11-slim

WORKDIR /app

# Install VLC and audio dependencies
RUN apt-get update && apt-get install -y \
    vlc \
    libvlc-dev \
    alsa-utils \
    pulseaudio \
    && rm -rf /var/lib/apt/lists/*

# Create a non-root user for VLC (VLC refuses to run as root)
RUN useradd -m vlcuser
RUN usermod -aG audio vlcuser

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY app.py .

# Expose port
EXPOSE 5001

# Set user
USER vlcuser

# Environment variables for audio
ENV PULSE_SERVER=unix:/run/user/1000/pulse/native

# Run the application
CMD ["python", "app.py"]
