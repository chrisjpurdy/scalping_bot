import requests
import json
import time
from datetime import datetime, date, timedelta
from enum import Enum
from itertools import takewhile

from selenium import webdriver
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.action_chains import ActionChains as AC

import details

class Direction(Enum):
    BUY = "BUY"
    SELL = "SELL"

    def __not__(a):
        if a == Direction.BUY:
            return Direction.SELL
        else:
            return Direction.BUY


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
    
    def logout(self):
        r=requests.delete("https://demo-api.ig.com/gateway/deal/session")

    def prep_headers(self, headers):
        headers["Accept"] = "application/json; charset=UTF-8"
        headers["Content-Type"] = "application/json; charset=UTF-8"
        headers["X-IG-API-KEY"] = self.api_key
        if not self.cst is None:
            headers["CST"] = self.cst
        if not self.x_sec_token is None:
            headers["X-SECURITY-TOKEN"] = self.x_sec_token
        return headers
    
    def get_current_price(self, epic):
        
        r=requests.get("https://demo-api.ig.com/gateway/deal/markets/"+epic, headers=self.prep_headers({"VERSION":"2"}))
        
        market_dict = json.loads(r.text)
        snapshot = market_dict["snapshot"]
        
        return {"bid":snapshot["bid"], "offer":snapshot["offer"]}
    
    def get_min_stop_distance(self, epic):
    
        r=requests.get("https://demo-api.ig.com/gateway/deal/markets/"+epic, headers=self.prep_headers({"VERSION":"2"}))
    
        return json.loads(r.text)["dealingRules"]["minNormalStopOrLimitDistance"]["value"]

    def open_position(self, direction, epic, size, stop, limit):
        
        r=requests.get("https://demo-api.ig.com/gateway/deal/markets/"+epic, headers=self.prep_headers({"VERSION":"2"}))
        
        market_dict = json.loads(r.text)
        instrument = market_dict["instrument"]
        snapshot = market_dict["snapshot"]
        
        if (not instrument["forceOpenAllowed"]) or (not instrument["stopsLimitsAllowed"]):
            print("Error - instrument is not 100% safe to trade (cannot set guarunteed stops)")
            return 1

        r=requests.post("https://demo-api.ig.com/gateway/deal/positions/otc/", json={
                        "epic": epic,
                        "expiry": instrument["expiry"],
                        "currencyCode": "GBP",
                        "direction": direction.value,
                        "orderType": "MARKET",
                        "timeInForce": "EXECUTE_AND_ELIMINATE",
                        "size": size,
                        "forceOpen": True,
                        "guaranteedStop": False,
                        "stopDistance": stop,
                        "limitDistance": limit
                        },headers=self.prep_headers({"VERSION":"2"}))
            
        response = json.loads(r.text)
        deal_reference = response["dealReference"]

        r=requests.get("https://demo-api.ig.com/gateway/deal/positions",headers=self.prep_headers({"VERSION":"2"}))
        search_positions = json.loads(r.text)["positions"]
        return list(filter(lambda x: x["position"]["dealReference"] == deal_reference, search_positions))[0]["position"]["dealId"]

    def get_position_info(self, deal_id):
        r=requests.get("https://demo-api.ig.com/gateway/deal/positions/"+deal_id,headers=self.prep_headers({"VERSION":"2"}))
        return json.loads(r.text)

    def close_position(self, deal_id):
        
        r=requests.get("https://demo-api.ig.com/gateway/deal/positions",headers=self.prep_headers({"VERSION":"2"}))
        search_positions = json.loads(r.text)["positions"]
        close_pos = list(filter(lambda x: x["position"]["dealId"] == deal_id, search_positions))[0]

        r=requests.post("https://demo-api.ig.com/gateway/deal/positions/otc/", json={
                          "dealId": deal_id,
                          "direction": "SELL" if (close_pos["position"]["direction"] == "BUY") else "BUY",
                          "orderType": "MARKET",
                          "timeInForce": "EXECUTE_AND_ELIMINATE",
                          "size": int(close_pos["position"]["size"])
                          },headers=self.prep_headers({"VERSION":"1","_method":"DELETE"}))
                          
        print("Position closed with deal reference: "+json.loads(r.text)["dealReference"])


class TimeFrame(Enum):
    ONE_MIN = 1
    FIVE_MIN = 2
    FIFTEEN_MIN = 3
    THIRTY_MIN = 4
    ONE_HOUR = 5
    FIVE_HOUR = 6
    DAILY = 7
    WEEKLY = 8
    MONTHLY = 9


