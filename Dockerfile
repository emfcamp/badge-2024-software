# Start with vaguely modernish ubuntu that doesn't have seccomp compat issues
FROM ubuntu:22.04

# Prevent tzinfo prompts
ARG DEBIAN_FRONTEND=noninteractive

# Set up access to newer git, to allow glob safe directories
# Update apt and install build dependencies
RUN apt-get update && apt-get install -y software-properties-common && apt-get update && apt-get install -y build-essential python3-pip libusb-1.0-0-dev cmake wget zip git python3-pillow python3-venv

# Download the ESP-IDF v5.1 release and install it
# Do this all in one step to avoid creating extraneous layers
RUN mkdir /esp-idf && git clone -b v5.0.4 --recursive https://github.com/espressif/esp-idf /esp-idf && /esp-idf/install.sh
WORKDIR /esp-idf

# Mark the firmware as a safe include directory for git
#RUN git config --global --add safe.directory "/firmware/*"
#RUN git config --global --add safe.directory "/firmware/micropython"

# Add Pillow to the build environment
RUN bash -c "source /esp-idf/export.sh && python3 -m pip install Pillow"

# Copy the build script in and define that as the entrypoint
COPY scripts/build.sh /
ENTRYPOINT ["/build.sh"]
