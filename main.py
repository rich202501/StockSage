import json
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import yfinance as yf
import streamlit as st
import os
from openai import OpenAI

client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))

def getStockPrice(ticker):
    return str(yf.Ticker(ticker).history(period='1y').iloc[-1].Close)

def calculateSMA(ticker, window):
    data = yf.Ticker(ticker).history(period='1y').Close
    return str(data.rolling(window=window).mean().iloc[-1])

def calculateEMA(ticker, window):
    data = yf.Ticker(ticker).history(period='1y').Close
    return str(data.ewm(span=window, adjust=False).mean().iloc[-1])

def calculateRSI(ticker):
    data = yf.Ticker(ticker).history(period='1y').Close
    delta = data.diff()
    up = delta.clip(lower=0)
    down = -1 * delta.clip(upper=0)
    ema_up = up.ewm(com=14-1, adjust=False).mean()
    ema_down = down.ewm(com=14-1, adjust=False).mean()
    rs = ema_up / ema_down
    return str(100 - (100 / (1 + rs)).iloc[-1])

def calculateMACD(ticker):
    data = yf.Ticker(ticker).history(period='1y').Close
    short_EMA = data.ewm(span=12, adjust=False).mean()
    long_EMA = data.ewm(span=26, adjust=False).mean()
    MACD = short_EMA - long_EMA
    signal = MACD.ewm(span=9, adjust=False).mean()
    MACD_histogram = MACD - signal
    return f'{MACD.iloc[-1]}, {signal.iloc[-1]}, {MACD_histogram.iloc[-1]}'

def plotStockPrice(ticker):
    data = yf.Ticker(ticker).history(period='1y')
    plt.figure(figsize=(10, 5))
    plt.plot(data.index, data.Close)
    plt.title(f'{ticker} Stock Price Over Last Year')
    plt.xlabel('Date')
    plt.ylabel('Stock Price ($)')
    plt.grid(True)
    plt.savefig('stock.png')
    plt.close()

functions = [
    {
        'name': 'getStockPrice',
        'description': 'Gets the latest stock price given the ticker symbol of a company.',
        'parameters': {
            'type': 'object',
            'properties': {
                'ticker': {
                    'type': 'string',
                    'description': 'The stock ticker symbol for a company (for example AAPL for Apple).'
                }
            },
            'required': ['ticker']
        }
    },
    {
        'name': 'calculateSMA',
        'description': 'Calculate the simple moving average for a given stock ticker and a window.',
        'parameters': {
            'type': 'object',
            'properties': {
                'ticker': {'type': 'string'},
                'window': {'type': 'integer'}
            },
            'required': ['ticker', 'window']
        }
    },
    {
        'name': 'calculateEMA',
        'description': 'Calculate the exponential moving average for a given stock ticker and a window.',
        'parameters': {
            'type': 'object',
            'properties': {
                'ticker': {'type': 'string'},
                'window': {'type': 'integer'}
            },
            'required': ['ticker', 'window']
        }
    },
    {
        'name': 'calculateRSI',
        'description': 'Calculate the RSI for a given stock ticker.',
        'parameters': {
            'type': 'object',
            'properties': {
                'ticker': {'type': 'string'}
            },
            'required': ['ticker']
        }
    },
    {
        'name': 'calculateMACD',
        'description': 'Calculate the MACD for a given stock ticker.',
        'parameters': {
            'type': 'object',
            'properties': {
                'ticker': {'type': 'string'}
            },
            'required': ['ticker']
        }
    },
    {
        'name': 'plotStockPrice',
        'description': 'Plot the stock price for the last year given the ticker symbol of a company',
        'parameters': {
            'type': 'object',
            'properties': {
                'ticker': {'type': 'string'}
            },
            'required': ['ticker']
        }
    }
]

availableFunctions = {
    'getStockPrice': getStockPrice,
    'calculateSMA': calculateSMA,
    'calculateEMA': calculateEMA,
    'calculateRSI': calculateRSI,
    'calculateMACD': calculateMACD,
    'plotStockPrice': plotStockPrice
}

if 'messages' not in st.session_state:
    st.session_state['messages'] = []

st.title('StockSage: Stock Analysis Assistant')

user_input = st.text_input('Your input:')

if user_input:
    try:
        st.session_state['messages'].append({'role': 'user', 'content': user_input})

        response = client.chat.completions.create(
            model='gpt-3.5-turbo-0613',
            messages=st.session_state['messages'],
            functions=functions,
            function_call='auto'
        )

        response_message = response.choices[0].message

        if response_message.function_call:
            function_name = response_message.function_call.name
            function_args = json.loads(response_message.function_call.arguments)
            if function_name in ['getStockPrice', 'calculateRSI', 'calculateMACD', 'plotStockPrice']:
                args_dict = {'ticker': function_args.get('ticker')}
            elif function_name in ['calculateSMA', 'calculateEMA']:
                args_dict = {
                    'ticker': function_args.get('ticker'),
                    'window': function_args.get('window')
                }

            function_to_call = availableFunctions[function_name]
            function_response = function_to_call(**args_dict)

            st.session_state['messages'].append(response_message)
            st.session_state['messages'].append({
                'role': 'function',
                'name': function_name,
                'content': function_response
            })

            if function_name == 'plotStockPrice':
                st.image('stock.png')
            else:
                second_response = client.chat.completions.create(
                    model='gpt-3.5-turbo-0613',
                    messages=st.session_state['messages']
                )
                st.text(second_response.choices[0].message.content)
                st.session_state['messages'].append({
                    'role': 'assistant',
                    'content': second_response.choices[0].message.content
                })
        else:
            st.text(response_message.content)
            st.session_state['messages'].append({
                'role': 'assistant',
                'content': response_message.content
            })

    except Exception as e:
        st.error(f"An error occurred: {e}")
