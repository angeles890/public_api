import requests as r
import os
import logging
from dotenv import load_dotenv, dotenv_values
import json
from dataclasses import dataclass
import time
from typing import List, Optional
import re

# LOAD ENV Variables
load_dotenv()
API_KEY = os.environ.get("API_KEY")
ACCOUNT_ID = os.environ.get("ACCOUNT_ID")
EXPECTED_MOVE = 5


@dataclass
class Greeks:
    symbol: str
    delta: float
    gamma: float
    theta: float
    vega: float
    rho: float
    impliedVolatility: float

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
            impliedVolatility=float(g["impliedVolatility"])
        )

@dataclass
class Instrument:
    symbol: str
    type: str

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

    params = {
        "osiSymbols": symbol
    }

    response = r.get(url, headers = headers, params = params)
    data = response.json()
    print(data)
    result = Greeks.from_dict(data)
    return result


def get_short_strike(option_chain: OptionChain, option_type: str, starting_index: int, expected_move: int):
    keep_searching = True
    


    scaling_factor = 1
    option_chains = option_chain.calls
    if option_type == "put":
        scaling_factor = -1
        option_chains = option_chain.puts

    i = starting_index + (scaling_factor * expected_move)
    max_search = 5
    while keep_searching:
        option_strike = option_chains[i]
        greeks = get_greeks(option_strike.instrument.symbol, ACCOUNT_ID, API_KEY)
        if abs(greeks.delta) > .10 and max_search >= 0:
            print(abs(greeks.delta))
            keep_searching = True
            i += (1*scaling_factor)
            max_search -= 1
        else:
            keep_searching = False

    return greeks







qqq = Instrument('QQQ','EQUITY')
for i in range(1):
    qqq_quote = get_quote(qqq, ACCOUNT_ID, API_KEY)
    print(f"{qqq_quote.instrument.symbol}: last price {qqq_quote.last}")
    qqq_option_chain = get_option_chain(qqq, ACCOUNT_ID, API_KEY,"2025-12-23")
    
    call_index = 62 #qqq_option_chain.call_strikes_count // 2
    put_index = 61 #qqq_option_chain.put_strikes_count // 2

    # check call strike is just above current price (ie less than $1.00)
    get_atm_call = True
    while get_atm_call:
        if 0.01 <= float(parse_option_symbol(qqq_option_chain.calls[call_index].instrument.symbol)['strike']) - qqq_quote.last <= 0.99:
            get_atm_call = False
        elif float(parse_option_symbol(qqq_option_chain.calls[call_index].instrument.symbol)['strike']) - qqq_quote.last > 0.99:
            call_index -=1
        else:
            call_index += 1

    get_atm_put = True
    while get_atm_put:
        if 0.01 <= qqq_quote.last - float(parse_option_symbol(qqq_option_chain.puts[put_index].instrument.symbol)['strike']) <= 0.99:
            get_atm_put = False
        elif qqq_quote.last - float(parse_option_symbol(qqq_option_chain.puts[put_index].instrument.symbol)['strike']) > 0.99:
            put_index +=1
        else:
            put_index -= 1

    # sanity check
    # ATM strikes should be no more than $1 away from each other, and current price should be between them
    if not (0 <= parse_option_symbol(qqq_option_chain.calls[call_index].instrument.symbol)['strike'] - parse_option_symbol(qqq_option_chain.puts[put_index].instrument.symbol)['strike'] <= 1.0):
        print("ERROR: Call and Puts too far aways")


    call_greeks = get_short_strike(qqq_option_chain, "call", call_index, 3)
    put_greeks = get_short_strike(qqq_option_chain, "put", put_index, 3)
    print(f"Call strike: {call_greeks}")
    print(f"PUT strike: {put_greeks}")
    time.sleep(5)


