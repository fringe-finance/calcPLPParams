import sys
from os import path

sys.path.insert(0, path.dirname(__file__))

import csv
from loguru import logger
from datetime import datetime
from lvrUtils import *
from refreshPriceHistories import *
from binancePriceHistory import *


def findMarketsToAnalyse(markets):
    marketsToAnalyse = []
    reasonsForNoMarkets = []
    for market in markets["data"]:
        isOutlier = market["outlier"]
        isExcluded = market["excluded"]
        if isOutlier or isExcluded:
            reasonsForNoMarkets.append("a market is excluded or is outlier")
            continue
        exchange = market["exchange"]
        quoteAsset = market["quote"]
        url = market["link"]
        bidTotal = market["bidTotal"]
        quotePriceUSD = market["price"] / market["rate"]
        if not bidTotal:
            reasonsForNoMarkets.append("a market is missing bid total")
            continue

        if exchange in ["binance", "uniswapv2"]:
            if "us" not in quoteAsset.lower() and exchange == "binance":
                reasonsForNoMarkets.append("Binance quote asset is not USD stable")
                continue
            marketsToAnalyse.append(
                [exchange, quoteAsset, bidTotal, url, quotePriceUSD]
            )

    if marketsToAnalyse:
        topMarket = sorted(marketsToAnalyse, key=lambda l: l[2], reverse=True)[0]
    else:
        topMarket = {}

    return [topMarket, reasonsForNoMarkets]


def getTopMarketForEachCoin(coins):
    topMarketForEachCoin = {}

    headers = {
        "authority": "http-api.livecoinwatch.com",
        "accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.9",
        "accept-language": "en-GB,en-US;q=0.9,en;q=0.8",
        "cache-control": "no-cache",
        "pragma": "no-cache",
        "sec-fetch-dest": "document",
        "sec-fetch-mode": "navigate",
        "sec-fetch-site": "none",
        "sec-fetch-user": "?1",
        "sec-gpc": "1",
        "upgrade-insecure-requests": "1",
        "user-agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/100.0.4896.127 Safari/537.36",
    }
    for coin in coins:
        url = (
            "https://http-api.livecoinwatch.com/markets?currency=USD&limit=30&search=&offset=0&sort=depth&order=descending&coin="
            + coin.upper()
        )

        markets = retryRequest(url, headers=headers, sleep=2)
        topMarket, reasonsForNoMarkets = findMarketsToAnalyse(markets)
        if not topMarket:
            errorMessage = (
                "No markets were found for "
                + coin
                + ". The following potential causes were detected: "
                + " | ".join(reasonsForNoMarkets)
                + ". API: "
                + url
            )
            logger.debug(errorMessage)
            continue

        topMarketForEachCoin[coin] = {
            "exchange": topMarket[0],
            "quoteAsset": topMarket[1],
            "url": topMarket[3],
            "quotePriceUSD": topMarket[4],
        }
    return topMarketForEachCoin


def calcHighLowLVR(csvFile, minTimeThreshold, resultRowDepth):
    LVRList = []
    minLVR = getConfig()["lvrConfig"]["minLVR"]
    for period in csvFile:
        openTime = float(period["Open time"])
        if openTime < minTimeThreshold:
            continue
        if float(period["Close"]) < float(period["Open"]):
            highLowLVR = float(period["Low"]) / float(period["High"])
        else:
            highLowLVR = 1

        if highLowLVR < minLVR:
            continue

        readableOpenTime = datetime.utcfromtimestamp(openTime / 1000).strftime(
            "%Y-%m-%d %H:%M"
        )
        LVRandTime = list([openTime / 1000, readableOpenTime, highLowLVR])

        LVRList.append(LVRandTime)

    LVRList = sorted(LVRList, key=lambda d: d[2])[:resultRowDepth]
    return LVRList


