from debtLimUtils import *


def calcOBLiqAtSlippageThresholds(
    percentSlippageThresholds, bids, fracOfTotalBid, quotePriceUSD
):
    tmpPercentSlippageThresholds = list(percentSlippageThresholds)
    totalLiquidity = totalCoins = 0
    try:
        highestBidPrice = float(bids[0][0])
    except:
        print(bids)

    liquidityAtSlippageThresholds = {}

    for bid in bids:
        totalLiquidity += float(bid[0]) * float(bid[1])
        totalCoins += float(bid[1])
        averagePrice = totalLiquidity / totalCoins
        slippage = 1 - (averagePrice / highestBidPrice)
        estimatedUSDAllMarketLiquidityAtDepth = (
            totalLiquidity / fracOfTotalBid
        ) * quotePriceUSD

        if not tmpPercentSlippageThresholds:
            break
        if slippage >= tmpPercentSlippageThresholds[0] / 100:
            liquidityAtSlippageThresholds[
                tmpPercentSlippageThresholds[0]
            ] = estimatedUSDAllMarketLiquidityAtDepth
            del tmpPercentSlippageThresholds[0]

    if sorted(liquidityAtSlippageThresholds.keys()) != sorted(
        percentSlippageThresholds
    ):
        for threshold in percentSlippageThresholds:
            if threshold not in liquidityAtSlippageThresholds.keys():
                liquidityAtSlippageThresholds[
                    threshold
                ] = estimatedUSDAllMarketLiquidityAtDepth

    return liquidityAtSlippageThresholds


def calcUniV2LiqAtSlippageThresholds(
    topPair, fracOfTotalBid, percentSlippageThresholds, quotePriceUSD
):
    quoteIndex = str((int(topPair["assetIndex"]) + 1) % 2)
    assetIndex = topPair["assetIndex"]

    currentPrice = float(topPair["token" + quoteIndex + "Price"])
    quoteReserve = float(topPair["reserve" + quoteIndex])
    assetReserve = float(topPair["reserve" + assetIndex])

    liquidityAtSlippageThresolds = {}
    for threshold in percentSlippageThresholds:
        priceAtSlippageThreshold = currentPrice * (1 - threshold / 100)

        quoteAssetLiquidityUntilThreshold = priceAtSlippageThreshold * (
            quoteReserve / priceAtSlippageThreshold - assetReserve
        )
        quoteAssetLiquidityUntilThreshold /= fracOfTotalBid
        quoteAssetLiquidityUntilThreshold *= quotePriceUSD
        liquidityAtSlippageThresolds[threshold] = quoteAssetLiquidityUntilThreshold
    return liquidityAtSlippageThresolds


def compileLiqAtSlipThresholds(allLiqAtSlipThresholds):
    sumLiqAtSlipThresholds = {}
    for liqThresholds in allLiqAtSlipThresholds:
        for threshold in liqThresholds:
            if threshold not in sumLiqAtSlipThresholds:
                sumLiqAtSlipThresholds[threshold] = 0
            sumLiqAtSlipThresholds[threshold] += liqThresholds[threshold]

    return sumLiqAtSlipThresholds


def getAllCoinLiqudityAtSlippageThresholds(orderbookAndMarketData):
    liqAtSlippageThresholds = {}
    percentSlippageThresholds = sorted(
        getConfig()["debtLimitConfig"]["percentSlippageThresholds"]
    )

    for coin in orderbookAndMarketData:
        allLiqAtSlipThresholds = []
        fracOfTotalBid = sum(
            [mkt["fracOfTotalBid"] for mkt in orderbookAndMarketData[coin]]
        )  # determine what percent of total market the markets under analysis consist of
        for market in orderbookAndMarketData[coin]:
            exchange = market["exchange"]
            quotePriceUSD = market["quotePriceUSD"]
            print(coin, exchange, ":")
            if exchange in getConfig()["OBExchanges"]:
                bids = market["orderBookData"][0]
                liqAtSlippageThresholds[coin] = calcOBLiqAtSlippageThresholds(
                    percentSlippageThresholds, bids, fracOfTotalBid, quotePriceUSD
                )
            if exchange in getConfig()["CPMMExchanges"]:
                topPair = market["orderBookData"]
                liqAtSlippageThresholds[coin] = calcUniV2LiqAtSlippageThresholds(
                    topPair, fracOfTotalBid, percentSlippageThresholds, quotePriceUSD
                )
            allLiqAtSlipThresholds.append(liqAtSlippageThresholds)

    sumLiqAtSlipThresholds = compileLiqAtSlipThresholds(allLiqAtSlipThresholds)
    return sumLiqAtSlipThresholds
