#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from binance.client import Client  # python-binance
import pandas as pd  # pandas
#from telegram.ext import Updater, CommandHandler # pip install python-telegram-bot
import random
import talib  as talib # ta-lib
import multiprocessing as mp
import logging, sys
import time
import asyncio
import numpy as np
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters # pip install python-telegram-bot\
import telegram
from avgEmas import AvgEmas
from peregrinearb import create_weighted_multi_exchange_digraph, bellman_ford_multi, print_profit_opportunity_for_path_multi
import math
import networkx as nx
import asyncio
from peregrinearb import load_exchange_graph, print_profit_opportunity_for_path, bellman_ford
import math
import networkx as nx


# Enable logging
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                    level=logging.INFO)

logger = logging.getLogger(__name__)


# Exchange Info
api_key = "123"
api_secret = "123"
client = Client(api_key, api_secret)
minVol = 160.0
minChgPrice = 1.0  # Percent of change price, min it accepts
linePerMsg = 5
percProfit = 1.0  #0.4
emas = [8, 62]
minDistEma = 1
enterDiff = 2
minLastCandleVol = 1  
percPriceEnter = 2
disLowEma = 1
stopPerc = 5
minBtcVolume = 500
diffMACDPerc = 0.5
avgVolumePeriods = 17

shortCoinsList = ['USDCBTC', 'PAXBTC', 'TUSDBTC', 'NBTBTC']

# TelegramBot Info
botApiToken = ""

def start(update, context):
    update.message.reply_text("Ola, atualmente eu analiso apenas na Binance.")

def send_pairs(update, context):
    msgSplt = update.message.text.split(" ")
    global minChgPrice
    oldMin = minChgPrice
    if len(msgSplt) == 2:
        minChgPrice = float(msgSplt[1])
    pairs = listChangeVol()
    minChgPrice = oldMin
    pairs = pairs.sort_values(by=['priceChangePercent', 'volume'])

    replyStr = "Essas sao as moedas que eu acredito que vale a pena voce analisar agora:"
    update.message.reply_text(replyStr)
    lines = 0
    replyStr = ""
    for idx, pair in pairs.iterrows():
        replyStr = replyStr + pair.symbol + " - Volume: " + str(pair.volume) + " - Price Change %(24h): " + str(
            pair.priceChangePercent) + "\n"
        lines += 1
        if lines == linePerMsg:
            update.message.reply_text(replyStr)
            lines = 0
            replyStr = ""
    if len(replyStr) > 0:
        update.message.reply_text(replyStr)
    replyStr = "\nAbra sua conta na binance: https://www.binance.com/?ref=16836135"
    update.message.reply_text(replyStr)
    return None

def error(update, context):
    """Log Errors caused by Updates."""
    logger.warning('Update "%s" caused error "%s"', update, context.error)


def sendSignal(update, context):
    try:
        print("Recebi o comando sinais")	
        sigs = findSignal()
        strSend = "Seguem umas boas entradas na Binance:"
        update.message.reply_text(strSend)
        print("Resposta enviada")
        strSend = ""
        lines = 0
        if len(sigs) == 0:
            strSend = "Não encontrei nenhuma boa entrada agora\nAbra sua conta na binance: https://www.binance.com/?ref=16836135"
            update.message.reply_text(strSend)
            return 0
        for sig in sigs:
            strSend = strSend + "\n" + "Entre no par: {0}\nPreço Atual:{4:.8f}\nEntrada: {1:.8f}\nProfit: {2:.8f}\nStop: {3:.8f}".format(sig[0], sig[1], sig[2], sig[3], sig[4])
            lines += 1
            if lines == linePerMsg:
                update.message.reply_text(strSend)
                sleep(3)
                lines = 0
                strSend = ""
        if len(strSend) > 0:
            update.message.reply_text(strSend)
        strSend = "\nAbra sua conta na binance: https://www.binance.com/?ref=16836135"
        update.message.reply_text(strSend)
        return 0   
    except Exception as e:
        print(str(e))
        return 0