class invest_interpreter:

    driver = None
    url = None
    
    def __init__(self, invest_url):
        self.url = invest_url
    
    def close_signup_window(self):
        wait = WebDriverWait(self.driver, 100)
        
        attempts = 0
        while attempts < 5:
            try:
                close_button = wait.until(EC.presence_of_element_located((By.XPATH, "//*[@id=\"PromoteSignUpPopUp\"]/div[2]/i")))
                actions = AC(self.driver)
                actions.move_to_element(close_button)
                actions.click()
                actions.perform()
                break
            except:
                attempts += 1
                continue
    
    def get_stock_price(self):
        elem = self.driver.find_element_by_css_selector("#lastValue1")
        return elem.get_attribute("innerHTML")
    
    def get_simple_indicator(self, time_frame):
        self.open_indicator_tab(time_frame)
        wait = WebDriverWait(self.driver, 100)
        
        self.close_signup_window()
        
        attempts = 0
        while attempts < 10:
            try:
                indicator = wait.until(EC.presence_of_element_located((By.XPATH, "//*[@id=\"techStudiesInnerBoxRight\"]/div[1]/span")))
                ind_text = indicator.get_attribute("innerHTML")
                break
            except:
                attempts += 1
                continue
        
        return ind_text
    
    def get_detailed_indicators(self, time_frame):
        self.open_indicator_tab(time_frame)
        wait = WebDriverWait(self.driver, 100)
        
        table = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, ".technicalIndicatorsTbl")))
        headers = [header.get_attribute("innerHTML") for header in table.find_elements_by_css_selector("thead tr th")]
        result = [{headers[i]: cell.text.replace("\n","").replace("\t","") for i, cell in enumerate(row.find_elements_by_css_selector("td"))} for row in table.find_elements_by_css_selector("tbody tr")]
        # remove dict entry containing summary from the bottom set of cells
        del result[len(result) - 1]
        return result
    
    def open_indicator_tab(self, time_frame):
        wait = WebDriverWait(self.driver, 100)
        button = wait.until(EC.element_to_be_clickable((By.XPATH, "//*[@id=\"techSummaryPage\"]/li[%s]"%time_frame.value)))
        self.driver.execute_script("window.scrollTo(0,200)")

        actions = AC(self.driver)
        actions.move_to_element(button)
        actions.click()
        actions.perform()
        
    def start(self):
        self.driver = webdriver.Firefox()
        self.driver.get(self.url)
    
    def kill(self):
        if self.driver:
            self.driver.quit()


