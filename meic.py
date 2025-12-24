import requests as r
import os
import logging
from dotenv import load_dotenv, dotenv_values
import json
from dataclasses import dataclass
import time
from typing import List, Optional
import re
from datetime import date

# LOAD ENV Variables
load_dotenv()
API_KEY = os.environ.get("API_KEY")
ACCOUNT_ID = os.environ.get("ACCOUNT_ID")



from dataclasses import dataclass
from typing import List, Optional


# -----------------------------
# Supporting nested structures
# -----------------------------

@dataclass
class BuyingPower:
    cashOnlyBuyingPower: float
    buyingPower: float
    optionsBuyingPower: float

    @staticmethod
    def from_dict(d: dict) -> "BuyingPower":
        return BuyingPower(
            cashOnlyBuyingPower=float(d["cashOnlyBuyingPower"]),
            buyingPower=float(d["buyingPower"]),
            optionsBuyingPower=float(d["optionsBuyingPower"])
        )


@dataclass
class EquitySlice:
    type: str
    value: float
    percentageOfPortfolio: float

    @staticmethod
    def from_dict(d: dict) -> "EquitySlice":
        return EquitySlice(
            type=d["type"],
            value=float(d["value"]),
            percentageOfPortfolio=float(d["percentageOfPortfolio"])
        )


@dataclass
class LastPrice:
    lastPrice: float
    timestamp: Optional[str]

    @staticmethod
    def from_dict(d: dict) -> "LastPrice":
        return LastPrice(
            lastPrice=float(d["lastPrice"]),
            timestamp=d["timestamp"]
        )


@dataclass
class Gain:
    gainValue: float
    gainPercentage: float
    timestamp: Optional[str]

    @staticmethod
    def from_dict(d: dict) -> "Gain":
        return Gain(
            gainValue=float(d["gainValue"]),
            gainPercentage=float(d["gainPercentage"]),
            timestamp=d["timestamp"]
        )


@dataclass
class CostBasis:
    totalCost: float
    unitCost: float
    gainValue: float
    gainPercentage: float
    lastUpdate: str

    @staticmethod
    def from_dict(d: dict) -> "CostBasis":
        return CostBasis(
            totalCost=float(d["totalCost"]),
            unitCost=float(d["unitCost"]),
            gainValue=float(d["gainValue"]),
            gainPercentage=float(d["gainPercentage"]),
            lastUpdate=d["lastUpdate"]
        )


# -----------------------------
# Position object
# -----------------------------

@dataclass
class PortfolioPosition:
    instrument: Instrument
    quantity: float
    openedAt: str
    currentValue: float
    percentOfPortfolio: float
    lastPrice: LastPrice
    instrumentGain: Gain
    positionDailyGain: Gain
    costBasis: CostBasis

    @staticmethod
    def from_dict(d: dict) -> "PortfolioPosition":
        return PortfolioPosition(
            instrument=Instrument(
                symbol=d["instrument"]["symbol"],
                type=d["instrument"]["type"],
                name=d["instrument"]["name"]
            ),
            quantity=float(d["quantity"]),
            openedAt=d["openedAt"],
            currentValue=float(d["currentValue"]),
            percentOfPortfolio=float(d["percentOfPortfolio"]),
            lastPrice=LastPrice.from_dict(d["lastPrice"]),
            instrumentGain=Gain.from_dict(d["instrumentGain"]),
            positionDailyGain=Gain.from_dict(d["positionDailyGain"]),
            costBasis=CostBasis.from_dict(d["costBasis"])
        )


# -----------------------------
# Top-level Portfolio object
# -----------------------------

@dataclass
class Portfolio:
    accountId: str
    accountType: str
    buyingPower: BuyingPower
    equity: List[EquitySlice]
    positions: List[PortfolioPosition]
    orders: List[dict]
    stock_positions: List[PortfolioPosition]
    option_positions: List[PortfolioPosition]   

    @staticmethod
    def from_dict(d: dict) -> "Portfolio":
        return Portfolio(
            accountId=d["accountId"],
            accountType=d["accountType"],
            buyingPower=BuyingPower.from_dict(d["buyingPower"]),
            equity=[EquitySlice.from_dict(e) for e in d["equity"]],
            positions=[PortfolioPosition.from_dict(p) for p in d["positions"]],
            orders=d["orders"]
        )

    def sort_positons(self):

        self.stock_positions.clear()
        self.option_positions.clear()

        for position in self.positions:
            if position.instrument.type == "EQUITY":
                self.stock_positions.append(position)
            elif position.instrument.type == "OPTION":
                self.option_positions.append(position)


