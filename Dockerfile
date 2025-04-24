FROM espressif/idf:v5.4.1

# Mark the firmware as a safe include directory for git
RUN git config --global --add safe.directory "*"

# Add Pillow to the build environment
RUN bash -c "apt update && apt install -y python3-pillow && apt clean"

# Copy the build script in and define that as the entrypoint
COPY scripts/build.sh /
ENTRYPOINT ["/opt/esp/entrypoint.sh", "/build.sh"]
