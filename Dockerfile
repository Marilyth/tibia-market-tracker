FROM ubuntu:22.04
ENV DEBIAN_FRONTEND=noninteractive

# Copy the current directory contents into the container at /app.
COPY . /app

# Set the working directory to /app.
WORKDIR /app/src

# Install dependencies.
RUN apt-get update && \ 
    apt-get install -y python3-dev python3-pip python3-tk\
    libpython3-dev tesseract-ocr tesseract-ocr-deu scrot libqt5gui5 \
    xvfb xserver-xephyr tigervnc-standalone-server x11-utils gnumeric &&\
    pip3 install -r /app/requirements.txt &&\
    apt-get clean

RUN apt-get install -y libqt5gui5
# Install Tibia.
RUN python3 install_tibia.py

# Run the command to start Tibia Market Tracker.
CMD [ "python3", "main.py y" ]

# Create this container with the tag "tibia-market-tracker" by running:
# docker build -t tibia-market-tracker .
# Run this container interactively with bash with the command:
# docker run --cap-add=SYS_PTRACE --security-opt seccomp=unconfined -it --rm -e DISPLAY=$DISPLAY -v /tmp/.X11-unix:/tmp/.X11-unix -v /path/to/config:/app/src/config tibia-market-tracker bash
# Run this container with the command:
# docker run --cap-add=SYS_PTRACE --security-opt seccomp=unconfined -it --rm -e DISPLAY=$DISPLAY -v /tmp/.X11-unix:/tmp/.X11-unix -v /path/to/config:/app/src/config tibia-market-tracker
# Upload this container to Docker Hub with the command:
# docker push tibiawiki/tibia-market-tracker