@dataclass
class Greeks:
    symbol: str
    delta: float
    gamma: float
    theta: float
    vega: float
    rho: float
    impliedVolatility: float
    strike: float
    index: int = None

    @staticmethod
    def from_dict(d: dict) -> "Greeks":
        greeks = d["greeks"][0]
        g = greeks["greeks"]

        return Greeks(
            symbol=greeks["symbol"],
            delta=float(g["delta"]),
            gamma=float(g["gamma"]),
            theta=float(g["theta"]),
            vega=float(g["vega"]),
            rho=float(g["rho"]),
            impliedVolatility=float(g["impliedVolatility"]),
            strike = float(parse_option_symbol(greeks["symbol"])['strike'])
        )

@dataclass
class Position:
    instrument: Instrument

@dataclass
class Instrument:
    symbol: str
    type: str
    name: str

    @staticmethod 
    def from_dict(d: dict) -> "Instrument": 
        return Instrument( symbol=d["symbol"], type=d["type"])

@dataclass
class Quote:
    instrument: Instrument
    outcome: str
    last: float
    lastTimestamp: str
    bid: float
    bidSize: int
    bidTimestamp: str
    ask: float
    askSize: int
    askTimestamp: str
    volume: int
    openInterest: int

    @staticmethod 
    def from_dict(d: dict) -> "Quote": 
        return Quote( 
            instrument = Instrument.from_dict(d["instrument"]), 
            outcome = d["outcome"], 
            last = float(d["last"]), 
            lastTimestamp=d["lastTimestamp"], 
            bid=float(d["bid"]), 
            bidSize=d["bidSize"], 
            bidTimestamp=d["bidTimestamp"], 
            ask=float(d["ask"]), 
            askSize=d["askSize"], 
            askTimestamp=d["askTimestamp"], 
            volume=d["volume"], 
            openInterest=d["openInterest"], )

@dataclass
class OptionChain:
    baseSymbol: str
    calls: List[Quote]
    puts: List[Quote]
    call_strikes_count: int
    put_strikes_count: int

    @staticmethod 
    def from_dict(d: dict) -> "OptionChain": 
        return OptionChain( 
            baseSymbol=d["baseSymbol"], 
            calls=[Quote.from_dict(q) for q in d["calls"]], 
            puts=[Quote.from_dict(q) for q in d["puts"]],
            call_strikes_count = len(d["calls"]),
            put_strikes_count = len(d["calls"]) )


def get_quote(instrument: Instrument, account_id: str, api_key: str) -> Quote:
    url = f"https://api.public.com/userapigateway/marketdata/{account_id}/quotes"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }

    request_body = {
        "instruments": [
            {
            "symbol": instrument.symbol,
            "type": instrument.type
            }
        ]
    }   
    response = r.post(url, headers=headers, json=request_body)
    data = response.json()

    quotes = [Quote.from_dict(q) for q in data["quotes"]]
    return quotes[0]





def get_option_chain(instrument: Instrument, account_id: str, api_key: str, expiration_date: str) -> OptionChain:
    url = f"https://api.public.com/userapigateway/marketdata/{account_id}/option-chain"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }

    request_body = {
        "instrument": {
            "symbol": instrument.symbol,
            "type": instrument.type
        },
        "expirationDate": expiration_date
    }

    response = r.post(url, headers=headers, json=request_body)
    data = response.json()
    return OptionChain.from_dict(data)






def parse_option_symbol(symbol: str):

    pattern = re.compile(r'^([A-Z]+)(\d{6})([CP])(\d{8})$')
    match = pattern.match(symbol)
    if not match:
        raise ValueError(f"Invalid option symbol: {symbol}")

    underlying, date, cp_flag, strike = match.groups()

    return {
        "symbol": symbol,
        "underlying": underlying,
        "expiration": date,
        "type": cp_flag,
        "strike_raw": strike,
        "strike": int(strike) / 1000  # optional: convert to real strike
    }

