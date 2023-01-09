import sys
from os import path

sys.path.insert(0, path.dirname(__file__))

from loguru import logger
from debtLimUtils import *
from priceManipCalc import *
from slippageThresholds import *
from getOrderbooks import *


def findMarketsToAnalyse(markets):
    allMarketsTotalBid = 0
    allMarketsTotalAsk = 0
    marketsToAnalyse = []
    reasonsForNoMarkets = []
    symbol = markets["data"]["symbol"]
    allExchanges = getConfig()["OBExchanges"] + getConfig()["CPMMExchanges"]
    for market in markets["data"]["marketPairs"]:
        # definitions
        exchange = market["exchangeSlug"]
        reversedPair = True if "quoteSymbol" == symbol else False
        quote = market["quoteSymbol"] if not reversedPair else market["baseSymbol"]
        base = market["baseSymbol"] if not reversedPair else market["quoteSymbol"]
        url = market["dexerUrl"] if "dexerUrl" in market else market["marketUrl"]
        bidTotal = market["depthUsdNegativeTwo"]
        askTotal = market["depthUsdPositiveTwo"]
        isOutlier = True if market["priceExcluded"] == 1 else False
        isExcluded = True if market["outlierDetected"] == 1 else False
        quotePriceUSD = market["price"] / market["quote"]
        scaleOfPrice = orderOfMagnitude(market["price"] / 100)

        # checks
        if reversedPair:
            if exchange not in getConfig()["CPMMExchanges"]:
                reasonsForNoMarkets.append(
                    "non CPMM mkt has asset as quote rather than base"
                )
                continue  ##too complex to handle in case of CLOB
            bidTotal, askTotal = [askTotal, bidTotal]
            quotePriceUSD = market["quote"]

        if exchange in [""]:  # false pos blacklisted exchanges
            isOutlier = isExcluded = False

        if exchange in ["rekeningku-com"]:  # false neg blacklisted exchanges
            isOutlier = isExcluded = True

        if isOutlier or isExcluded:
            reasonsForNoMarkets.append("a market is excluded or is outlier")
            continue

        if not (bidTotal and askTotal):
            reasonsForNoMarkets.append("a market is missing bid/ask total")
            continue

        # effects
        allMarketsTotalBid += bidTotal
        allMarketsTotalAsk += askTotal
        if exchange in allExchanges:
            marketsToAnalyse.append(
                {
                    "exchange": exchange,
                    "url": url,
                    "quoteAsset": quote,
                    "baseAsset": base,
                    "bidTotal": bidTotal,
                    "askTotal": askTotal,
                    "quotePriceUSD": quotePriceUSD,
                    "scaleOfPrice": scaleOfPrice,
                }
            )

    if marketsToAnalyse:
        sortedMarkets = sorted(
            marketsToAnalyse,
            key=lambda mkt: mkt["bidTotal"] * mkt["askTotal"],
            reverse=True,
        )
    else:
        sortedMarkets = []

    return [sortedMarkets, allMarketsTotalBid, allMarketsTotalAsk, reasonsForNoMarkets]


def getSortedMarketsForEachCoin(coins):
    topMarketForEachCoin = {}
    symbolSlugMap = getCMCSymbolSlugMap()

    headers = {
        "authority": "api.coinmarketcap.com",
        "accept": "application/json, text/plain, */*",
        "accept-language": "en-GB,en;q=0.7",
        "cache-control": "no-cache",
        "origin": "https://coinmarketcap.com",
        "platform": "web",
        "pragma": "no-cache",
        "referer": "https://coinmarketcap.com/",
        "sec-fetch-dest": "empty",
        "sec-fetch-mode": "cors",
        "sec-fetch-site": "same-site",
        "sec-gpc": "1",
        "user-agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/104.0.5112.102 Safari/537.36",
    }

    for coin in coins:
        if coins[coin].get("cmcSlug", ""):
            cmcSlug = coins[coin].get("cmcSlug", "")
        else:
            cmcSlug = symbolSlugMap[coin.upper()]
        url = (
            "https://api.coinmarketcap.com/data-api/v3/cryptocurrency/market-pairs/latest?slug="
            + cmcSlug
            + "&start=1&limit=100&category=spot&sort=cmc_rank_advanced"
        )

        markets = retryRequest(url, headers=headers, sleep=2)
        (
            sortedMarkets,
            allMarketsTotalBid,
            allMarketsTotalAsk,
            reasonsForNoMarkets,
        ) = findMarketsToAnalyse(markets)
        if not sortedMarkets:
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

        for market in sortedMarkets:
            bidTotal = market["bidTotal"]
            askTotal = market["askTotal"]
            fracOfTotalBid = bidTotal / allMarketsTotalBid
            fracOfTotalAsk = askTotal / allMarketsTotalAsk
            sortedMarkets[market]["fracOfTotalBid"] = fracOfTotalBid
            sortedMarkets[market]["fracOfTotalAsk"] = fracOfTotalAsk

    return sortedMarkets


