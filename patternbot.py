import base64
import json
import random
import time
from datetime import datetime, timedelta
from selenium.webdriver.common.by import By
from driver import companies, get_driver
import numpy as np
import pandas as pd

BASE_URL = 'https://pocketoption.com'
LENGTH_STACK_MIN = 460
LENGTH_STACK_MAX = 1000
PERIOD = 15
TIME = 1
SMA_LONG = 50
SMA_SHORT = 8
PERCENTAGE = 0.91
check = {}
STACK = {}
ACTIONS = {}
MAX_ACTIONS = 1
ACTIONS_SECONDS = PERIOD - 1
LAST_REFRESH = datetime.now()
CURRENCY = None
CURRENCY_CHANGE = False
CURRENCY_CHANGE_DATE = datetime.now()
HISTORY_TAKEN = False
closeD_TRADES_LENGTH = 3
MODEL = None
SCALER = None
PREVIOUS = 1200
MAX_DEPOSIT = 0
MIN_DEPOSIT = 0
INIT_DEPOSIT = None
NUMBERS = {'0': '11', '1': '7', '2': '8', '3': '9', '4': '4', '5': '5', '6': '6', '7': '1', '8': '2', '9': '3','.':'10'}
IS_AMOUNT_SET = True
AMOUNTS = []
EARNINGS = 15
MARTINGALE_COEFFICIENT = 2.0
CURRENT_INDEX = 0  # Track current Martingale index
tradeprofit = 0
test = 0
signal1 = 0
amount_won = 0
na = 0
elapsed_time = 1
start_time = time.time()
ready_to_trade = False
lv_values = {}
driver = get_driver()
previous_amount = 1
values = {}
signal2 = 0
trial = False
result=[]
signal = 'Hold'
iter = 0

def load_web_driver():
    url = f'{BASE_URL}/en/cabinet/demo-quick-high-low/'
    driver.get(url)

def main():
    load_web_driver()
    while True:
        try:
            stack = websocket_log(STACK)
           
            if tradeprofit > 20:
                print(f"trading profit reached:{tradeprofit}")
                globals().clear()
                del stack
                exit()
            deposit = driver.find_element(by=By.CSS_SELECTOR, value='body > div.wrapper > div.wrapper__top > header > div.right-block.js-right-block > div.right-block__item.js-drop-down-modal-open > div > div.balance-info-block__data > div.balance-info-block__balance > span')
            INIT_DEPOSIT = get_deposit_value(deposit)
            if INIT_DEPOSIT < 1:
                print(f"Balance reached: Low")
                globals().clear()
                del stack
                exit()
            time.sleep(5)
        except Exception as e:
            print(f"Error: {e}")
            time.sleep(5)

def hand_delay():
    time.sleep(random.choice([0.2, 0.3, 0.4, 0.5, 0.6,1]))

def get_deposit_value(deposit):
    return float(deposit.text.replace(',', ''))

def can_trade():
    global ready_to_trade,elapsed_time
    
    if not ready_to_trade:
        elapsed_time = time.time() - start_time
        if elapsed_time >= 5 * 60:  # 5 minutes
            ready_to_trade = True
    print(f"Analyzing.. Please wait till:{elapsed_time}")
    return ready_to_trade

import pandas as pd
from datetime import datetime, timedelta