def get_greeks(symbol: str, account_id: str, api_key: str) -> Greeks:
    url = f"https://api.public.com/userapigateway/option-details/{account_id}/greeks"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }

    params = {"osiSymbols": symbol}

    response = r.get(url, headers=headers, params=params)

    # Debug output
    if response.status_code != 200:
        print("STATUS:", response.status_code)
        print("URL:", response.url)
        print("RAW:", response.text)

    # Try to parse JSON
    try:
        data = response.json()
    except ValueError:
        raise RuntimeError(f"API did not return JSON. Status={response.status_code}, Body={response.text}")

    return Greeks.from_dict(data)



def get_short_strike(option_chain: OptionChain, option_type: str, starting_index: int, expected_move: int):
    keep_searching = True
    scaling_factor = 1
    option_chains = option_chain.calls
    if option_type == "PUT":
        # print("Fetching Short PUT strike")
        scaling_factor = -1
        option_chains = option_chain.puts

    i = starting_index + (scaling_factor * expected_move)
    max_search = 5
    while keep_searching:
        option_strike = option_chains[i]
        strike = parse_option_symbol(option_strike.instrument.symbol)['strike']
        # print(f"Fetching greeks for {option_type} at strike {strike}")
        greeks = get_greeks(option_strike.instrument.symbol, ACCOUNT_ID, API_KEY)        
        if abs(greeks.delta) > .10 and max_search >= 0:
            # print(f"{option_type} {strike}: delta too large at {abs(greeks.delta)}")            
            keep_searching = True
            i += (1*scaling_factor)
            max_search -= 1
        elif abs(greeks.delta) <= .05 and max_search >= 0:
            # print(f"{option_type} {strike}: delta too small at {abs(greeks.delta)}") 
            keep_searching = True
            i -= (1*scaling_factor)
            max_search -= 1
        else:
            keep_searching = False
            
    print(f"Found Short {option_type} at {greeks.strike} at delta {greeks.delta} ({greeks.symbol})")
    greeks.index = i
    return greeks



def get_atm_strike_index(option_type: str, last_price: float, ticker_option_chain: OptionChain, starting_index: int) -> int:
    keep_searching = True
    return_index = starting_index
    max_search_count = 5
    abs_diff = 1
    strike_price = None

    if option_type == "CALL":
        # print("Fetching ATM CALL strike")
        while keep_searching:
            strike_price = float(parse_option_symbol(ticker_option_chain.calls[return_index].instrument.symbol)['strike'])
            abs_diff = 1
            if 0.00 <= strike_price - last_price <= 0.99:
                keep_searching = False
            elif strike_price - last_price > 1.00:
                #print(f"{option_type} {strike_price} is too far above {last_price}")
                if strike_price - last_price > 3.00:
                    abs_diff = round(abs(strike_price - last_price)) - 1
                return_index -= (1 * abs_diff)
            else:
                #print(f"{option_type} {strike_price} is too far bellow {last_price}")                
                if last_price - strike_price > 3.0:
                    abs_diff = round(abs(last_price - strike_price)) - 1
                return_index += (1 * abs_diff)

            max_search_count -= 1
            if max_search_count < 0:
                keep_searching = False
    else:
        # print("Fetching ATM PUT strike")
        while keep_searching:
            strike_price = float(parse_option_symbol(ticker_option_chain.puts[return_index].instrument.symbol)['strike'])
            abs_diff = 1
            if 0.00 <= (last_price - strike_price) <= 0.999:
                keep_searching = False
            elif last_price - strike_price > 1.00:
                # print(f"{option_type} {strike_price} is too far bellow {last_price}")
                if last_price - strike_price > 3.00:
                    abs_diff = round(abs(last_price - strike_price)) - 1
                return_index += (1 * abs_diff)
            else:
                # print(f"{option_type} {strike_price} is too far above {last_price}")
                if strike_price - last_price > 3.00:
                    abs_diff = round(abs(strike_price - last_price)) - 1
                return_index -= (1 * abs_diff) 

            max_search_count -= 1
            if max_search_count < 0:
                keep_searching = False
  
    print(f"Found ATM strike of {option_type} at {strike_price}")
    return return_index

