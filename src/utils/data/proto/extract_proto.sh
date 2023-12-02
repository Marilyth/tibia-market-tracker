#!/bin/bash

# Extracts the proto files from the Tibia client executable.
cd "$(dirname "$0")"
cd protod
python2 ./protod ~/.local/share/CipSoft\ GmbH/Tibia/packages/Tibia/bin/client
cd ..

# Compile the proto files.
protoc/bin/protoc --proto_path=protod --python_out=./ --pyi_out=./ protod/*.proto