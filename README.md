# tibia-market-tracker
A tool to keep track of Tibia market prices over time

# Setup
1. Run the `./install.sh` to install all required dependencies.
2. Install the `requirements.txt` or `requirements_api.txt` using pip, depending on your need.
3. Fill out the `src/config/config.json` with the desired values.
4. Run `sudo python3 extract.py` or `sudo python3 api.py`

The `extract.py` runs a full market search on the first character of the provided account.
To automate the script execution, add a cron job (`sudo crontab -e`) using something like

0 20 * * * export DISPLAY=':0' && xhost + && cd /home/may/Desktop/tibia-market-tracker-bot/src && ./kill_trackers.sh && python3 extract.py > logs/out_$(date +\%Y-\%m-\%d--\%H-\%M>
