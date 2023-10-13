# tibia-market-tracker
A website, a bot and data to keep track of Tibia market prices over time

Try it out here https://www.mayiscoding.com/tibia-market-tracker/

![image](https://user-images.githubusercontent.com/19623152/232283743-6dbe49c3-3160-4fcc-b954-84c806b539fc.png)
![image](https://user-images.githubusercontent.com/19623152/235438430-64b99210-1d23-4ac8-90e2-7311969cf90c.png)

# Setup
The main.py runs a full market search on the first character of the provided account.
To automate the script execution, add a cron job (sudo crontab -e) using something like
0 6,18 * * * export DISPLAY=':0' && xhost + && cd /path/to/src && python3 main.py > logs/out_$(date +\%H-\%M--\%d-\%m-\%Y).txt
