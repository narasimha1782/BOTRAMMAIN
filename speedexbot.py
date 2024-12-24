import base64
import json
import random
import time
from datetime import datetime, timedelta
from selenium.webdriver.common.by import By
from driver import companies, get_driver

BASE_URL = 'https://pocketoption.com'
LENGTH_STACK_MIN = 460
LENGTH_STACK_MAX = 1000
PERIOD = 15
TIME = 1
SMA_LONG = 50
SMA_SHORT = 8
PERCENTAGE = 0.91
STACK = {}
ACTIONS = {}
MAX_ACTIONS = 1
ACTIONS_SECONDS = PERIOD - 1
LAST_REFRESH = datetime.now()
CURRENCY = None
CURRENCY_CHANGE = False
CURRENCY_CHANGE_DATE = datetime.now()
HISTORY_TAKEN = False
CLOSED_TRADES_LENGTH = 3
MODEL = None
SCALER = None
PREVIOUS = 1200
MAX_DEPOSIT = 0
MIN_DEPOSIT = 0
INIT_DEPOSIT = None
NUMBERS = {'0': '11', '1': '7', '2': '8', '3': '9', '4': '4', '5': '5', '6': '6', '7': '1', '8': '2', '9': '3'}
IS_AMOUNT_SET = True
AMOUNTS = []
EARNINGS = 15
MARTINGALE_COEFFICIENT = 2.0
CURRENT_INDEX = 0  # Track current Martingale index
tradeprofit = 0
test = 0
signal1 = 'c'
amount_won = 0
driver = get_driver()

def load_web_driver():
    url = f'{BASE_URL}/en/cabinet/demo-quick-high-low/'
    driver.get(url)
def update_stack(stack):
    global CURRENCY, CURRENCY_CHANGE, CURRENCY_CHANGE_DATE, LAST_REFRESH, HISTORY_TAKEN, MODEL, INIT_DEPOSIT
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
         
    return stack

def websocket_log(stack):
    global CURRENCY, CURRENCY_CHANGE, CURRENCY_CHANGE_DATE, LAST_REFRESH, HISTORY_TAKEN, MODEL, INIT_DEPOSIT
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
            check_values(stack)
    return stack

def change_currency():
    current_symbol = driver.find_element(by=By.CLASS_NAME, value='current-symbol')
    current_symbol.click()
    currencies = driver.find_elements(By.XPATH, "//li[contains(., '92%')]")
    if currencies:
        while True:
            currency = random.choice(currencies)
            if CURRENCY not in currency.text:
                break
        currency.click()
 
