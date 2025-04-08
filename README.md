# tibia-market-tracker
A tool to keep track of Tibia market prices over time

# Setup (WIP)
1. Run the `./install.sh` to install all required dependencies.
2. Install the `requirements.txt` or `requirements_api.txt` using pip, depending on your need.
3. Fill out the `src/config/config.json` with the desired values.
4. Compile the zlib decompressor by running `dotnet build`
5. Run `sudo python3 src/extract.py` or `sudo python3 src/api.py`
