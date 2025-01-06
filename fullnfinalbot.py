import base64
import json
import datetime
import random
import time
from datetime import datetime,timedelta
from selenium.webdriver.common.by import By
from driver import companies, get_driver
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import queue
import numpy as np
import pandas as pd


significant_reversals = {}
confirmed_reversals = {}
# Define the global variables
BASE_URL = 'https://pocketoption.com'
LENGTH_STACK_MIN = 460
LENGTH_STACK_MAX = 1000
PERIOD = 60
STACK = {}
tradeprofit =0
previous_amount = 0
CURRENCY = None
CURRENCY_CHANGE = False
CURRENCY_CHANGE_DATE = datetime.now()
HISTORY_TAKEN = False
MAX_DEPOSIT = 0
in_deposit = None
NUMBERS = {
    '0': '11', '1': '7', '2': '8', '3': '9', '4': '4', '5': '5', '6': '6', 
    '7': '1', '8': '2', '9': '3','.' : '10',
}
IS_AMOUNT_SET = True
AMOUNTS = [] 
na = 0
naa = 0
# Get the WebDriver instance
driver = get_driver()

def get_driver_instance():
    """
    This function simply returns the existing WebDriver instance.
    """
    global driver
    if driver is None:
        driver = get_driver()  # Initialize the WebDriver if not already initialized
    return driver

# Create a queue to pass the stack between functions
stack_queue = queue.Queue()

def load_web_driver():
    url = f'{BASE_URL}/en/cabinet/demo-quick-high-low/'
    driver.get(url)
    print(f"WebDriver loaded with URL: {url}")

def websocket_log(last_update_time):
    global STACK, CURRENCY, CURRENCY_CHANGE, CURRENCY_CHANGE_DATE, HISTORY_TAKEN, PERIOD
    current_time = datetime.now()

    if (current_time - last_update_time).total_seconds() >= 0.5:  # Process every 0.5 seconds
        last_update_time = current_time  # Update the timestamp
        try:
            current_symbol = driver.find_element(by=By.CLASS_NAME, value='current-symbol').text
            if current_symbol != CURRENCY:
                CURRENCY = current_symbol
                CURRENCY_CHANGE = True
                CURRENCY_CHANGE_DATE = current_time
        except:
            pass

        if CURRENCY_CHANGE and CURRENCY_CHANGE_DATE < current_time - timedelta(seconds=5):
            STACK = {}
            HISTORY_TAKEN = False
            driver.refresh()
            CURRENCY_CHANGE = False
          

        for wsData in driver.get_log('performance'):
            message = json.loads(wsData['message'])['message']
            response = message.get('params', {}).get('response', {})
            if response.get('opcode', 0) == 2 and not CURRENCY_CHANGE:
                payload_str = base64.b64decode(response['payloadData']).decode('utf-8')
                data = json.loads(payload_str)
                if not HISTORY_TAKEN:
                    if 'history' in data and data['history']:
                        STACK = {int(d[0]): d[1] for d in data['history']}
                        print(f"History taken for asset: {data['asset']},period: {data['period']}, len_history: {len(data['history'])}, len_stack: {len(STACK)}")
                        PERIOD = data['period']  
                try:
                    symbol, timestamp, value = data[0]
                except:
                    continue
                if len(STACK) == LENGTH_STACK_MAX:
                    first_element = list(STACK.keys())[0]
                    if timestamp - first_element > PERIOD:
                        STACK = {k: v for k, v in STACK.items() if k > timestamp - LENGTH_STACK_MIN}
                STACK[timestamp] = value

        # Add timestamp to stack before sending to trade_process
        stack_with_timestamp = {'timestamp': current_time, 'stack': STACK}
        
        # Put the updated stack in the queue for processing by trade_process
        stack_queue.put(stack_with_timestamp)

    return last_update_time
def hand_delay():
    time.sleep(random.choice([0.2, 0.3, 0.4, 0.5, 0.6,1]))
