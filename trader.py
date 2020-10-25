from __future__ import (absolute_import, division, print_function,
                            unicode_literals)

import datetime
from scraper import my_scraper
import warnings
warnings.filterwarnings('ignore')

import backtrader as bt
import backtrader.indicators as btind
import pandas 
import os.path
import time
import sys

class Sentiment(bt.Indicator):
    lines = ('sentiment',)
    plotinfo = dict(
        plotymargin=0.15,
        plothlines=[0],
        plotyticks=[1.0, 0, -1.0])
    
    def next(self):
        self.date = self.data.datetime
        date = bt.num2date(self.date[0]).date()
        prev_sentiment = self.sentiment
        if date in date_sentiment:
            self.sentiment = date_sentiment[date]
        self.lines.sentiment[0] = self.sentiment


class SentimentStrat(bt.Strategy):
    params = (
        ('period', 15),
        ('printlog', True),
    )

    def log(self, txt, dt=None, doprint=False):
        ''' Logging function for this strategy'''
        if self.params.printlog or doprint:
            dt = dt or self.datas[0].datetime.date(0)
            print('%s, %s' % (dt.isoformat(), txt))

    def __init__(self):
        # Keep a reference to the "close" line in the data[0] dataseries
        self.dataclose = self.datas[0].close
        # Keep track of pending orders
        self.order = None
        self.buyprice = None
        self.buycomm = None
        self.sma = bt.indicators.SimpleMovingAverage(
            self.datas[0], period=self.params.period)
        self.date = self.data.datetime
        self.sentiment = None
        Sentiment(self.data)
        
    def notify_order(self, order):
        if order.status in [order.Submitted, order.Accepted]:
            # Buy/Sell order submitted/accepted to/by broker - Nothing to do
            return
        
        # Check if an order has been completed
        # Attention: broker could reject order if not enough cash
        if order.status in [order.Completed]:
            if order.isbuy():
                self.log(
                    'BUY EXECUTED, Price: %.2f, Cost: %.2f, Comm %.2f' %
                    (order.executed.price,
                     order.executed.value,
                     order.executed.comm))
                self.buyprice = order.executed.price
                self.buycomm = order.executed.comm
            else:  # Sell
                self.log('SELL EXECUTED, Price: %.2f, Cost: %.2f, Comm %.2f' %
                         (order.executed.price,
                          order.executed.value,
                          order.executed.comm))
                
            self.bar_executed = len(self)     
            
        elif order.status in [order.Canceled, order.Margin, order.Rejected]:
            self.log('Order Canceled/Margin/Rejected')
            
        # Write down: no pending order
        self.order = None
        
    def notify_trade(self, trade):
        if not trade.isclosed:
            return

        self.log('OPERATION PROFIT, GROSS %.2f, NET %.2f' %
                 (trade.pnl, trade.pnlcomm))
    
    ### Main Strat ###
    def next(self):
        # log closing price of the series from the reference
        self.log('Close, %.2f' % self.dataclose[0])
        
        date = bt.num2date(self.date[0]).date()
        prev_sentiment = self.sentiment
        if date in date_sentiment:
            self.sentiment = date_sentiment[date]
        
        # Check if an order is pending. if yes, we cannot send a 2nd one
        if self.order:
            return
        print(self.sentiment)
        # If not in the market and previous sentiment not none
        if not self.position and prev_sentiment:
            # buy if current close more than sma AND sentiment increased by >= 0.5
            if self.dataclose[0] > self.sma[0] and self.sentiment - prev_sentiment >= 0.5:
                self.log('BUY CREATE, %.2f' % self.dataclose[0])
                self.order = self.buy()
                
        # Already in the market and previous sentiment not none
        elif prev_sentiment:
            # sell if current close less than sma AND sentiment decreased by >= 0.5
            if self.dataclose[0] < self.sma[0] and self.sentiment - prev_sentiment <= -0.5:
                self.log('SELL CREATE, %.2f' % self.dataclose[0])
                self.order = self.sell()

    def stop(self):
        self.log('(MA Period %2d) Ending Value %.2f' %
                 (self.params.period, self.broker.getvalue()), doprint=True)
        

if __name__ == '__main__':
    # Create cerebro
    cerebro = bt.Cerebro()
    date_sentiment, earliest_date = my_scraper()
    # Strategy
    cerebro.addstrategy(SentimentStrat)

    # Data Feed
    filepath = 'data\\spy-midpoint-1-day-bars-for-3-m-before-20200718-12-00-00-est.csv' 
    # Load data from cache into cerebro
    # df = pandas.read_csv(filepath, usecols = ['DateTime', 'Open_Bid', 'High_Bid', 'Low_Bid', 'Close_Bid', 'Open_Ask', 'High_Ask', 'Low_Ask', 'Close_Ask'])
    df = pandas.read_csv(filepath, usecols = ['DateTime', 'Open', 'High', 'Low', 'Close', 'Volume'])
    df.columns = [col_name.lower() for col_name in df.columns]
    df['datetime'] = pandas.to_datetime(df['datetime'])
    df.set_index('datetime')
    print(df.head())
    data = bt.feeds.PandasData(dataname=df, datetime=0, open=1, high=2, low=3, close=4, volume=5)
    print(data)
    # Add second data
    cerebro.adddata(data)              
    # Add minute data 
    cerebro.resampledata(data, timeframe=bt.TimeFrame.Minutes, compression=180)

    cerebro.broker.setcash(100000.0)
    print('Starting Portfolio Value: %.2f' % cerebro.broker.getvalue())
    cerebro.run()
    print('Final Portfolio Value: %.2f' % cerebro.broker.getvalue())


sentiment_plot = pandas.DataFrame(list(date_sentiment.items()), columns=['Date', 'Sentiment'])
sentiment_plot.index = sentiment_plot['Date']
sentiment_plot.plot()
cerebro.plot(style='candlestick')