class investing_bot:

    invest_wrapper = None
    ig_stock_epic = None
    ig_wrapper = None
    ig_epic = None
    confidence = None
    position_ids = []
    
    def __init__(self, epic, trade_url, confidence):
        self.ig_epic = epic
        self.invest_wrapper = invest_interpreter(trade_url)
        self.ig_wrapper = ig_api(IG_API_KEY)
        self.ig_wrapper.login(IG_USERNAME, IG_PASSWORD)
        self.confidence = confidence
        
        #self.invest_wrapper.open()
    
        # Getting indicators from investing.com
        #print(self.invest_wrapper.get_simple_indicator(TimeFrame.FIVE_MIN))
        #print(self.invest_wrapper.get_detailed_indicators(TimeFrame.FIVE_MIN))
        self.run()
    
    def open_position(self, position_details):
        return self.ig_wrapper.open_position(position_details["direction"], self.ig_epic, position_details["size"], position_details["stop_dist"], position_details["stop_dist"]*1.5)
    
    def close_position(self, position_to_close):
        self.ig_wrapper.close_position(position_to_close["deal_id"])
        position_to_close.update({"closed":True})
        
    def interpret_indicators(self):
        # work out what to do in the case of a buy or sell indicator

        # perhaps only buy or sell when the indicator changes value
        # then close position when:
        #   indicator changes or indicator starts showing a lessening of strength (evaluate by looking at indicator breakdown,
        #   certain time has elapsed,
        #   almost end of trading day
        
        # look at the indicators for different time values - work out a lower bound and an upper bound for a window to attempt a trade at profit
        # if the trade gives below £10 profit, don't trade unless it hits the upper bound, then close the position no matter
        # maybe set the profit lower bound based on time left before the upper time bound is hit
        
        indicators = list(map(self.invest_wrapper.get_simple_indicator, list(TimeFrame)[0:5]))
        
        indicators = list(map(lambda x: {
                              'Strong Sell': -2,
                              'Sell': -1,
                              'Neutral': 0,
                              'Buy': 1,
                              'Strong Buy': 2
                              }.get(x, 0), indicators))
        
        def figure_out_possible_trade(indicator_list):
            # first choose the direction based on the shortest time frame (1 min)
            # then work out the time it can be active by looking for the first indicator which is neutral or contrary
            initial_dir = indicator_list[0]
            trend_vals = list(takewhile(lambda x: (x*initial_dir) > 0, indicator_list))
            
            trend_len_mins = {0:0,
                              1:1,
                              2:5,
                              3:15,
                              4:30,
                              5:60}.get(len(trend_vals))
            if trend_len_mins>0:
                return {"direction":(Direction.BUY if initial_dir>0 else Direction.SELL), "upper_time_bound":trend_len_mins*1.3, "lower_time_bound":trend_len_mins*0.3}
            else:
                return None

        possible_trade = figure_out_possible_trade(indicators)
        
        if possible_trade != None:
            possible_trade["size"] = self.confidence
            possible_trade["stop_dist"] = self.ig_wrapper.get_min_stop_distance(self.ig_epic)
        
        # trade will also be closed if it hits the stop or limit values
        # try to evaluate liquidity, volatility etc. to make sure the environment is right to trade
        
        return possible_trade
    
    def evaluate_position(self, pos_eval):
        
        position_info = self.ig_wrapper.get_position_info(pos_eval["deal_id"])
        current_price = self.ig_wrapper.get_current_price(self.ig_epic)
        
        if position_info.get("errorCode",False):
            print("----- Pos Closed -----")
            print("Position ID: "+str(pos_eval["deal_id"])+" no longer exists")
            pos_eval.update({"closed":True})
            return
    
        close_direction = Direction.SELL if position_info["position"]["direction"] == Direction.BUY.value else Direction.BUY
        close_price = current_price["bid"] if close_direction == Direction.SELL else current_price["offer"]
        #selling will use the bid price, buying the offer
        
        possible_profit = ((position_info["position"]["level"] - close_price) if close_direction==Direction.BUY else (close_price - position_info["position"]["level"])) * position_info["position"]["size"]
    
        opened_time = datetime.strptime(position_info["position"]["createdDate"], "%Y/%m/%d %H:%M:%S:000")
        current_time = datetime.now()
        
        time_open = (current_time - opened_time)
        
        print("----- Pos Data -----")
        print("Position ID: "+str(pos_eval["deal_id"]))
        print("Possible profit: £%.2f"%possible_profit)
        print("Position open for: " + str(time_open))
        
        print("In considerable profit?: "+str(possible_profit >= 5*self.confidence))
        print("In profit?: "+str(possible_profit >= 3*self.confidence))
        print("Open long enough?: "+str((time_open.total_seconds()//60) > pos_eval["lower_time_bound"])+" ("+str(pos_eval["lower_time_bound"])+")")
        print("Open too long?: "+str((time_open.total_seconds()//60) >= pos_eval["upper_time_bound"])+" ("+str(pos_eval["upper_time_bound"])+")")
    
    # If the position either gives considerable profit, is open longer than its lower bound and makes profit, or if its been open longer than its upper bound, close the position
        if (possible_profit >= 5*self.confidence) or ((possible_profit >= 3*self.confidence) and ((time_open.total_seconds()//60) > pos_eval["lower_time_bound"])) or ((time_open.total_seconds()//60) >= pos_eval["upper_time_bound"]):
            print("Closing position...")
            self.close_position(pos_eval)
    
    def save_positions(self):
        with open('positions.json', 'w') as json_file:
            json.dump(self.position_ids, json_file)

    def load_positions(self):
        try:
            with open('positions.json') as json_file:
                self.position_ids = json.load(json_file)
        except:
            print("No file to read")
    
    def run(self):
        
        time_to_stop = datetime.now() + timedelta(hours=1)
        print("Application will automatically stop at: "+str(time_to_stop))

        # first update position list, and evaluate if any need closing or removing
        self.load_positions()
        self.invest_wrapper.start()
        #print(self.position_ids)
        
        while(datetime.now() < time_to_stop):
            
            for pos in self.position_ids:
                self.evaluate_position(pos)
            
            self.position_ids = list(filter(lambda x: not(x.get("closed",False)),self.position_ids))
            
            self.save_positions()
            
            # WHEN LOOKING FOR AN OPENING OF A POSITION, USE THE INDICATOR
            # WHEN LOOKING TO CLOSE THE POSITION, USE THE CURRENT PRICE TO WORK OUT PROFIT, AND THE INDICATOR TO WORK OUT HOW LONG TO RIDE A TREND
            
            # if looking to open
            if len(self.position_ids) == 0:
                
                recommended_position = self.interpret_indicators()
            
                #decide on recommended pos, v simple check right now just to see if there exists a recommended position
                if recommended_position != None:
                    open_pos = self.open_position(recommended_position)
                    self.position_ids.append({"deal_id":open_pos, "upper_time_bound":recommended_position["upper_time_bound"], "lower_time_bound":recommended_position["lower_time_bound"]})
                    self.save_positions()

            time.sleep(2)

        #print(self.position_ids)
    
    def kill(self):
        self.ig_wrapper.logout()
        self.invest_wrapper.kill()

iibot = investing_bot("IX.D.FTSE.DAILY.IP", "https://www.investing.com/technical/uk-100-technical-analysis", 1)
iibot.kill()