def generate_candles(stack, interval='15s'):
    """
    Converts raw price data into OHLC candles with generated timestamps.

    Args:
        stack (dict): STACK containing raw price data.
                      E.g., {0: price1, 1: price2, ...}.
        interval (str): Resampling interval (e.g., '15s' for 15 seconds).

    Returns:
        pd.DataFrame: DataFrame with OHLC candles.
    """
    # Extract price data
    prices = list(stack.values())
    
    # Generate timestamps assuming 1-second intervals
    current_time = datetime.now()
    timestamps = [current_time - timedelta(seconds=len(prices) - i - 1) for i in range(len(prices))]
    
    # Create a DataFrame with generated timestamps and prices
    data = pd.DataFrame({'timestamp': timestamps, 'price': prices})
    
    # Set 'timestamp' as the index
    data['timestamp'] = pd.to_datetime(data['timestamp'])
    data.set_index('timestamp', inplace=True)
    
    # Check if data has enough rows for resampling
    if data.empty or len(data) < 2:
        raise ValueError("Insufficient data to generate candles.")
    
    # Resample to create OHLC candles
    try:
        ohlc = data['price'].resample(interval).ohlc()
    except ValueError as e:
        raise ValueError(f"Error during resampling: {e}")
    
    # Check if resampling produced valid candles
    if ohlc.empty:
        raise ValueError("Resampling did not produce any valid candles.")
    
    
    return ohlc


def generate_signal(data):
   # Signal initialization
    signal = 'Hold'

    # Moving Averages
    data['SMA_20'] = data['close'].rolling(window=20).mean()
    data['SMA_50'] = data['close'].rolling(window=50).mean()

    # RSI Calculation
    def calculate_rsi(close, period=14):
        delta = close.diff()
        gain = delta.where(delta > 0, 0).rolling(window=period).mean()
        loss = -delta.where(delta < 0, 0).rolling(window=period).mean()
        rs = gain / loss
        rsi = 100 - (100 / (1 + rs))
        return rsi

    data['RSI'] = calculate_rsi(data['close'])

    # MACD Calculation
    data['EMA_12'] = data['close'].ewm(span=12, adjust=False).mean()
    data['EMA_26'] = data['close'].ewm(span=26, adjust=False).mean()
    data['MACD'] = data['EMA_12'] - data['EMA_26']
    data['Signal_Line'] = data['MACD'].ewm(span=9, adjust=False).mean()

    # Bollinger Bands
    data['BB_Mid'] = data['close'].rolling(window=20).mean()
    data['BB_Upper'] = data['BB_Mid'] + (data['close'].rolling(window=20).std() * 2)
    data['BB_Lower'] = data['BB_Mid'] - (data['close'].rolling(window=20).std() * 2)

    # Candlestick Pattern Detection
    def detect_patterns(data):
        patterns = pd.DataFrame(index=data.index)

        # Bullish Engulfing
        patterns['Bullish_Engulfing'] = (data['close'] > data['open']) & (data['open'].shift(1) > data['close'].shift(1)) & \
                                        (data['open'] < data['close'].shift(1)) & (data['close'] > data['open'].shift(1))

        # Bearish Engulfing
        patterns['Bearish_Engulfing'] = (data['open'] > data['close']) & (data['close'].shift(1) > data['open'].shift(1)) & \
                                        (data['close'] < data['open'].shift(1)) & (data['open'] > data['close'].shift(1))

        # Hammer
        patterns['Hammer'] = ((data['high'] - data['low'] > 3 * (data['open'] - data['close'])) &
                              ((data['close'] - data['low']) / (.001 + data['high'] - data['low']) > 0.6) &
                              ((data['open'] - data['low']) / (.001 + data['high'] - data['low']) > 0.6))

        # Shooting Star
        patterns['Shooting_Star'] = ((data['high'] - data['low'] > 3 * (data['open'] - data['close'])) &
                                     ((data['high'] - data['close']) / (.001 + data['high'] - data['low']) > 0.6) &
                                     ((data['high'] - data['open']) / (.001 + data['high'] - data['low']) > 0.6))

        # Doji
        patterns['Doji'] = (abs(data['open'] - data['close']) <= (data['high'] - data['low']) * 0.1)

        # Morning Star
        patterns['Morning_Star'] = ((data['close'].shift(2) < data['open'].shift(2)) &
                                    (data['close'].shift(1) < data['open'].shift(1)) &
                                    (data['close'] > data['open']) &
                                    (data['open'] > data['close'].shift(1)) &
                                    (data['close'] > data['open'].shift(2)))

        # Evening Star
        patterns['Evening_Star'] = ((data['close'].shift(2) > data['open'].shift(2)) &
                                    (data['close'].shift(1) > data['open'].shift(1)) &
                                    (data['close'] < data['open']) &
                                    (data['open'] < data['close'].shift(1)) &
                                    (data['close'] < data['open'].shift(2)))

        return patterns

    patterns = detect_patterns(data)
    data = pd.concat([data, patterns], axis=1)

    # Signal Generation Logic
    latest = data.iloc[-1]
    
    # Candlestick Patterns
    if latest['Bullish_Engulfing'] or latest['Hammer'] or latest['Morning_Star']:
        signal = 'call'
    elif latest['Bearish_Engulfing'] or latest['Shooting_Star'] or latest['Evening_Star']:
        signal = 'put'

    # RSI
    if latest['RSI'] < 30:
        signal = 'call'
    elif latest['RSI'] > 70:
        signal = 'put'

    # MACD
    if latest['MACD'] > latest['Signal_Line']:
        signal = 'call'
    elif latest['MACD'] < latest['Signal_Line']:
        signal = 'put'

    # Bollinger Bands
    if latest['close'] < latest['BB_Lower']:
        signal = 'call'
    elif latest['close'] > latest['BB_Upper']:
        signal = 'put'

    # Trend Detection (Moving Averages)
    if latest['SMA_20'] > latest['SMA_50']:
        signal = 'call'
    elif latest['SMA_20'] < latest['SMA_50']:
        signal = 'put'

    return signal