def getOrderbookData(sortedMarketsForEachCoin):
    for coin in sortedMarketsForEachCoin:
        for market in sortedMarketsForEachCoin[coin]:
            baseAsset = market["baseAsset"].lower()  # usually should be same as coin
            exchange = market["exchange"]
            quoteAsset = market["quoteAsset"].lower()
            scaleOfPrice = market["scaleOfPrice"]
            url = market["url"]

            print(coin, quoteAsset, exchange, ":")

            if exchange == "binance":
                orderbookData = getBinanceOrderbook(baseAsset, quoteAsset)
            if exchange == "gate-io":
                orderbookData = getGateOrderbook(baseAsset, quoteAsset)
            if exchange == "gemini":
                orderbookData = getGeminiOrderbook(baseAsset, quoteAsset)
            if exchange == "poloniex":
                orderbookData = getPoloniexOrderbook(
                    baseAsset, quoteAsset, scaleOfPrice
                )
            if exchange == "huobi-global":
                orderbookData = getHuobiOrderbook(baseAsset, quoteAsset)
            if exchange == "kucoin":
                orderbookData = getKucoinOrderbook(baseAsset, quoteAsset)
            if exchange == "mxc":
                orderbookData = getMexcOrderbook(baseAsset, quoteAsset)
            if exchange == "bitcoin-com-exchange":
                orderbookData = getFmfwOrderbook(baseAsset, quoteAsset)
            if exchange == "bibox":
                orderbookData = getBiboxOrderbook(baseAsset, quoteAsset)
            if exchange == "pexpay":
                orderbookData = getPexpayOrderbook(baseAsset, quoteAsset)

            if exchange == "uniswap-v2":
                orderbookData = getUniV2Pair(url, quoteAsset)
            if exchange == "sushiswap":
                orderbookData = getSushiPair(url, quoteAsset)

            sortedMarketsForEachCoin[coin]["orderBookData"] = orderbookData
    return sortedMarketsForEachCoin


def compileDebtLimits(debtLimits, liquidityAtSlippageThresholds):
    compiledDebtLimits = {}
    for coin in liquidityAtSlippageThresholds:
        coinDebtLimit = debtLimits[coin]
        compiledDebtLimits[coin] = dict(liquidityAtSlippageThresholds[coin])
        compiledDebtLimits[coin]["priceManip"] = coinDebtLimit
        origDebtLimits = dict(compiledDebtLimits[coin])
        compiledDebtLimits[coin] = {}
        for debtLimit in origDebtLimits:
            compiledDebtLimits[coin][str(debtLimit)] = round(
                origDebtLimits[debtLimit], 1
            )

    return compiledDebtLimits


def returnDebtLimits():
    coins = getConfig()["coins"]
    sortedMarketsForEachCoin = getSortedMarketsForEachCoin(coins)
    orderbookAndMarketData = getOrderbookData(sortedMarketsForEachCoin)
    liquidityAtSlippageThresholds = getAllCoinLiqudityAtSlippageThresholds(
        orderbookAndMarketData
    )
    debtLimits = calcManipDebtLimits(orderbookAndMarketData)
    compiledDebtLimits = compileDebtLimits(debtLimits, liquidityAtSlippageThresholds)
    return compiledDebtLimits