def trade_process():
    global na, PERIOD, confirmed_reversals, in_deposit, signal_price
    candles = []  # List to hold the formed candles
    last_processed_candle_time = None  # Track the last processed candle time
    # Set EMA periods dynamically based on the selected timeframe
    if PERIOD == 5:
        fast_ema_period = 10
        slow_ema_period = 21
    elif PERIOD == 10:
        fast_ema_period = 8
        slow_ema_period = 16
    elif PERIOD == 15:
        fast_ema_period = 6
        slow_ema_period = 12
    else:
        fast_ema_period = 5
        slow_ema_period = 10
    while True:
        if not stack_queue.empty():
            stack_data = stack_queue.get()
            copied_stack = stack_data['stack']
            timestamp = stack_data['timestamp']

            for ts, price in list(copied_stack.items()):
                candle_time = ts - (ts % PERIOD)
                if candles and candles[-1]['time'] == candle_time:
                    candles[-1]['high'] = max(candles[-1]['high'], price)
                    candles[-1]['low'] = min(candles[-1]['low'], price)
                    candles[-1]['close'] = price
                else:
                    candles.append({
                        'time': candle_time,
                        'open': price,
                        'high': price,
                        'low': price,
                        'close': price
                    })
                    if len(candles) > 50:
                        candles.pop(0)
            
            if len(candles) >= 50 and candles[-1]['time'] != last_processed_candle_time:
    
                  # Get the current driver instance

                capture_reversal_points(candles)        
                trend = identify_trend(candles)
                if not trend == "consolidating":
                    print(f"market is trending :{trend}")
                    print(f"{len(candles)}")
                    fast_ema = calculate_ema(candles, fast_ema_period)
                    slow_ema = calculate_ema(candles, slow_ema_period)
                    signal_price = candles[-1]['close']
                    print(f"signal generated price:{signal_price}")
                # Signal generation logic 
                    if fast_ema > slow_ema and candles[-1]['close'] > fast_ema:
                         basic_signal = "call"
                    elif fast_ema < slow_ema and candles[-1]['close'] < fast_ema:
                         basic_signal = "put"
                    else:
                         basic_signal = None
                    print(f"signal generated with candles:{basic_signal}")
                # Proceed with signal confirmation if a basic signal is generated
                
                    # Calculate Heiken Ashi candles
                    heiken_ashi_candles = calculate_heiken_ashi(candles)
                    fast_ema = calculate_ema(heiken_ashi_candles, fast_ema_period)
                    slow_ema = calculate_ema(heiken_ashi_candles, slow_ema_period)
                    rtime = candles[-1]['time']
                    readable_time = datetime.fromtimestamp(rtime)
                    print(f"Last processed candle time: {readable_time.strftime('%Y-%m-%d %H:%M:%S')}")
                    if fast_ema > slow_ema and candles[-1]['close'] > fast_ema:
                          basic_signal1 = "call"
                    elif fast_ema < slow_ema and candles[-1]['close'] < fast_ema:
                          basic_signal1 = "put"
                    else:
                         basic_signal1 = None
                    print(f"signal generated with HA candles:{basic_signal1}")
                
                    nearest_price = 0
                    min_diff = float('inf')  # Initialize the minimum difference to infinity
                    price = signal_price
                # Iterate through confirmed reversals and find the nearest price
                    for price in confirmed_reversals.keys():
                      diff = abs(price - signal_price)  # Calculate absolute difference
                      if diff < min_diff:
                          min_diff = diff
                          nearest_price = price
                    print(f"nearest price:{nearest_price}")

                    if nearest_price > 0:
                         if basic_signal == "call" and basic_signal1 == "call" and nearest_price <= signal_price:
                                semi_final_signal = "call"
                         elif basic_signal == "put" and basic_signal1 == "put" and nearest_price >= signal_price:
                                semi_final_signal = "put"
                         else:
                                semi_final_signal = "Hold:1"
                    else:
                         semi_final_signal = "Hold"
                    print(f"snr signal: {semi_final_signal}") 
                    if semi_final_signal == "call" or semi_final_signal == "put" :  
                           do_action(semi_final_signal)  
                    pass       
                else:
                    print(f"Market is consolidating.")
                    pass
                last_processed_candle_time = candles[-1]['time']