def sigAvgEmas(update, context):
    try:
        context.bot.sendChatAction(update.message.chat.id, telegram.ChatAction.TYPING)
        avgEmas = AvgEmas(api_key, api_secret, '1h', 0.01)
        context.bot.sendChatAction(update.message.chat.id, telegram.ChatAction.TYPING)
        signals = avgEmas.run()
        strSend = ""
        lines = 0
        if len(signals) == 0:
            strSend = "Não encontrei nenhuma boa entrada agora\nAbra sua conta na binance: https://www.binance.com/?ref=16836135"
            #update.message.reply_text(strSend)
            context.bot.send_message(chat_id=update.message.chat_id, text=strSend)
            return 0
        for pair, prices in signals.items():
            strSend = strSend + "\n" + "Entre no par: {0}\nPreço Atual:{1:.8f}\nEntrada: {2:.8f}\nProfit: {3:.8f}\nStop: {4:.8f}\n".format(
                pair, prices["enterPrice"], prices["enterPrice"], prices["profitPrice"], prices["stopPrice"])
            lines += 1
            if lines == linePerMsg:
                context.bot.send_message(chat_id=update.message.chat_id, text=strSend)
                lines = 0
                strSend = ""
        if len(strSend) > 0:
            context.bot.send_message(chat_id=update.message.chat_id, text=strSend)
        strSend = "\nAbra sua conta na binance: https://www.binance.com/?ref=16836135"
        update.message.reply_text(strSend)
        return 0
    except Exception as e:
        print(str(e))
        return 0


def shortCoins(pairs):
    try:
        return pairs[pairs['symbol'].isin(shortCoinsList)]
    except Exception as ex:
        print("Short Coins Filter:", str(ex))
        raise(ex)


def findSignal():
    try:
        trend = btcVolumeBlock()
        if trend == 'B':
            print("Bitcoin Filter Stopped signals")
            return []
        pairs = listChangeVol()
        if trend == 'S':
            print("Bitcoin is in short Trend")
            pairs = shortCoins(pairs)

        pool = mp.Pool(processes=6)
        trades = []
        for symbol in pairs.symbol:
            trades.append(pool.apply_async(emasSig, args=[symbol], ))
        pool.close()
        pool.join()
        sigsToSend = []
        for trade in trades:
            sig = trade.get()
            if (float(sig[1]) > 0):
                sigsToSend.append(sig)
        return sigsToSend

    except KeyboardInterrupt:
        print("Exiting...")
        exit()
    except Exception as ex:
        print("Error finding signal")
        print(str(ex))
        exit()


#@bot.message_handler(regexp="[Ss]uper.[EeÉé]rick")
def super_erick(update, context):
    replies = ["Claro, posso ajudar?", "Opa, Super Erick??? Esse sou eu!!! Me chamou?", "Quem eu?",
               "Eu sou o Super Erick", "Você me chamou?", "Oi ", "E ai, eu sou o Super Erick, me peça uns sinais!", 
               "Super Erick sou eu, é uma longa história...", "Eu costumava ser um aventureiro como você, aí tomei uma flechada no joelho..."
               ]
    repLen = int(len(replies))
    rndAnsw = random.randint(0, repLen-1)
    update.message.reply_text(replies[rndAnsw])
    return
    

async def getCandles(pair, interval, since):
    while True:
        try:
            klines = client.get_historical_klines(pair, interval, since)
            header = [["Timestamp", "Open", "High", "Low", "Close", "Volume", "Close time", "Quote asset volume", "Number of trades", "Taker buy base asset volume", "Taker buy quote asset volume", "Ignore"]]
            return header + klines
        except:
            pass

def genDataFrame(candles):
    return pd.DataFrame.from_records(candles[1:], columns=candles[0])

