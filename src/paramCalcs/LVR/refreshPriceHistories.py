from string import Template
from lvrUtils import *
import time
from datetime import datetime
from pathlib import Path
import csv

queryTemplate = Template(
    """
{
  ethereum(network: ethereum) {
    dexTrades(options: {limit: 24000}, any: [{baseCurrency: {is: "${quoteAddress}"}, quoteCurrency: {is: "0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48"}}, {baseCurrency: {is: "${quoteAddress}"}, quoteCurrency: {is: "0xdAC17F958D2ee523a2206206994597C13D831ec7"}}, {baseCurrency: {is: "${baseAddress}"}, quoteCurrency: {is: "${quoteAddress}"}}], date: {since: "${sinceDate}"}, tradeAmountUsd: {gt: 10}) {
      timeInterval {
        hour(format: "%FT%TZ", count: ${timePeriod})
      }
      buyCurrency: baseCurrency {
        symbol
        address
      }
      sellCurrency: quoteCurrency {
        symbol
        address
      }
      maximum_price: quotePrice(calculate: maximum)
      minimum_price: quotePrice(calculate: minimum)
      open_price: minimum(of: block, get: quote_price)
      close_price: maximum(of: block, get: quote_price)
    }
  }
}"""
)


def getUniV2Pair(url, quoteAsset):

    tokenAddress = url.replace("https://uniswap.exchange/swap/", "").lower()
    tokenAddress = (
        tokenAddress.replace("https://app.sushi.com/swap?inputCurrency=", "")
        .lower()
        .split("&outputcurrency=")
    )[0]
    allPairs = []
    for tokenIndex in range(0, 2):
        tokenIndex = str(tokenIndex)
        quoteIndex = str((int(tokenIndex) + 1) % 2)
        query = """{  pairs (orderBy: reserveUSD, orderDirection: desc, where: {token%(tokenIndex)s: "%(tokenAddress)s"}) 
    {
        id
        token0 {
            id
            symbol
        }
        token1 {
            id
            symbol
        }
        reserve0
        reserve1
        token0Price
        token1Price
        reserveUSD
        }
    }""" % {
            "tokenIndex": tokenIndex,
            "tokenAddress": tokenAddress,
        }
        pairs = retryRequest(
            "https://api.thegraph.com/subgraphs/name/uniswap/uniswap-v2",
            "POST",
            json={"query": query},
        )["data"]["pairs"]

        indexedPairs = []
        for pair in pairs:
            pair["tokenIndex"] = tokenIndex
            if quoteAsset.lower() in pair["token" + quoteIndex]["symbol"].lower():
                indexedPairs.append(pair)

        allPairs.extend(indexedPairs)

    topPair = sorted(
        allPairs, key=lambda pair: float(pair["reserveUSD"]), reverse=False
    )[0]

    if topPair["tokenIndex"] == "0":
        baseAddress = topPair["token0"]["id"].lower()
        quoteAddress = topPair["token1"]["id"].lower()

    elif topPair["tokenIndex"] == "1":
        baseAddress = topPair["token1"]["id"].lower()
        quoteAddress = topPair["token0"]["id"].lower()

    return [baseAddress, quoteAddress]


def runBitQuery(query):
    bitQueryApiKey = getConfig()["lvrConfig"]["bitQueryApiKey"]
    headers = {"X-API-KEY": bitQueryApiKey}

    response = retryRequest(
        "https://graphql.bitquery.io/", "POST", headers=headers, json={"query": query}
    )
    return response


def getCPMMHLOC(timePeriods, topMarketForEachCoin):
    tradingSnapshots = {}
    for timePeriod in timePeriods:
        tradingSnapshots[timePeriod] = {}
        for coin in topMarketForEachCoin:
            market = topMarketForEachCoin[coin]
            exchange = market["exchange"]
            url = market["url"]
            quoteAsset = market["quoteAsset"]
            if exchange != "uniswapv2":
                continue
            tradingSnapshots[timePeriod][coin] = []
            baseAddress, quoteAddress = getUniV2Pair(url, quoteAsset)
            unixTime, sinceDate, entries = 0, "2001-01-01", []
            while time.time() > unixTime + 24 * 60 * 60 * 3:
                query = queryTemplate.substitute(
                    baseAddress=baseAddress,
                    quoteAddress=quoteAddress,
                    timePeriod=timePeriod,
                    sinceDate=sinceDate,
                )
                HLOCData = runBitQuery(query)["data"]
                entries.extend(HLOCData["ethereum"]["dexTrades"])
                latestDateString = entries[-1]["timeInterval"]["hour"]
                dateFormat = datetime.strptime(latestDateString, "%Y-%m-%dT%H:%M:%SZ")
                unixTime = datetime.timestamp(dateFormat)
                sinceDate = latestDateString.split(" ")[0]
            tradingSnapshots[timePeriod][coin] = entries
    return tradingSnapshots


