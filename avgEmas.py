#!/usr/bin/python
# -*- coding: utf-8 -*-

from binance.client import Client  # python-binance
import time
import multiprocessing as mp
import talib
import pandas as pd
import numpy as np
import logging, sys
import datetime
from pair import Pair


class AvgEmas:

    # Construtor
    def __init__(self, key, sec, timeFrame, balEnter, username="no_user"):
        self.binance = Client(key, sec)
        self.tFrame = self.binance.KLINE_INTERVAL_4HOUR if timeFrame == '4h' else self.binance.KLINE_INTERVAL_1HOUR
        # Emas Avgs
        # self.emasAvgs = [(4, 17, 34), (34, 72, 144)]
        # Stoch (Period, Smooth)
        self.pairs = {}

        self.defaultSize = 700
        self.trend = 'N'
        self.balEnter = balEnter
        self.dataFrame = pd.DataFrame()
        self.manager = mp.Manager()
        # self.sendOnTelegram("Running trade bot for " + timeFrame +
        #                         " with balance " + str(self.balEnter))

        #chatId, par, enter Time, enterPrice, close time, close Price, profit %
        self.tradeInfo = [{'ChatId': str(username)}]
        #self.tradeInfo[0]['NumContratos'] = self.numContratos
        self.tradeInfo[0]['TimeFrame'] = timeFrame
        self.stopPerc = 0
        self.profitPerc = 3 if timeFrame == '1h' else 4
        self.minVol = 160.0
        # self.minVol = 5.0
        self.minChgPrice = 2.0

        logging.basicConfig(level=logging.INFO, filename='./log/avgEmas.log',
                            filemode='w')


    def mediumVolume(array, periods):
        periods = periods * -1
        return np.mean(array[periods:])


    # Get all the active pairs with volume greater than minVol and a good price change
    def listPairs(self):
        logging.debug("Buscando pares com volume bom")
        tickers = pd.DataFrame(self.binance.get_ticker())
        tickers[['volume', 'priceChangePercent']] = tickers[['volume', 'priceChangePercent']].astype(float)
        return tickers[(tickers['symbol'].str.endswith("BTC")) & (tickers['volume'] > self.minVol) & (
                tickers['priceChangePercent'] > self.minChgPrice)]

    def stopTimeFrame(self):
        return self.tFrame
        # if self.tFrame == '1min' or self.tFrame == '5min':
        #     return '1min'
        # elif self.tFrame == '15min':
        #     return '5min'
        # elif self.tFrame == '1hour':
        #     return '15min'
        # elif self.tFrame == '4hour':
        #     return '1hour'


    def trailingStop(self, startPrice=0, newTrend='B'):
        profitPrice = self.calcProfit(startPrice)
        if startPrice == 0:
            startPrice = self.okex.lastPrice()
        if newTrend != 'B':
            self.trend = newTrend
        if self.trend == 'S':
            # return trailingStopShort(startPrice, initialStop, profitPrice)
            return self.trailingStopShort(startPrice, profitPrice)
        elif self.trend == 'L':
            # return trailingStopLong(startPrice, initialStop, profitPrice)
            return self.trailingStopLong(startPrice, profitPrice)
        else:
            return -2


    def trailingStopShort(self, startPrice, profit=0):
        self.sendOnTelegram("Starting Trailling Stop:\nPrice: " + str(startPrice))
        stopPrice = self.calcStop(self.candleInPosition(-1)['High'])
        self.sendOnTelegram("Price: " + str(startPrice) + "\nStop: " + str(stopPrice) + "\nProfit: " + str(profit))
        while True:
            try:
                lastCandle = self.okex.lastCandle()
                currPrice = float(lastCandle['Close'])
                currLow = float(lastCandle['Low'])
                newstopPrice = self.calcStop(currLow)
                idxTop, lastTop = self.getLastTop(tFrame=self.stopTFrame)
                lastTop = lastTop if lastTop > currPrice else newstopPrice
                newstopPrice = newstopPrice if newstopPrice < lastTop else lastTop
                if float(newstopPrice) < float(stopPrice):
                    stopPrice = newstopPrice
                    self.sendOnTelegram("Stop updated to: " + str(stopPrice))
                if float(currPrice) <= float(profit) and float(profit) != 0:
                    self.sendOnTelegram("Get Profit at " + str(currPrice))
                    return self.forceClose()
                elif float(currPrice) >= float(stopPrice):
                    self.sendOnTelegram("Get Stop at " + str(currPrice))
                    return self.forceClose()
                time.sleep(15)
            except Exception as ex:
                self.sendOnTelegram("trailingStopShort: Error on trailing Stop " + str(ex))
                time.sleep(20)
                pass

    def trailingStopLong(self, startPrice, profit=0):
        self.sendOnTelegram("Starting Trailling Stop:\nPrice: " + str(startPrice))
        stopPrice = self.calcStop(self.candleInPosition(-1)['Low'])
        self.sendOnTelegram("Price: " + str(startPrice) + "\nStop: " + str(stopPrice) + "\nProfit: " + str(profit))
        while True:
            try:
                lastCandle = self.okex.lastCandle()
                currPrice = float(lastCandle['Close'])
                currHigh = float(lastCandle['High'])
                newstopPrice = self.calcStop(currHigh)
                idxBottom, lastBottom = self.getLastBottom(tFrame=self.stopTFrame)
                lastBottom = lastBottom if lastBottom < currPrice else newstopPrice
                newstopPrice = newstopPrice if newstopPrice > lastBottom else lastBottom
                if float(newstopPrice) > float(stopPrice):
                    stopPrice = newstopPrice
                    self.sendOnTelegram("Stop updated to: " + str(stopPrice))
                if float(currPrice) >= float(profit) and float(profit) != 0:
                    self.sendOnTelegram("Get Profit at " + str(currPrice))
                    return self.forceClose()
                elif float(currPrice) <= float(stopPrice):
                    self.sendOnTelegram("Get Stop at " + str(currPrice))
                    return self.forceClose()
                time.sleep(15)
            except Exception as ex:
                self.sendOnTelegram("trailingStopLong: Error on trailing Stop " + str(ex))
                time.sleep(20)
                pass

    # def trailingStopShort(self, startPrice):
    #     self.sendOnTelegram("Starting Trailling Stop:\nPrice: " + str(startPrice))
    #     cross = self.waitCrossover(crossToEnter=False)
    #     self.sendOnTelegram("Closing Position")
    #     return self.forceClose()
    #
    # def trailingStopLong(self, startPrice):
    #     self.sendOnTelegram("Starting Trailling Stop:\nPrice: " + str(startPrice))
    #     cross = self.waitCrossunder(crossToEnter=False)
    #     self.sendOnTelegram("Closing Position")
    #     return self.forceClose()

    def forceClose(self):
        while True:
            try:
                lastCandle = self.okex.lastCandle()
                currPrice = float(lastCandle['Close'])
                currPrice = currPrice * 0.999 if self.trend == 'L' else currPrice * 1.001
                self.sendOnTelegram("Closing position at price(will be closed at market price): " + str(currPrice))
                #self.okex.closePosition(self.trend, currPrice, self.numContratos, 1)
                return float(lastCandle['Close'])
            except Exception as ex:
                self.sendOnTelegram("Error closing postion: " + str(ex))
                # if self.numContratos == 1:
                #     self.sendOnTelegram("I can't close your position: " + str(ex))
                #     raise(ex)
                # self.sendOnTelegram("I will try to subtract 1 contract")
                # self.numContratos = int(self.numContratos) - 1
                if self.numContratos <= 0:
                    self.sendOnTelegram("Position not closed")
                    return float(lastCandle['Close'])
                pass

    def candleVerde(self, candle):
        if candle['Open'] < candle['Close']:
            return True
        else:
            return False


    def priceUp(self, pair):
        candles = self.pairs[pair].getCandles()
        if (candles["AVGEMA17"].values[-1] < candles['Close'].values[-1] and candles["AVGEMA17"].values[-2] > candles['Close'].values[-2]):
            return True
        else:
            return False

    # def openPosition(self, openPrice):
    #     try:
    #         # orderId = self.okex.openOrder(self.trend, 0, numContratos=self.numContratos)
    #         if (self.okex.aguardaExecucao(orderId) <=0):
    #             self.sendOnTelegram("Order not executed")
    #             self.okex.cancelaOrdem(orderId)
    #             return (-1,-1)
    #         avgPrice = self.okex.getPosPrice(self.trend)
    #
    #         return (orderId, avgPrice)
    #
    #     except Exception as ex:
    #         print("Open Position: "+ str(ex))
    #         raise(ex)

    def turnOff(self, exitStatus=0):
        # self.sendOnTelegram("Avg Ema Bot Desligado!\nStatus Code:" + str(exitStatus))
        sys.exit(exitStatus)

    def genCsv(self, csvPath="./log.csv"):
        try:
            logs = pd.read_csv(csvPath)
            logs = logs.append(self.tradeInfo, ignore_index=True)
        except:
            logs = pd.DataFrame(self.tradeInfo)
        logs.to_csv(csvPath, index=False)

    def calcStop(self, price):
        if self.trend == 'L':
            return price * ((100 - float(self.stopPerc))/100)
        else:
            return price * ((100 + float(self.stopPerc))/100)
        return 0

    def calcProfit(self, price):
        if self.profitPerc == 0:
            return 0
        if self.trend == 'L':
            return price * ((100 + float(self.profitPerc))/100)
        else:
            return price * ((100 - float(self.profitPerc))/100)
        return 0

    def getLastBottom(self, pair):
        try:
            candles = self.pairs[pair].getCandles()[-2::-1]
            for idx, candle in enumerate(candles[1:]):
                if idx + 2 >= len(candles):
                    break
                nextValue = candles['EMA4'].values[idx + 2]
                mainIdx = candles['EMA4'].values[idx + 1]
                prevValue = candles['EMA4'].values[idx]
                if (nextValue > mainIdx and prevValue > mainIdx):
                    return ((idx+1), candles['Low'].values[idx +1])
            return (-1,0)

        except Exception as ex:
            print("getLastBottom: Error getting bottom " + str(ex))
            raise(ex)

    def getLastTop(self, pair):
        try:
            candles = self.pairs[pair].getCandles()[-2::-1]
            for idx, candle in enumerate(candles[1:]):
                if idx + 2 >= len(candles):
                    break
                nextValue = candles['EMA4'].values[idx + 2]
                mainIdx = candles['EMA4'].values[idx + 1]
                prevValue = candles['EMA4'].values[idx]
                if (nextValue < mainIdx and prevValue < mainIdx):
                    return ((idx + 1), candles['High'].values[idx + 1])
            return (-1, 0)

        except Exception as ex:
            print("getLastBottom: Error getting bottom " + str(ex))
            raise (ex)

    # def getBalance():
    #     exit()

    def longPosition(self, pairName):
        try:
            candles = self.pairs[pairName].getCandles()
            #se as médias estão cruzadas
            if candles['Low'].values[-3] < candles["AVGEMA17"].values[-3] and candles["AVGEMA17"].values[-1] > candles["AVGEMA72"].values[-1] and candles["AVGEMA17"].values[-2] > candles["AVGEMA72"].values[-2] and candles['Close'].values[-1] > candles["AVGEMA17"].values[-1] and candles['Close'].values[-2] > candles["AVGEMA17"].values[-2] and self.candleVerde(candles.iloc[-1]) and self.candleVerde((candles.iloc[-2])):
                return True
            else:
                return False



        except Exception as ex:
            print("Crossover: " + str(ex))
            raise(ex)

    def getLong(self, pair):
        inLong = self.longPosition(pair)
        if inLong:
            #Get two open sequence
            return pair
        return None

    def getAllLongs(self):
        try:
            longs = []
            for pair in self.pairs.items():
                #Get name of pair in long or None if not
                pair = self.getLong(pair[0])
                if pair != None:
                    longs.append(pair)
            # print(longs)
            return longs
        except Exception as e:
            print(str(e))
            pass

    def findEnters(self, namesList):

        if len(self.pairs) == 0:
            self.createPairs(namesList)
        else:
            self.updatePairs(namesList)

        print("Getting Long Positions")
        longs = self.getAllLongs()
        return longs


    def updatePairs(self, namesList):
        try:
            pool = mp.Pool(processes=20)
            trades = []
            for symbol in namesList:
                print("Updating pair", symbol)
                # pairs.append(Pair(self.binance, symbol, self.tFrame))
                trades.append(pool.apply_async(self.pairs[symbol].getCandles, args=[], ))
            pool.close()
            pool.join()
            for trade in trades:
                trade.get()
            # print(self.pairs)
        except:
            return

    def createPairs(self, namesList):
        try:
            pool = mp.Pool(processes=20)
            trades = []
            for symbol in namesList:
                print("Creating pair", symbol)
                # pairs.append(Pair(self.binance, symbol, self.tFrame))
                trades.append(pool.apply_async(Pair, args=[self.binance, symbol, self.tFrame], ))
            pool.close()
            pool.join()
            for trade in trades:
                pair = trade.get()
                self.pairs[pair.name] = pair
            # print(self.pairs)
        except:
            self.pairs = {}
            return


    def run(self):
            try:
                # while True:
                    print("Listing pairs")
                    pairsList = self.listPairs()
                    print("Getting pairs in Long Position")
                    # print(pairsList['symbol'].values)
                    enters = self.findEnters(pairsList['symbol'].values)
                    res = {}
                    for pair in enters:
                        name = self.pairs[pair].name
                        enterPrice = self.pairs[pair].getLast('Close')
                        stopPrice = self.getLastBottom(pair)[1]
                        profitPrice = float(enterPrice) * 1.04
                        values = {
                            "enterPrice": float("{0:.8f}".format(enterPrice)),
                            "stopPrice": float("{0:.8f}".format(stopPrice)),
                            "profitPrice": float("{0:.8f}".format(profitPrice))
                        }
                        res[name] = values

                    return res

            except Exception as e:
                print(str(e))
                return dict()


    # if __name__ == "__main__":
    #     app.run(debug=True)
