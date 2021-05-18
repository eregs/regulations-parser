#!/bin/sh
# Create a directory for the output
mkdir -p output
# Create a placeholder local_settings.py, if none exists
touch local_settings.py
# Execute docker with appropriate flags while passing in any arguments.
# --rm removes the container after execution
# -it makes the container interactive (particularly useful with --debug)
# -v mounts volumes for cache, output, and copies in the local settings
docker run --rm -it -v eregs-cache:/app/cache -v $PWD/output:/app/output -v $PWD/local_settings