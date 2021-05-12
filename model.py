import numpy as np
import pandas as pd
import requests
import json
from datetime import datetime, date, timedelta

import details

class ig_api:
    
    cst = None
    x_sec_token = None
    api_key = None
    
    def __init__(self, key):
        self.api_key = key
    
    def login(self, username, password):
        r=requests.post("https://demo-api.ig.com/gateway/deal/session", json={
                        "identifier":username,
                        "password":password
                        }, headers=self.prep_headers({"VERSION":"2"}))
            
        self.cst = r.headers["CST"]
        self.x_sec_token = r.headers["X-SECURITY-TOKEN"]


    def prep_headers(self, headers):
        headers["Accept"] = "application/json; charset=UTF-8"
        headers["Content-Type"] = "application/json; charset=UTF-8"
        headers["X-IG-API-KEY"] = self.api_key
        if not self.cst is None:
            headers["CST"] = self.cst
        if not self.x_sec_token is None:
            headers["X-SECURITY-TOKEN"] = self.x_sec_token
        return headers


    #Just taking closing prices
    def get_hourly_prev_days(self, epic, num_days):
        
        today = datetime.today()
        yesterday = (today-timedelta(1)).strftime("%Y-%m-%dT23:59:59")
        n_days_ago = (today-timedelta(num_days)).strftime("%Y-%m-%dT00:00:00")
        
        print(yesterday)
        print(n_days_ago)
        
        r = requests.get("https://demo-api.ig.com/gateway/deal/prices/"+epic, params={
                         "resolution": "HOUR",
                         "max": "1000",
                         "pageSize": "1000",
                         "pageNumber": "1",
                         "from": n_days_ago.replace(":","%3A"), #replacing colons to make date compatible as a http request param
                         "to": yesterday.replace(":","%3A")
                         },headers=self.prep_headers({"VERSION":"3"}))
        
        prices = json.loads(r.text)["prices"]
        prices = list(map(lambda x: {"date":datetime.strptime(x["snapshotTimeUTC"],"%Y-%m-%dT%H:%M:%S"),"rawPrice":x["closePrice"],"avgPrice":((x["closePrice"]["bid"]+x["closePrice"]["ask"])/2)}, prices))

        return prices
    

    def get_secondly_daily_prices(self, epic):
        
        start_of_today = datetime.today().strftime("%Y-%m-%dT00:00:00")
        
        r = requests.get("https://demo-api.ig.com/gateway/deal/prices/"+epic, params={
                         "resolution": "SECOND",
                         "max": "3",
                         "pageSize": "1000",
                         "pageNumber": "1",
                         "from": start_of_today.replace(":","%3A")
                         },headers=self.prep_headers({"VERSION":"3"}))

        prices = json.loads(r.text)["prices"]
        prices = list(map(lambda x: {"date":datetime.strptime(x["snapshotTimeUTC"],"%Y-%m-%dT%H:%M:%S"),"rawPrice":x["closePrice"],"avgPrice":((x["closePrice"]["bid"]+x["closePrice"]["ask"])/2)}, prices))
        
        return prices



# get historical data (only up to 10000 per week using IG API remember) and store in an array
# when operating intraday, just take data from the current day (datapoints each second or every few seconds)

# get each of the 4 measures of the time series data outlined on the IG '4 simple scalping trading strategies' article

#stochastic oscillator - takes hourly data from past n days, and second-ly data from the current day
def stoc_n(n_days_historical_prices, last_3_prices):
    
    #work out how many days worth of houly data
    #times are stored as a datetime object formed from the timestamp of the stock snapshot (eg. "2019/08/30 21:00:00")
    current_time = last_3_prices[2]["date"]
    n_days = (current_time - min(list(map(lambda x: x["date"], n_days_historical_prices)))).days

    p_array = list(map(lambda x: x["avgPrice"], n_days_historical_prices))
    
    highest_p = max(p_array)
    lowest_p = min(p_array)

    def k_func(n):
        return 100*(n-lowest_p)/(highest_p-lowest_p)

    d=0
    for k in range(3):
        d += k_func(last_3_prices[k]["avgPrice"])
    d = d/3

    return d

def interpret_stoc_n():


def macd():



# work out from each measure whether a trade might be profitable (with a probability between 0-1), given the current price and either a stop price or expiry time on the trade

# take the weighted average of the probabilities to get a final probability of profit/some measure of possible outcome

# make or don't make a trade based on that, and decide what strategy to use to close the position later
#   either decide to stop after a certain profit, or go out after a certain time

# use historical data points from other days to test the model and see if it could be profitable

ig = ig_api(IG_API_KEY)
ig.login(IG_USERNAME, IG_PASSWORD)

prev_day = ig.get_hourly_prev_days("IX.D.FTSE.CFD.IP",2)

print(stoc_n(prev_day,ig.get_secondly_daily_prices("IX.D.FTSE.CFD.IP")))