def do_action(signal):
    global signal_price, CURRENCY, in_deposit, previous_amount, tradeprofit, PERIOD, na
    
    print(f"executing: {signal}")
    driver = get_driver_instance()
    if na == 0:
        next_amount = 1
        amount_input = WebDriverWait(driver, 10).until(
        EC.element_to_be_clickable((By.CSS_SELECTOR, '#put-call-buttons-chart-1 > div > div.blocks-wrap > div.block.block--bet-amount > div.block__control.control > div.control__value.value.value--several-items > div > input[type=text]'))
        )
        
                     # Clear any pre-existing value and set the amount  
        amount_input.click()
                   # Click the amount input field (if required)
        base = '#modal-root > div > div > div > div > div.trading-panel-modal__in > div.virtual-keyboard > div > div:nth-child(%s) > div'
        for number in str(next_amount):
            driver.find_element(by=By.CSS_SELECTOR, value=base % NUMBERS[number]).click()
        amount_input.click()
        deposit = driver.find_element(by=By.CSS_SELECTOR, value='body > div.wrapper > div.wrapper__top > header > div.right-block.js-right-block > div.right-block__item.js-drop-down-modal-open > div > div.balance-info-block__data > div.balance-info-block__balance > span')
        in_deposit = float(deposit.text.replace(',', ''))
        print(f"deposit :{in_deposit}")
        try:
            closed_tab = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.CSS_SELECTOR, '#bar-chart > div > div > div.right-widget-container > div > div.widget-slot__header > div.divider > ul > li:nth-child(2) > a'))
            )
            closed_tab.click()
            closed_tab_parent = closed_tab.find_element(by=By.XPATH, value='..')
            if closed_tab_parent.get_attribute('class') == '':
                closed_tab_parent.click()
            na = 1
        except Exception as e:
            print(f"Error closed value: {e}")
    else:
        print(f"problem in na")            
    
    driver.find_element(by=By.CLASS_NAME, value=f'btn-{signal}').click()
    print(f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S')} {signal.upper()}, currency: {CURRENCY} signal price: {signal_price}")
    time.sleep(PERIOD+3)
    deposit = driver.find_element(by=By.CSS_SELECTOR, value='body > div.wrapper > div.wrapper__top > header > div.right-block.js-right-block > div.right-block__item.js-drop-down-modal-open > div > div.balance-info-block__data > div.balance-info-block__balance > span')
    in_deposit = float(deposit.text.replace(',', ''))
    closed_trades = driver.find_elements(by=By.CLASS_NAME, value='deals-list__item')
    if closed_trades:
            last_split = closed_trades[0].text.split('\n')
            print("Last Split:", last_split)
            amount_won = last_split[4].replace('$', '').strip() 
            try:
                amount = WebDriverWait(driver, 10).until(
                EC.element_to_be_clickable((By.CSS_SELECTOR, '#put-call-buttons-chart-1 > div > div.blocks-wrap > div.block.block--bet-amount > div.block__control.control > div.control__value.value.value--several-items > div > input[type=text]'))
                )

                dep = in_deposit / 10 
                if amount_won == '0':  # If loss, move to the next Martingale value
                        next_amount = previous_amount * 2
                        previous_amount = next_amount
                        tradeprofit -= float(last_split[2].replace('$', '').strip())
                        print(f"trading profit:{tradeprofit}")
                else:  # If win, reset to the first value
                    next_amount = previous_amount
                    previous_amount = next_amount
                    tradeprofit += float(amount_won)
                    print(f"trading profit:{tradeprofit}")
                
                if dep < next_amount : 
                    next_amount = dep
                if next_amount < 1 :
                    next_amount = 1   
                print(f"Next Trade amount: {next_amount}") 
                amount.click()
                base = '#modal-root > div > div > div > div > div.trading-panel-modal__in > div.virtual-keyboard > div > div:nth-child(%s) > div'
                for char in str(next_amount):
                    driver.find_element(by=By.CSS_SELECTOR, value=base % NUMBERS[char]).click()
                    hand_delay()
                amount.click()
                previous_amount = next_amount
            except Exception as e:
                print(f"Error updating amount: {e}")           
def calculate_ema(candles, period):
    prices = [candle['close'] for candle in candles[-period:]]
    ema = sum(prices) / len(prices)  # Simple average for initial calculation
    multiplier = 2 / (period + 1)
    for price in prices[1:]:
        ema = (price - ema) * multiplier + ema
    return ema
def calculate_heiken_ashi(candles):
    heiken_ashi_candles = []
    for i in range(len(candles)):
        if i == 0:
            ha_open = (candles[i]['open'] + candles[i]['close']) / 2
            ha_close = (candles[i]['open'] + candles[i]['high'] + candles[i]['low'] + candles[i]['close']) / 4
        else:
            ha_open = (heiken_ashi_candles[-1]['open'] + heiken_ashi_candles[-1]['close']) / 2
            ha_close = (candles[i]['open'] + candles[i]['high'] + candles[i]['low'] + candles[i]['close']) / 4
        
        ha_high = max(candles[i]['high'], ha_open, ha_close)
        ha_low = min(candles[i]['low'], ha_open, ha_close)
        
        heiken_ashi_candles.append({
            'time': candles[i]['time'],
            'open': ha_open,
            'high': ha_high,
            'low': ha_low,
            'close': ha_close
        })
    
    return heiken_ashi_candles

def calculate_atr(candles, period=14):
    """Calculate the Average True Range (ATR)."""
    tr_values = []
    for i in range(1, len(candles)):
        high = candles[i]['high']
        low = candles[i]['low']
        prev_close = candles[i - 1]['close']
        tr = max(high - low, abs(high - prev_close), abs(low - prev_close))
        tr_values.append(tr)
    
    atr = sum(tr_values[-period:]) / period
    return atr

def calculate_dynamic_threshold(candles, multiplier=0.5):
    """Calculate a dynamic threshold using ATR."""
    atr = calculate_atr(candles)
    return atr * multiplier  # Multiplier adjusts sensitivity

def identify_trend(candles, min_candles=30, pullback_threshold=0.001):
    recent_candles = candles[-50:]
    trend_direction = None  # 'up', 'down', or 'consolidating'
    trend_count = 0
    
    for i in range(1, len(recent_candles)):
        curr_close = recent_candles[i]['close']
        prev_close = recent_candles[i - 1]['close']
        
        if curr_close > prev_close * (1 + pullback_threshold):  # Uptrend
            if trend_direction == 'up':
                trend_count += 1
            else:
                trend_direction = 'up'
                trend_count = 1
        elif curr_close < prev_close * (1 - pullback_threshold):  # Downtrend
            if trend_direction == 'down':
                trend_count += 1
            else:
                trend_direction = 'down'
                trend_count = 1
        else:  # Consolidating or pullback
            if trend_direction is None:  # No trend identified
                trend_direction = 'consolidating'
            trend_count = 0
        
        # If trend count reaches the minimum required candles
        if trend_count >= min_candles:
            return trend_direction  # Return the trend type ('up', 'down', or 'consolidating')
    
    return trend_direction  # Returns 'consolidating' or None if no trend found



# Global variables to store reversals
def unpredictable_sleep():
    """
    Sleep for a random duration between 10 seconds and 1.5 minutes (90 seconds),
    calculated using a combination of random operations for unpredictability.
    """
    # Generate random base and modifiers
    base_sleep = random.uniform(10, 30)  # Base sleep between 10 and 30 seconds
    modifier = random.uniform(1, 3)     # Multiplier between 1 and 3
    addition = random.uniform(0, 10)    # Additional seconds between 0 and 10

    # Calculate total sleep duration
    total_sleep = base_sleep * modifier + addition

    # Ensure sleep duration doesn't exceed the upper limit (90 seconds)
    total_sleep = min(total_sleep, 60)

    print(f"sleep duration: {total_sleep:.2f} seconds...")
    time.sleep(total_sleep)

# Function to be called on each new candle update, with the updated candles list
def capture_reversal_points(candles):
    global significant_reversals, confirmed_reversals

    # Ensure we have at least 50 candles before processing
    if len(candles) < 50:
        return

    # If this is the first time we're processing, calculate reversals for the first 50 candles
    if len(significant_reversals) == 0 and len(confirmed_reversals) == 0:
        calculate_reversals(candles[:50])
    
    # Update reversals with the new candle
    update_reversals(candles[-1], candles[-2])

# Function to calculate reversals for the initial 50 candles
def calculate_reversals(candles):
    global significant_reversals, confirmed_reversals

    # Iterate through candles (except the first candle)
    for i in range(1, len(candles)):
        current_candle = candles[i]
        prev_candle = candles[i - 1]

        # Check for price reversal condition
        if current_candle['close'] < prev_candle['close']:  # Downward reversal
            reversal_price = current_candle['close']
            significant_reversals[reversal_price] = significant_reversals.get(reversal_price, {'count': 0, 'last_touched': current_candle['time']})
            significant_reversals[reversal_price]['count'] += 1

        elif current_candle['close'] > prev_candle['close']:  # Upward reversal
            reversal_price = current_candle['close']
            significant_reversals[reversal_price] = significant_reversals.get(reversal_price, {'count': 0, 'last_touched': current_candle['time']})
            significant_reversals[reversal_price]['count'] += 1

    # Populate confirmed_reversals
    confirmed_reversals = {price: data for price, data in significant_reversals.items() if data['count'] >= 2}

# Function to update reversals with each new candle
def update_reversals(current_candle, prev_candle):
    global significant_reversals, confirmed_reversals

    # Check for price reversal condition for the new candle
    if current_candle['close'] < prev_candle['close']:  # Downward reversal
        reversal_price = current_candle['close']
        significant_reversals[reversal_price] = significant_reversals.get(reversal_price, {'count': 0, 'last_touched': current_candle['time']})
        significant_reversals[reversal_price]['count'] += 1

    elif current_candle['close'] > prev_candle['close']:  # Upward reversal
        reversal_price = current_candle['close']
        significant_reversals[reversal_price] = significant_reversals.get(reversal_price, {'count': 0, 'last_touched': current_candle['time']})
        significant_reversals[reversal_price]['count'] += 1

    # Filter significant_reversals to store only points with a count > 2 in confirmed_reversals
    confirmed_reversals = {price: data for price, data in significant_reversals.items() if data['count'] >= 2}

if __name__ == "__main__":
    load_web_driver()

    # Start trade_process in the background to continuously check for the stack
    import threading
    trade_thread = threading.Thread(target=trade_process, daemon=True)
    trade_thread.start()

    last_update_time = datetime.now()

    while True:
        try:
            # Update the stack by running websocket_log without sleep
            last_update_time = websocket_log(last_update_time)
            
        except Exception as e:
            print(f"Error: {e}")