def run_trade_pre_flight(account_id: str, api_key: str,  short_symbol: str, long_symbol: str, quantity: int, limit_price: float, option_type: str):
    print(f"Running pre-flight on short {short_symbol} and long {long_symbol} {option_type}'s")
    url = f"https://api.public.com/userapigateway/trading/{account_id}/preflight/multi-leg"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }

    request_body = {
            "orderType": "LIMIT",
            "expiration": {
            "timeInForce": "DAY"
            },
            "quantity": "1",
            "limitPrice": "1.00",
            "legs": [
                {
                    "instrument": {
                    "symbol": long_symbol,
                    "type": "OPTION"
                    },
                    "side": "BUY",
                    "openCloseIndicator": "OPEN",
                    "ratioQuantity": 1
                },
                {
                    "instrument": {
                    "symbol": short_symbol,
                    "type": "OPTION"
                    },
                    "side": "SELL",
                    "openCloseIndicator": "OPEN",
                    "ratioQuantity": 1
                }
            ]
    }

    response = r.post(url, headers=headers, json=request_body)

    # Debug output
    if response.status_code != 200:
        print("STATUS:", response.status_code)
        print("URL:", response.url)
        print("RAW:", response.text)

    # Try to parse JSON
    try:
        data = response.json()
    except ValueError:
        raise RuntimeError(f"API did not return JSON. Status={response.status_code}, Body={response.text}")

    print(data)


def get_account_portfolio(account_id: str, api_key: str) -> Portfolio:
    url = f"https://api.public.com/userapigateway/trading/{account_id}/portfolio/v2"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }

    response = requests.get(url, headers=headers)
    data = response.json()
    return Portfolio.from_dict(data)

ticker = Instrument('SPY','EQUITY')
EXPECTED_MOVE = 2
today = "2025-12-24" #date.today().strftime("%Y-%m-%d")
print(f"Starting 0 DTE trading for {today}")
for i in range(1):
    ticker_quote = get_quote(ticker, ACCOUNT_ID, API_KEY)
    print(f"{ticker_quote.instrument.symbol}: last price {ticker_quote.last}")
    ticker_option_chain = get_option_chain(ticker, ACCOUNT_ID, API_KEY, today)
    
    # starting roughly in the middle of the options chain
    atm_call_index = get_atm_strike_index("CALL", ticker_quote.last, ticker_option_chain, 62) #62 #qqq_option_chain.call_strikes_count // 2
    atm_put_index = get_atm_strike_index("PUT", ticker_quote.last, ticker_option_chain, 61) #qqq_option_chain.put_strikes_count // 2
        
    # sanity check
    # ATM strikes should be no more than $1 away from each other, and current price should be between them
    atm_call_strike = float(parse_option_symbol(ticker_option_chain.calls[atm_call_index].instrument.symbol)['strike'])
    atm_put_strike = float(parse_option_symbol(ticker_option_chain.puts[atm_put_index].instrument.symbol)['strike'])
    if atm_call_strike - atm_put_strike > 1.0 or ticker_quote.last > atm_call_strike or ticker_quote.last < atm_put_strike:
        print("ERROR: Call and Puts too far aways")

    # Get short strikes based on delta rules (between .04 and .10)
    call_greeks = get_short_strike(ticker_option_chain, "CALL", atm_call_index, EXPECTED_MOVE)
    put_greeks = get_short_strike(ticker_option_chain, "PUT", atm_put_index, EXPECTED_MOVE)

    # we are trading 2 dollar wide spreads so...
    short_call_symbol = ticker_option_chain.calls[call_greeks.index].instrument.symbol
    long_call_symbol = ticker_option_chain.calls[call_greeks.index + 2].instrument.symbol
    short_put_symbol = ticker_option_chain.calls[put_greeks.index].instrument.symbol
    long_put_symbol = ticker_option_chain.calls[put_greeks.index - 2].instrument.symbol

    print(f"Short Call strike {call_greeks.symbol} at delta of {call_greeks.delta} || Short: {short_call_symbol} Long: {long_call_symbol}")
    #run_trade_pre_flight(ACCOUNT_ID, API_KEY, short_call_symbol, long_call_symbol, 1, 1.0, "CALL")
    print(f"Short PUT strike {put_greeks.symbol} at delta of {put_greeks.delta} || Short: {short_put_symbol} Long: {long_put_symbol} ")
    #run_trade_pre_flight(ACCOUNT_ID, API_KEY, short_put_symbol, long_put_symbol, 1, 1.0, "PUT")


    sleep = 15
    for i in range(sleep,0,-1):
        if i % 3 == 0:
            print(f"New data in {i} seconds")
        time.sleep(1)


print("Done for day")