def calcUsdQuoteAssetPrices(uniswapHLOC):
    usdQuoteAssetPrices = {}
    for timePeriod in uniswapHLOC:
        usdQuoteAssetPrices[timePeriod] = {}
        for assetSymbol in uniswapHLOC[timePeriod]:
            usdQuoteAssetPrices[timePeriod][assetSymbol] = {}
            for entry in uniswapHLOC[timePeriod][assetSymbol]:
                sellCurrency = entry["sellCurrency"]["symbol"].lower()
                buyCurrency = entry["buyCurrency"]["symbol"].lower()
                timeInterval = entry["timeInterval"]["hour"]
                relevantUsdQuotePrices = usdQuoteAssetPrices[timePeriod][assetSymbol]
                sellCurrencyIsUSD = sellCurrency in ["usdc" or "usdt"]
                entry["open_price"] = float(entry["open_price"])
                entry["close_price"] = float(entry["close_price"])

                if sellCurrencyIsUSD and (assetSymbol.lower() not in buyCurrency):
                    averagePrice = (entry["open_price"] + entry["close_price"]) / 2
                    if timeInterval in relevantUsdQuotePrices:
                        combinedAvgPrice = (
                            relevantUsdQuotePrices[timeInterval] + averagePrice
                        ) / 2
                        usdQuoteAssetPrices[timePeriod][assetSymbol][
                            timeInterval
                        ] = combinedAvgPrice
                    else:
                        usdQuoteAssetPrices[timePeriod][assetSymbol][
                            timeInterval
                        ] = averagePrice
    return usdQuoteAssetPrices


def calcUsdCPMMHLOC(uniswapHLOC):
    usdPricedHLOC = {}
    usdQuoteAssetPrices = calcUsdQuoteAssetPrices(uniswapHLOC)

    for timePeriod in uniswapHLOC:
        usdPricedHLOC[timePeriod] = {}
        for assetSymbol in uniswapHLOC[timePeriod]:
            usdPricedHLOC[timePeriod][assetSymbol] = []
            for entry in uniswapHLOC[timePeriod][assetSymbol]:
                sellCurrency = entry["sellCurrency"]["symbol"].lower()
                buyCurrency = entry["buyCurrency"]["symbol"].lower()
                timeInterval = entry["timeInterval"]["hour"]
                relevantUsdQuotePrices = usdQuoteAssetPrices[timePeriod][assetSymbol]
                sellCurrencyIsUSD = sellCurrency in ["usdc" or "usdt"]
                entry["maximum_price"] = float(entry["maximum_price"])
                entry["minimum_price"] = float(entry["minimum_price"])
                entry["open_price"] = float(entry["open_price"])
                entry["close_price"] = float(entry["close_price"])
                if assetSymbol.lower() in buyCurrency:
                    if timeInterval in relevantUsdQuotePrices or sellCurrencyIsUSD:
                        usdPricedEntry = dict(entry)
                        if sellCurrencyIsUSD:
                            quoteAssetPrice = 1
                        else:
                            quoteAssetPrice = relevantUsdQuotePrices[timeInterval]
                            usdPricedEntry["sellCurrency"]["symbol"] = "USD"
                        usdPricedEntry["maximum_price"] *= quoteAssetPrice
                        usdPricedEntry["minimum_price"] *= quoteAssetPrice
                        usdPricedEntry["open_price"] *= quoteAssetPrice
                        usdPricedEntry["close_price"] *= quoteAssetPrice
                        usdPricedHLOC[timePeriod][assetSymbol].append(usdPricedEntry)
    return usdPricedHLOC


def savePriceHistory(usdPricedHLOC):
    dataFolder = getAbsPath("../../../data/LVR/")

    for timePeriod in usdPricedHLOC:
        Path(dataFolder + "/" + str(timePeriod) + ".hr").mkdir(
            parents=True, exist_ok=True
        )
        timePeriodFolder = dataFolder + "/" + str(timePeriod) + ".hr/"
        for assetSymbol in usdPricedHLOC[timePeriod]:
            csvData = []
            pair = (
                assetSymbol
                + usdPricedHLOC[timePeriod][assetSymbol][-1]["sellCurrency"]["symbol"]
            )
            for snapshot in usdPricedHLOC[timePeriod][assetSymbol]:
                openPrice = snapshot["open_price"]
                closePrice = snapshot["close_price"]
                highPrice = snapshot["maximum_price"]
                lowPrice = snapshot["minimum_price"]
                dateFormat = datetime.strptime(
                    snapshot["timeInterval"]["hour"], "%Y-%m-%dT%H:%M:%SZ"
                )
                unixTime = datetime.timestamp(dateFormat) * 1000
                row = {
                    "Open time": unixTime,
                    "Open": openPrice,
                    "High": highPrice,
                    "Low": lowPrice,
                    "Close": closePrice,
                }
                csvData.append(row)
                with open(
                    timePeriodFolder + pair + "-.csv", "w", newline=""
                ) as output_file:
                    dict_writer = csv.DictWriter(output_file, csvData[0].keys())
                    dict_writer.writeheader()
                    dict_writer.writerows(csvData)


def reloadCPMMPriceHistory(timePeriods, topMarketForEachCoin):
    CPMMHLOC = getCPMMHLOC(timePeriods, topMarketForEachCoin)
    usdPricedHLOC = calcUsdCPMMHLOC(CPMMHLOC)
    savePriceHistory(usdPricedHLOC)


def reloadCexPriceHistory():
    usdPricedHLOC = ""
    savePriceHistory(usdPricedHLOC)