def update_stack(stack):
    try:
        for wsData in driver.get_log('performance'):
            message = json.loads(wsData['message'])['message']
            response = message.get('params', {}).get('response', {})
            
            if response.get('opcode', 0) == 2:  # WebSocket message is of type 2 (data)
                payload_str = base64.b64decode(response['payloadData']).decode('utf-8')
                data = json.loads(payload_str)
                
                # Print data to inspect its structure
            
                
                # Check if data has enough elements for unpacking
                if len(data[0]) >= 3:
                    symbol, timestamp, value = data[0]
                else:

                    continue
                
                # Update current symbol (if needed, based on your logic)
                current_symbol = driver.find_element(by=By.CLASS_NAME, value='current-symbol').text
                
                # If the stack reaches the max length, remove the oldest entries based on the period
                if len(stack) == LENGTH_STACK_MAX:
                    first_element = list(stack.keys())[0]
                    if timestamp - first_element > PERIOD:
                        stack = {k: v for k, v in stack.items() if k > timestamp - LENGTH_STACK_MIN}
                
                # Add the new timestamp and value to the stack
                stack[timestamp] = value

    except Exception as e:
        print(f"Error in updating stack: {e}")
    
    return stack

def update_result(amount):
    global result
    # Add the new item at the beginning
    result.insert(0, amount)
    # Ensure the list length does not exceed 20
    if len(result) > 20:
        result.pop()  # Remove the last item