def do_action(signal):
    global signal1

    if signal1 == signal: 
       if amount_won != 0: 
           print(f"signal already executed")
           return
    signal1 = signal
    print(f"detected signal: {signal}")
    action = True
    try:
        if not STACK:
            return
        last_value = list(STACK.values())[-1]
    except Exception as e:
        print(f"Error fetching last value from stack: {e}")
        return

    global ACTIONS, IS_AMOUNT_SET, test, test1, lv1, lv2, lv3, lv4, lv5, lv6, t
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
    
    if action:
        try:
            print(f"Signal Value:{last_value}")
            stack = update_stack(STACK)
            last_value1 = list(stack.values())[-1] 
            lv1 = last_value1
            print(f"Last Value:{last_value1}")
            stack = update_stack(STACK)
            last_value1 = list(stack.values())[-1]
            lv2 = last_value1
            t= True
            while True:
                if lv2 == lv1 :
                 stack = update_stack(STACK)
                 last_value1 = list(stack.values())[-1] 
                 lv2 = last_value1
                else:
                 print(f"Last Value:{lv2}")
                 t= False
                 break
            stack = update_stack(STACK)
            last_value1 = list(stack.values())[-1]
            lv3 = last_value1
            t= True
            while True:
                if lv3 == lv2 :
                 stack = update_stack(STACK)
                 last_value1 = list(stack.values())[-1] 
                 lv3 = last_value1
                else:
                 print(f"Last Value:{lv3}")
                 t= False
                 break
            stack = update_stack(STACK)
            last_value1 = list(stack.values())[-1] 
            lv4 = last_value1
            t= True
            while True:
                if lv4 == lv3 :
                 stack = update_stack(STACK)
                 last_value1 = list(stack.values())[-1] 
                 lv4 = last_value1
                else:
                 print(f"Last Value:{lv4}")
                 t= False
                 break           
            stack = update_stack(STACK)
            last_value1 = list(stack.values())[-1]
            lv5 = last_value1
            t= True
            while True:
                if lv5 == lv4 :
                 stack = update_stack(STACK)
                 last_value1 = list(stack.values())[-1] 
                 lv5 = last_value1
                else:
                 print(f"Last Value:{lv5}")
                 t= False
                 break
            stack = update_stack(STACK)
            last_value1 = list(stack.values())[-1]
            lv6 = last_value1
            t= True
            while True:
                if lv6 == lv5 :
                 stack = update_stack(STACK)
                 last_value1 = list(stack.values())[-1] 
                 lv6 = last_value1
                else:
                 print(f"Last Value:{lv6}")
                 t= False
                 test1 = 0
                 break
                  
            
            if signal == 'call' and lv6 > lv3 : 
              if test1 == 0 :
                driver.find_element(by=By.CLASS_NAME, value=f'btn-{signal}').click()
                ACTIONS[datetime.now()] = last_value
                IS_AMOUNT_SET = False
                print(f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S')} {signal.upper()}, currency: {CURRENCY} last_value: {last_value}")
                test1 = test1+1
            else:
              if test1 == 0:
                signal = 'put'
                driver.find_element(by=By.CLASS_NAME, value=f'btn-{signal}').click()
                ACTIONS[datetime.now()] = last_value
                IS_AMOUNT_SET = False
                print(f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S')} {signal.upper()}, currency: {CURRENCY} last_value: {last_value}")
                test1 = test1+1
            if signal == 'put' and lv6 < lv3:
              if test1 == 0:
                driver.find_element(by=By.CLASS_NAME, value=f'btn-{signal}').click()
                ACTIONS[datetime.now()] = last_value
                IS_AMOUNT_SET = False
                print(f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S')} {signal.upper()}, currency: {CURRENCY} last_value: {last_value}")
                test1 = test1+1
            else:
              if test1 == 0:
                signal = 'buy'
                driver.find_element(by=By.CLASS_NAME, value=f'btn-{signal}').click()
                ACTIONS[datetime.now()] = last_value
                IS_AMOUNT_SET = False
                print(f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S')} {signal.upper()}, currency: {CURRENCY} last_value: {last_value}")
                test1 = test1+1
        except Exception as e:
          print(f"Error during action execution: {e}")
        time.sleep(30)
     
def hand_delay():
    time.sleep(random.choice([0.2, 0.3, 0.4, 0.5, 0.6,1]))

def get_amounts(amount):
    return [1,3,9]

def get_deposit_value(deposit):
    return float(deposit.text.replace(',', ''))

def check_values(stack):
    try:
        deposit = driver.find_element(by=By.CSS_SELECTOR, value='body > div.wrapper > div.wrapper__top > header > div.right-block.js-right-block > div.right-block__item.js-drop-down-modal-open > div > div.balance-info-block__data > div.balance-info-block__balance > span')
    except Exception as e:
        print(f"Error fetching deposit value: {e}")

    time_style = driver.find_element(by=By.CSS_SELECTOR, value='#put-call-buttons-chart-1 > div > div.blocks-wrap > div.block.block--expiration-inputs > div.block__control.control > div.control-buttons__wrapper > div > a > div > div > svg')
    if 'exp-mode-2.svg' in time_style.get_attribute('data-src'):
        time_style.click()

    global IS_AMOUNT_SET, AMOUNTS, INIT_DEPOSIT, CURRENT_INDEX, amount_won, tradeprofit
     
    if not INIT_DEPOSIT:
        INIT_DEPOSIT = get_deposit_value(deposit)

    if not AMOUNTS:
        AMOUNTS = get_amounts(get_deposit_value(deposit))

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
            
            try:
                amount = driver.find_element(by=By.CSS_SELECTOR, value='#put-call-buttons-chart-1 > div > div.blocks-wrap > div.block.block--bet-amount > div.block__control.control > div.control__value.value.value--several-items > div > input[type=text]')
                if amount_won == '0':  # If loss, move to the next Martingale value
                    if CURRENT_INDEX + 1 < 3:
                        CURRENT_INDEX += 1
                        tradeprofit -= float(last_split[2].replace('$', '').strip())
                        print(f"trading profit:{tradeprofit}")
                    else:
                        tradeprofit -= float(last_split[2].replace('$', '').strip())
                        print(f"trading profit:{tradeprofit}")
                        print("Resetting to initial Martingale level after 3 steps.")
                        CURRENT_INDEX = 0
                else:  # If win, reset to the first value
                    CURRENT_INDEX = 0
                    tradeprofit += float(amount_won)
                    print(f"trading profit:{tradeprofit}")
                next_amount = AMOUNTS[CURRENT_INDEX]
                amount.click()
                base = '#modal-root > div > div > div > div > div.trading-panel-modal__in > div.virtual-keyboard > div > div:nth-child(%s) > div'
                for number in str(next_amount):
                    driver.find_element(by=By.CSS_SELECTOR, value=base % NUMBERS[number]).click()
                    hand_delay()
                print(f"Next Martingale amount set: {next_amount}")
            except Exception as e:
                print(f"Error updating amount: {e}")
        IS_AMOUNT_SET = True

    if IS_AMOUNT_SET and datetime.now().second % 10 == 0:
        values = list(stack.values())
        if len(values) >= PERIOD * 2:
            if values[-1] < values[-1 - PERIOD] < values[-1 - PERIOD * 2]:
                do_action('put')
            elif values[-1] > values[-1 - PERIOD] > values[-1 - PERIOD * 2]:
                do_action('call')

if __name__ == '__main__':
    load_web_driver()
    while True:
        try:
            if tradeprofit > 20:
                print(f"trading profit reached:{tradeprofit}")
                exit()
             
            stack = websocket_log(STACK)
            
            time.sleep(30)
        except Exception as e:
            print(f"Error: {e}")
            time.sleep(30)