# Find enter, profit and stop prices based on two emas
# Returns a tupple: SymbolName, enterPrice, profitPrice, stopPrice
def emasSig(symbol):
    logging.debug("Verificando entradas para o par: " + symbol)
    # Download Klines
    while True:
        try:
            since = "2 days ago UTC"
            asyncio.set_event_loop(asyncio.new_event_loop())
            loop = asyncio.get_event_loop()
            candles = loop.run_until_complete(getCandles(symbol, client.KLINE_INTERVAL_15MINUTE, since))
            klines15 = genDataFrame(candles)
            klines15['Close'] = klines15['Close'].astype('float')
            klines15['Quote asset volume'] = klines15['Quote asset volume'].astype('float')
            if (len(klines15['Close'].values) > 0): #and float(klines15['Quote asset volume'].values[-1]) > minLastCandleVol):
                klines15['MACD'], klines15['Signal'], klines15['Hist'] = talib.MACD(klines15['Close'].values, fastperiod=17, slowperiod=72, signalperiod=34)
                print(symbol, ":\nMACD:", "%.8f" % klines15['MACD'].values[-1], "\nSignal:", "%.8f" % klines15['Signal'].values[-1])
                if float(klines15['MACD'].values[-1]) < (float(klines15['Signal'].values[-1]) * (1 + (float(diffMACDPerc)/100))):
                    return (symbol, -1.0, -1.0,-1.0, -1.0)
            nameEmas = []
            for ema in emas:
                logging.debug("EMA " + str(ema) + " for " + symbol)
                nameEmas.append("EMA" + str(int(ema)))
                if (len(klines15['Close'].values) <= 0 or float(klines15['Quote asset volume'].values[-1]) < minLastCandleVol):
                    return (symbol, -1.0, -1.0, -1.0, -1.0)

                klines15["EMA" + str(int(ema))] = talib.EMA(klines15['Close'].values, timeperiod=ema).astype('float')
                klines15["EMA" + str(int(ema))] = klines15["EMA" + str(int(ema))].fillna(value=0.0)

            lowEma = klines15[-1:][nameEmas[0]].values
            highEma = klines15[-1:][nameEmas[1]].values

            #Verificar se a lowEma > highEma e calcular entrada, stop e saída.
            if lowEma >= (highEma * (1+(minDistEma/100)))and lowEma <= klines15['Close'].values[-1]:
                close=float(klines15['Close'].values[-1])
                enter = enterPrice(close=close, ema=lowEma)
                stop = stopPrice(enter, close, lowEma, highEma)
                profit = profitPrice(enter)

                return (symbol, float(enter), float(profit), float(stop), float(klines15['Close'].values[-1]))
            else:
                return (symbol, -1.0, -1.0,-1.0, -1.0)

        except KeyboardInterrupt:
            raise
        except Exception as ex:
            print("Erro ao calcular sinal: ", symbol)
            print(str(ex))
            return (symbol, -1.0, -1.0,-1.0, -1.0)

def enterPrice(close=0, ema=0):
    if close >= ema * (1+(percPriceEnter/100)):
        return close
    else:
        return ema

def profitPrice(enter=0):
    return enter * (1 + (percProfit/100))

def stopPrice(enter=0, close=0, lowEma=0, highEma=0):
    percPrice = enter * (1 - (stopPerc/100))
    if percPrice > highEma:
        return percPrice
    elif float(close) == float(enter):
        if percPrice > (lowEma * (1 - (disLowEma/100))):
            return percPrice
        else:
            return lowEma * (1 - (disLowEma/100))
    else:
        return highEma

def MacdFilter(histArray):
    return histArray[-1] < 0 or histArray[-2] < 0 or histArray[-3] > 0

def mediumVolume(array, periods):
    periods = periods * -1
    return np.mean(array[periods:])

def MACDTrend(klines):
    klines['Close'] = klines['Close'].astype('float')
    klines['MACD'], klines['Signal'], klines['Hist'] = talib.MACD(klines['Close'].values, fastperiod=17.0,
                                                                        slowperiod=72.0, signalperiod=34.0)

    print("BTCUSD", ":\nMACD:", "%.8f" % klines['MACD'].values[-1], "\nSignal:",
          "%.8f" % klines['Signal'].values[-1])

    if float(klines['MACD'].values[-1]) <= float(klines['Signal'].values[-1]):
        return 'S'
    else:
        return 'L'

def btcVolumeBlock():
    return 'L'
    asyncio.set_event_loop(asyncio.new_event_loop())

    since = "2 days ago UTC"
    loop = asyncio.get_event_loop()
    candles = loop.run_until_complete(getCandles("BTCUSDT", client.KLINE_INTERVAL_15MINUTE, since))
    klines15 = genDataFrame(candles)
    klines15['Close'] = klines15['Close'].astype('float')
    klines15['High'] = klines15['High'].astype('float')
    klines15['Quote asset volume'] = klines15['Quote asset volume'].astype('float')
    avgVolume = mediumVolume(klines15['Quote asset volume'].values, avgVolumePeriods)

    high = klines15['High'].values[-2]
    lastClose = klines15['Close'].values[-1]
    print("Filter: High Price =", high, "Close Price", lastClose, "\nAvg Volume:", avgVolume, "\nLast Volume:",klines15['Quote asset volume'].values [-1])
    if klines15['Quote asset volume'].values[-1] < float(avgVolume) / 4:
        return 'B'
    else:
        return MACDTrend(klines15)
    return 'S'

def downloadKlines(symbol, interval, since):
    numErrors = 1
    while True:
        try:
            return client.get_historical_klines(symbol, interval, since)
        except KeyboardInterrupt:
            print("Exiting...")
            exit()
        except Exception as ex:
            print(str(ex))
            slp = random.randint(1, 10)
            time.sleep(slp * numErrors)
            numErrors = numErrors + 1
            pass


