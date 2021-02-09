#!/usr/bin/python
# -*- coding: utf-8 -*-

#from binance.client import Client  # python-binance
from datetime import datetime
import pandas as pd
import talib
import numpy as np

secondsToUpdate = 120


class Pair:
    def __init__(self, exgCli, pairName, timeFrame):
        self.binance = exgCli
        self.name = pairName
        self.emasAvgs = [(4, 17, 34), (34, 72, 144)]
        self.tFrame = self.binance.KLINE_INTERVAL_4HOUR if timeFrame == '4h' else self.binance.KLINE_INTERVAL_1HOUR
        self.last_update = datetime.now()
        self.candles = pd.DataFrame()
        self.updateCanldes()


    def secondsSinceUpdate(self):
        dif = datetime.now() - self.last_update
        return dif.seconds

    def updateCanldes(self):
        try:
            print("Updating candles for pair", self.name)
            #Download
            self.candles = self.genDataFrame()

            #Convert types to Float
            self.candles['Close'] = self.candles['Close'].astype('float')
            self.candles['Open'] = self.candles['Open'].astype('float')
            self.candles['High'] = self.candles['High'].astype('float')
            self.candles['Low'] = self.candles['Low'].astype('float')
        except Exception as e:
            print("Download:", str(e))
            raise (e)

        try:
            #Calc Indicators
            self.calcEmasAvgs()
        except Exception as e:
            print("Calculating Indicators:", str(e))
            raise (e)

        try:
            #Update DateTime
            self.last_update = datetime.now()
        except Exception as e:
            print("Updating Date:", str(e))
            raise (e)


    #Download klines from pair in Binance
    def klines(self):
        while True:
            try:
                since = "30 days ago UTC"
                klines = self.binance.get_historical_klines(self.name, self.tFrame, since)
                header = [["Timestamp", "Open", "High", "Low", "Close", "Volume", "Close time", "Quote asset volume",
                           "Number of trades", "Taker buy base asset volume", "Taker buy quote asset volume", "Ignore"]]
                return header + klines
            except:
                pass

    def genDataFrame(self):
        candles = self.klines()
        return pd.DataFrame.from_records(candles[1:], columns=candles[0])

    def calcEmasAvgs(self):
        try:
            #self.candles['Close'] = self.candles['Close'].astype('float')
            for fast, med, slow in self.emasAvgs:
                # print("Calculating Emas: " + str(fast) + " " + str(med) + " " + str(slow))
                self.candles["EMA" + str(fast)] = talib.EMA(self.candles['Close'].values, timeperiod=fast).astype('float')
                self.candles["EMA" + str(med)] = talib.EMA(self.candles['Close'].values, timeperiod=med).astype('float')
                self.candles["EMA" + str(slow)] = talib.EMA(self.candles['Close'].values, timeperiod=slow).astype('float')
                self.candles["AVGEMA" + str(med)] = self.candles[["EMA" + str(fast), "EMA" + str(med), "EMA" + str(slow)]].mean(
                    axis=1)
            self.candles = self.candles.fillna(0)
            return self.candles

        except Exception as ex:
            print("CalcEmasAvgs: Error calculating EMAS " + str(ex))
            raise (ex)


    def printCandles(self):
        if self.secondsSinceUpdate() > secondsToUpdate:
            self.updateCanldes()
        print(self.candles)
        print("Updated in", self.last_update, self.secondsSinceUpdate(), " seconds before")

    def getCandles(self):
        if self.secondsSinceUpdate() > secondsToUpdate:
            self.updateCanldes()
        return self.candles

    def getLast(self, name):
        return self.candles[name].values[-1]

    def name(self):
        return self.name

    # def genDataFrame(self, candles):
    #     return pd.DataFrame.from_records(candles[1:], columns=candles[0])