def websocket_log(stack):
    global CURRENCY,symbol, CURRENCY_CHANGE, CURRENCY_CHANGE_DATE,trial, LAST_REFRESH, HISTORY_TAKEN, MODEL, INIT_DEPOSIT
    
    try:
        current_symbol = driver.find_element(by=By.CLASS_NAME, value='current-symbol').text
        if current_symbol != CURRENCY:
            CURRENCY = current_symbol
            CURRENCY_CHANGE = True
            CURRENCY_CHANGE_DATE = datetime.now()
    except:
        pass
    
    if CURRENCY_CHANGE and CURRENCY_CHANGE_DATE < datetime.now() - timedelta(seconds=5):
        stack = {}
        HISTORY_TAKEN = False
        driver.refresh()
        CURRENCY_CHANGE = False
        MODEL = None
        INIT_DEPOSIT = None

    for wsData in driver.get_log('performance'):
        message = json.loads(wsData['message'])['message']
        response = message.get('params', {}).get('response', {})
        if response.get('opcode', 0) == 2 and not CURRENCY_CHANGE:
            payload_str = base64.b64decode(response['payloadData']).decode('utf-8')
            data = json.loads(payload_str)
            if not HISTORY_TAKEN:
                if 'history' in data and data['history']:
                    stack = {int(d[0]): d[1] for d in data['history']}
                    print(f"History taken for asset: {data['asset']}, period: {data['period']}, len_history: {len(data['history'])}, len_stack: {len(stack)}")
            try:
                current_symbol = driver.find_element(by=By.CLASS_NAME, value='current-symbol').text
                symbol, timestamp, value = data[0]
            except:
                continue
            if len(stack) == LENGTH_STACK_MAX:
                first_element = list(stack.keys())[0]
                if timestamp - first_element > PERIOD:
                    stack = {k: v for k, v in stack.items() if k > timestamp - LENGTH_STACK_MIN}
            stack[timestamp] = value
        trial = check_values(stack)
        if trial == False:
                return stack

    return stack