def calcOpenCloseLVR(csvFile, minTimeThreshold, resultRowDepth):
    LVRList = []
    minLVR = getConfig()["lvrConfig"]["minLVR"]
    for period in csvFile:
        openTime = float(period["Open time"])
        if openTime < minTimeThreshold:
            continue
        openCloseLVR = float(period["Close"]) / float(period["Open"])

        if openCloseLVR < minLVR:
            continue

        readableOpenTime = datetime.utcfromtimestamp(openTime / 1000).strftime(
            "%Y-%m-%d %H:%M"
        )
        LVRandTime = list([openTime / 1000, readableOpenTime, openCloseLVR])

        LVRList.append(LVRandTime)

    LVRList = sorted(LVRList, key=lambda d: d[2])[:resultRowDepth]
    return LVRList


def calcWorstCaseLVR(csvFile, minTimeThreshold, resultRowDepth):
    LVRList = []
    minLVR = getConfig()["lvrConfig"]["minLVR"]
    for index, period in enumerate(csvFile):
        openTime = float(period["Open time"])
        if openTime < minTimeThreshold:
            continue

        if index < len(csvFile) - 1:
            worstCaseLVR = float(csvFile[index + 1]["Low"]) / float(period["High"])
        else:
            worstCaseLVR = 1

        if worstCaseLVR < minLVR:
            continue

        readableOpenTime = datetime.utcfromtimestamp(openTime / 1000).strftime(
            "%Y-%m-%d %H:%M"
        )

        LVRandTime = list([openTime / 1000, readableOpenTime, worstCaseLVR])

        LVRList.append(LVRandTime)

    LVRList = sorted(LVRList, key=lambda d: d[2])[:resultRowDepth]

    return LVRList


def calcMinTimeThreshold(csvFile):
    startTime = float(csvFile[0]["Open time"])
    endTime = float(csvFile[-1]["Open time"])
    percentOfHistoryToInclude = (
        getConfig()["lvrConfig"]["percentOfHistoryToInclude"] / 100
    )
    minTimeThreshold = (endTime - startTime) * (
        1 - percentOfHistoryToInclude
    ) + startTime
    return minTimeThreshold


def calcSortedLVRs():
    outputData = {}
    dataFolder = getAbsPath("../../../data/LVR/")
    resultRowDepth = getConfig()["lvrConfig"]["resultRowDepth"]
    for timePeriod in getConfig()["lvrConfig"]["timePeriods"]:
        CSVFolder = dataFolder + "/" + timePeriod + ".hr/"
        outputData[timePeriod] = {}
        csvFiles = os.scandir(CSVFolder)
        for csvFile in csvFiles:
            csvFilePath = CSVFolder + csvFile.name
            pair = csvFile.name.split("-")[0]
            outputData[timePeriod][pair] = {}

            with open(csvFilePath) as OHLCFile:
                csvFile = [entry for entry in csv.DictReader(OHLCFile)]
                minTimeThreshold = calcMinTimeThreshold(csvFile)
                if getConfig()["lvrConfig"]["includeHighLowLVR"]:
                    outputData[timePeriod][pair]["highLowLVR"] = calcHighLowLVR(
                        csvFile, minTimeThreshold, resultRowDepth
                    )
                if getConfig()["lvrConfig"]["includeOpenCloseLVR"]:
                    outputData[timePeriod][pair]["openCloseLVR"] = calcOpenCloseLVR(
                        csvFile, minTimeThreshold, resultRowDepth
                    )
                if getConfig()["lvrConfig"]["includeWorstCaseLVR"]:
                    outputData[timePeriod][pair]["worstCaseLVR"] = calcWorstCaseLVR(
                        csvFile, minTimeThreshold, resultRowDepth
                    )
    return outputData


def returnLVRs():
    toReloadData = getConfig()["lvrConfig"]["reloadData"]
    if toReloadData:
        coins = getConfig()["coins"].keys()
        topMarketForEachCoin = getTopMarketForEachCoin(coins)
        timePeriods = getConfig()["lvrConfig"]["timePeriods"]
        clearOldData()
        reloadBinanceData(timePeriods, topMarketForEachCoin)
        reloadCPMMPriceHistory(timePeriods, topMarketForEachCoin)
    sortedLVRs = calcSortedLVRs()
    return sortedLVRs
