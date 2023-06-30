from tibia import Client, MarketValues, Wiki
import time
import os
import json
import schedule
import subprocess
from datetime import datetime
from git.repo import Repo


def write_marketable_items():
    items = Wiki().get_all_marketable_items()
    with open("tracked_items.txt", "w") as f:
        for item in items:
            f.write(item + "\n")

def write_events(results_location: str):
    """
    Writes all currently known events into the events.csv in the results_location.
    """
    try:
        last_date = datetime.min

        if os.path.exists(os.path.join(results_location, "events.csv")):
            with open(os.path.join(results_location, "events.csv"), "r") as event_file:
                previous_events = [event for event in event_file.readlines() if event and not str.isspace(event)]
                if previous_events:
                    last_date = datetime.strptime(previous_events[-1].split(",")[0], "%Y.%m.%d")

        with open(os.path.join(results_location, "events.csv"), "a+") as event_file:
            events = [event for event in Wiki().get_events(last_date) if event.date <= datetime.today()]
            if events:
                # Write all events that are in the past up until today to the events file.
                # This is done so that spontaneous events that are added to the schedule are not missed.
                event_file.write("\n".join([event.__str__() for event in events]) + "\n")
    except Exception as e:
        print(f"Writing events failed: {e}")


def do_market_search(email: str, password: str, tibia_location: str, results_location: str):
    write_events(results_location)

    with open(os.path.join(results_location, "fullscan_tmp.csv"), "w+") as f:
        f.write("Name,SellPrice,BuyPrice,AvgSellPrice,AvgBuyPrice,Sold,Bought,ActiveTraders\n")
        
        client = Client()
        client.start_game(tibia_location)
        client.login_to_game(email, password)

        if not client.open_market():
            client.exit_tibia()
            return
        
        for category in range(1, 25):
            try:
                for item in client.crawl_market(category):
                    with open(os.path.join(results_location, "histories", f"{item.name.lower()}.csv"), "a+") as h:
                        h.write(item.history_string() + "\n")
                    f.write(f"{item}\n")
            except Exception as e:
                print(f"Error while crawling market: {e}")
                break
        
    client.exit_tibia()

    os.replace(os.path.join(results_location, "fullscan_tmp.csv"), os.path.join(results_location, "fullscan.csv"))
    push_to_github(results_location)

    turn_off_display()

def push_to_github(results_repo_location: str):
    """
    Pushes the new market data from the results repo to GitHub.
    """
    try:
        repo = Repo(os.path.join(results_repo_location, ".git"))
        repo.git.add(all=True)
        repo.index.commit("Update market data")
        origin = repo.remote("origin")
        origin.push()
    except Exception as e:
        print(f"Error while pushing to git: {e}")

def turn_off_display():
    """Turns off the display by using xset.
    The display will turn on again when there is mouse or keyboard activity.
    This is done to save power.
    """
    os.system("xset dpms force off")

if __name__ == "__main__":
    with open("config.json", "r") as c:
        config = json.loads(c.read())

    #schedule.every().day.at("10:15:00").do(lambda: observe_items(config["email"], config["password"], config["tibiaLocation"], config["resultsLocation"]))
    #observe_items(config["email"], config["password"], config["tibiaLocation"], config["resultsLocation"])
    if input("Do you want to do a run right now? (y/n): ").lower() == "y":
        do_market_search(config["email"], config["password"], config["tibiaLocation"], config["resultsLocation"])
    
    turn_off_display()

    schedule.every().day.at("18:00:00").do(lambda: do_market_search(config["email"], config["password"], config["tibiaLocation"], config["resultsLocation"]))
    schedule.every().day.at("06:00:00").do(lambda: do_market_search(config["email"], config["password"], config["tibiaLocation"], config["resultsLocation"]))
    
    while True:
        schedule.run_pending()
        time.sleep(60)