# Get all the active pairs with volume greater than minVol and a good price change
def listChangeVol():
    logging.debug("Buscando pares com volume bom")
    tickers = pd.DataFrame(client.get_ticker())
    tickers[['volume', 'priceChangePercent']] = tickers[['volume', 'priceChangePercent']].astype(float)
    return tickers[(tickers['symbol'].str.endswith("BTC")) & (tickers['volume'] > minVol) & (
            tickers['priceChangePercent'] > minChgPrice)]


def arbitragem(update, context):
    try:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        graph = create_weighted_multi_exchange_digraph(['kraken', 'bittrex', 'binance', 'coinbase', 'poloniex'], fees=True, log=True)
        graph, paths = bellman_ford_multi(graph, 'BTC')
        i = 0
        lines = ""
        for path in paths:
            lines = lines + str(print_profit_opportunity_for_path_multi(graph,path))
            if i % 3 == 0:
                try:
                    context.bot.send_message(chat_id=update.message.chat_id, text=lines)
                except:
                    time.sleep(5)
                    context.bot.send_message(chat_id=update.message.chat_id, text=lines)
                    pass
                lines = ""
            
            if i > 30:
                break
            i +=1
    
        replyStr = "\nAbra sua conta na binance: https://www.binance.com/?ref=16836135"
        update.message.reply_text(replyStr)
    except Exception as e:
        print(str(e))
        pass

def get_opportunity_for_path(graph, path, round_to=None, depth=False, starting_amount=100):
    if not path:
        return

    print("Começando com {} em {}".format(starting_amount, path[0]))

    for i in range(len(path)):
        if i + 1 < len(path):
            start = path[i]
            end = path[i + 1]

            if depth:
                volume = min(starting_amount, math.exp(-graph[start][end]['depth']))
                starting_amount = math.exp(-graph[start][end]['weight']) * volume
            else:
                starting_amount *= math.exp(-graph[start][end]['weight'])

            if round_to is None:
                rate = math.exp(-graph[start][end]['weight'])
                resulting_amount = starting_amount
            else:
                rate = round(math.exp(-graph[start][end]['weight']), round_to)
                resulting_amount = round(starting_amount, round_to)

            printed_line = "{} para {} a {} = {} (total)".format(start, end, rate, resulting_amount)

            # todo: add a round_to option for depth
            if depth:
                printed_line += " com {} de {} negociado".format(volume, start)

            return printed_line

def triangular(update, context):
    try:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        graph = asyncio.get_event_loop().run_until_complete(load_exchange_graph('binance', fees=True))

        paths = bellman_ford(graph, 'BTC')
        i = 0
        for path in paths:
            lines = get_opportunity_for_path(graph, path)
            if i % 3 == 0:
                try:
                    context.bot.send_message(chat_id=update.message.chat_id, text=lines)
                except:
                    time.sleep(5)
                    context.bot.send_message(chat_id=update.message.chat_id, text=lines)
                    pass
                lines = ""

            if i > 30:
                break
            i += 1

        replyStr = "\nAbra sua conta na binance: https://www.binance.com/?ref=16836135"
        update.message.reply_text(replyStr)
    except Exception as e:
        print(str(e))
        pass

def main():
    logging.basicConfig(stream=sys.stderr, level=logging.WARNING)
    # prices = client.get_all_tickers()
    while True:
        try:
            print("Iniciando Lemo...")
            updater = Updater(botApiToken, use_context=True)
            # Get the dispatcher to register handlers
            dp = updater.dispatcher

            #Add command handler
            cmds = {"start": start, "help": start, 
                    "list": send_pairs, "pairs": send_pairs, 
                    "sinais": sendSignal, "avgEmas": sigAvgEmas,
                    "arb": arbitragem, "triang": triangular
                    }

            for cmd in cmds.items():
                dp.add_handler(CommandHandler(cmd[0], cmd[1]))
                
            rgxHandlers = {"[Ss]uper.[EeÉé]rick": super_erick
                            ,"[Ll]emo": super_erick
                            }
            
            for handler in rgxHandlers.items():
                dp.add_handler(MessageHandler(Filters.regex(handler[0]), handler[1]))                            

            # log all errors
            dp.add_error_handler(error)

            #Polling
            # Start the Bot
            updater.start_polling()

            # Run the bot until you press Ctrl-C or the process receives SIGINT,
            # SIGTERM or SIGABRT. This should be used most of the time, since
            # start_polling() is non-blocking and will stop the bot gracefully.
            updater.idle()


        except KeyboardInterrupt:
            print("Exiting...")
            sys.exit()

        except Exception as e:
            print(str(e))
            sys.exit()




if __name__ == '__main__':
    main()