def check_values(stack):
    global ready_to_trade, signal, signal1, IS_AMOUNT_SET, AMOUNTS, INIT_DEPOSIT, amount_won, tradeprofit, previous_amount, na, dep
    global ACTIONS, IS_AMOUNT_SET, test, test1, lv1, lv2, lv3, lv4, lv5, lv6, t, lv, signal2, iter, iter1
    last_value = 0   
    try:
        if not STACK:
            return
        last_value = list(STACK.values())[-1]
    except Exception as e:
        print(f"Error fetching last value from stack: {e}")
        return
    try:
        deposit = driver.find_element(by=By.CSS_SELECTOR, value='body > div.wrapper > div.wrapper__top > header > div.right-block.js-right-block > div.right-block__item.js-drop-down-modal-open > div > div.balance-info-block__data > div.balance-info-block__balance > span')
    except Exception as e:
        print(f"Error fetching deposit value: {e}")

    time_style = driver.find_element(by=By.CSS_SELECTOR, value='#put-call-buttons-chart-1 > div > div.blocks-wrap > div.block.block--expiration-inputs > div.block__control.control > div.control-buttons__wrapper > div > a > div > div > svg')
    if 'exp-mode-2.svg' in time_style.get_attribute('data-src'):
        time_style.click()

    if na == 0:
         
           next_amount=1
           amount = driver.find_element(by=By.CSS_SELECTOR, value='#put-call-buttons-chart-1 > div > div.blocks-wrap > div.block.block--bet-amount > div.block__control.control > div.control__value.value.value--several-items > div > input[type=text]')
           amount.click()
           base = '#modal-root > div > div > div > div > div.trading-panel-modal__in > div.virtual-keyboard > div > div:nth-child(%s) > div'
           for number in str(next_amount):
                    driver.find_element(by=By.CSS_SELECTOR, value=base % NUMBERS[number]).click()
                    hand_delay()
                    na = 1
        
    if not INIT_DEPOSIT:
        INIT_DEPOSIT = get_deposit_value(deposit)

    if not IS_AMOUNT_SET:
        if ACTIONS and list(ACTIONS.keys())[-1] + timedelta(seconds=PERIOD + 5) > datetime.now():
            return

        try:
            closed_tab = driver.find_element(by=By.CSS_SELECTOR, value='#bar-chart > div > div > div.right-widget-container > div > div.widget-slot__header > div.divider > ul > li:nth-child(2) > a')
            closed_tab_parent = closed_tab.find_element(by=By.XPATH, value='..')
            if closed_tab_parent.get_attribute('class') == '':
                closed_tab_parent.click()
        except:
            pass

        closed_trades = driver.find_elements(by=By.CLASS_NAME, value='deals-list__item')
        if closed_trades:
            last_split = closed_trades[0].text.split('\n')
            print("Last Split:", last_split)
            amount_won = last_split[4].replace('$', '').strip()
            update_result(amount_won)

            try:
                amount = driver.find_element(by=By.CSS_SELECTOR, value='#put-call-buttons-chart-1 > div > div.blocks-wrap > div.block.block--bet-amount > div.block__control.control > div.control__value.value.value--several-items > div > input[type=text]')
                if amount_won == '0':  # If loss, move to the next Martingale value
                        iter = iter + 1
                        if iter == 2: 
                            iter = 0    
                        next_amount = previous_amount * 1.5
                        tradeprofit -= float(last_split[2].replace('$', '').strip())
                        print(f"trading profit:{tradeprofit}")
                else:  # If win, reset to the first value
                    next_amount = previous_amount *1.2
                    tradeprofit += float(amount_won)
                    print(f"trading profit:{tradeprofit}")
                dep = INIT_DEPOSIT/10
                if dep < next_amount : 
                    next_amount = 1
                if next_amount < 1 :
                    next_amount = 1  
                  
                next_amount = round(next_amount)
                if round(previous_amount) != next_amount:
                 amount.click()
                 base = '#modal-root > div > div > div > div > div.trading-panel-modal__in > div.virtual-keyboard > div > div:nth-child(%s) > div'
                 for number in str(next_amount):
                    driver.find_element(by=By.CSS_SELECTOR, value=base % NUMBERS[number]).click()
                    hand_delay()
                previous_amount = next_amount

                print(f"Next Trade amount: {next_amount}")
            except Exception as e:
                print(f"Error updating amount: {e}")
                     
        IS_AMOUNT_SET = True

    if IS_AMOUNT_SET and datetime.now().second % 10 == 0:
       values = list(stack.values())
       candles = generate_candles(STACK)
      
       signal = generate_signal(candles)
    else:
        return    
    print(f"detected signal:{signal}")
    signal1 = list(stack.values())[-1]
    if signal1 == signal2 : 
       if amount_won != 0: 
           print(f"signal already executed")
           update_stack(stack)
           return
    signal2 = signal1
    
    action = True
    
    for dat in list(ACTIONS.keys()):
        if dat < datetime.now() - timedelta(seconds=ACTIONS_SECONDS):
            del ACTIONS[dat]

    if action and len(ACTIONS) >= MAX_ACTIONS:
        action = False

    if action and ACTIONS:
        if signal == 'call' and last_value >= min(list(ACTIONS.values())):
            action = False
        elif signal == 'put' and last_value <= max(list(ACTIONS.values())):
            action = False
        elif signal == 'Hold':
            print(f"Signals to Hold... Please wait")
            return 
    if action:
        try:
            
            test1 = 0
            if signal == 'Hold':
                       print(f"signals to Hold.checking next signal")
                       test1 = test1+1
            print(f"Signal Value:{last_value}")
            if signal == 'call': 
              if iter == 1: 
                 signal = 'put'
              if test1 == 0 :
                 driver.find_element(by=By.CLASS_NAME, value=f'btn-{signal}').click()
                 ACTIONS[datetime.now()] = last_value
                 IS_AMOUNT_SET = False
                 print(f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S')} {signal.upper()}, currency: {CURRENCY} last_value: {last_value}")
                 test1 = test1+1
                 
            elif signal == 'put':
              if iter == 1:
                 signal = 'call'
              if test1 == 0:
                 driver.find_element(by=By.CLASS_NAME, value=f'btn-{signal}').click()
                 ACTIONS[datetime.now()] = last_value
                 IS_AMOUNT_SET = False
                 print(f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S')} {signal.upper()}, currency: {CURRENCY} last_value: {last_value}")
                 test1 = test1+1
                 
            signal = 'Hold'
            last_value=0    

        except Exception as e:
          print(f"Error during action execution: {e}")
        time.sleep(5)

    return True

if __name__ == '__main__':
    main()