import numpy as np
from debtLimUtils import *


def calcDebtLimitForX(x, lvr, xReserve, yReserve, isFinal):
    k = yReserve * xReserve
    initialPrice = yReserve / xReserve
    manipulationFactor = k / (initialPrice * (x**2))
    slippage = 1 - 1 / (
        ((((k / x) - yReserve) / (xReserve - x)) / (yReserve / xReserve))
    )
    slippageCostTotal = (yReserve * (xReserve - x) ** 2) / (xReserve * x)

    if manipulationFactor * lvr - 1 == 0:
        debtLimit = float("inf")
    else:
        debtLimit = (slippageCostTotal * manipulationFactor * lvr) / (
            manipulationFactor * lvr - 1
        )

    if isFinal:
        print(
            "manipFact:",
            manipulationFactor,
            "lvr:",
            lvr,
            "slippageCostTotal:",
            slippageCostTotal,
            "slippage:",
            slippage,
            "tradeSize:",
            slippageCostTotal / slippage,
        )
    return debtLimit, manipulationFactor


def getMinimaRange(startRange, endRange, lvr, xReserve, yReserve, maxManip):
    segments = 10
    xValues = list(np.linspace(startRange, endRange, segments))
    yValues = [calcDebtLimitForX(x, lvr, xReserve, yReserve, False) for x in xValues]
    diffs = list(np.diff(y[0] for y in yValues))  # diffs of debtLims, not manipFactors
    manipFactors = list(y[1] for y in yValues)
    minimaRange = 0
    points = [
        {"range": [xValues[i], xValues[i + 1]], "diff": diffs[i]}
        for i in range(len(diffs))
    ]
    lowEndOfLastRange = 0
    for point in points:
        diff = point["diff"]
        xRange = point["range"]
        if diff > 0:
            minimaRange = xRange
            minimaRange[0] = lowEndOfLastRange
            break
        lowEndOfLastRange = point["range"][0]

    if minimaRange == 0:
        print(startRange, endRange, lvr, xReserve, yReserve)
        print(points)
    return minimaRange


def getEndOfDebtLimitRange(lvr, xReserve, yReserve):
    k = yReserve * xReserve
    initialPrice = yReserve / xReserve
    return ((lvr * k) / initialPrice) ** 0.5 - 10**-10


def estMinDebtLimitXCoord(lvr, assetReserve, quoteReserve):
    nonAsymptoticIters = 0
    endOfRange = getEndOfDebtLimitRange(lvr, assetReserve, quoteReserve)
    startRange, endRange = getMinimaRange(
        0.0000000001, endOfRange, lvr, assetReserve, quoteReserve
    )

    while nonAsymptoticIters < 5:
        if startRange != 0 and endRange != endOfRange:
            startRange, endRange = getMinimaRange(
                startRange, endRange, lvr, assetReserve, quoteReserve
            )
            nonAsymptoticIters += 1
        else:
            startRange, endRange = getMinimaRange(
                startRange, endRange, lvr, assetReserve, quoteReserve
            )

    estimatedX = (startRange + endRange) / 2
    return estimatedX


def getUniV2DebtLimit(fracOfTotalAsk, quotePriceUSD, topPair, lvr):
    quoteIndex = str((int(topPair["assetIndex"]) + 1) % 2)
    assetIndex = topPair["assetIndex"]

    quoteReserve = float(topPair["reserve" + quoteIndex])
    assetReserve = float(topPair["reserve" + assetIndex])

    estimatedX = estMinDebtLimitXCoord(lvr, assetReserve, quoteReserve)

    debtLimit = calcDebtLimitForX(estimatedX, lvr, assetReserve, quoteReserve, False)
    debtLimit = (debtLimit * quotePriceUSD) / fracOfTotalAsk
    return debtLimit


def getOBDebtLimit(fracOfTotalAsk, quotePriceUSD, asks, lvr):
    totalLiquidity = totalCoins = 0
    lowestAskPrice = float(asks[0][0])
    lowestDebtLimit = 10**100
    for ask in asks:
        ask = float(ask[0]), float(ask[1])
        totalLiquidity += ask[0] * ask[1]
        totalCoins += ask[1]
        averagePrice = totalLiquidity / totalCoins
        slippage = (averagePrice / lowestAskPrice) - 1
        slippageCost = (averagePrice - lowestAskPrice) * totalCoins
        manipulationFactor = ask[0] / lowestAskPrice
        if lvr * manipulationFactor - 1 == 0:
            continue
        debtLimit = (slippageCost * manipulationFactor * lvr) / (
            lvr * manipulationFactor - 1
        )

        if round(debtLimit, 8) > 0:
            if debtLimit < lowestDebtLimit:
                lowestDebtLimit = debtLimit
                ATLDebtLimitSlippageCost = slippageCost
                ATLDebtLimitSlippage = slippage
                ATLDebtLimitTotalLiquidity = totalLiquidity
                ATLDebtLimitManipulationFactor = manipulationFactor
                print(
                    "manip:",
                    round(ATLDebtLimitManipulationFactor, 2),
                    ",lvr:",
                    round(lvr, 3),
                    ",debtLimit:",
                    round(lowestDebtLimit, 3),
                    ",slipCostUSD:",
                    round(ATLDebtLimitSlippageCost * quotePriceUSD, 2),
                    ",slipPercent",
                    str(round(ATLDebtLimitSlippage * 100, 2)) + "%",
                    ",totalLiqUSD:",
                    round(ATLDebtLimitTotalLiquidity * quotePriceUSD, 2),
                    ",fracOfTotalAsk:",
                    round(fracOfTotalAsk, 3),
                )

    if lowestDebtLimit == 10**100:
        lowestDebtLimit = slippageCost
        print("max manip factor too low: " + str(manipulationFactor))

    adjustedLowestDebtLimit = (lowestDebtLimit * quotePriceUSD) / fracOfTotalAsk
    return adjustedLowestDebtLimit


def calcManipDebtLimits(orderbookAndMarketData):
    debtLimits = {}
    coins = getConfig()["coins"]
    for coin in orderbookAndMarketData:
        fracOfTotalAsk = sum(
            [mkt["fracOfTotalAsk"] for mkt in orderbookAndMarketData[coin]]
        )  # determine what percent of total market the markets under analysis consist of
        for market in orderbookAndMarketData[coin]:
            quotePriceUSD = market["quotePriceUSD"]
            exchange = market["exchange"]
            lvr = coins[coin]["lvr"]
            print(coin, ":")
            if exchange in getConfig()["OBExchanges"]:
                asks = market["orderBookData"][1]
                debtLimits[coin] = getOBDebtLimit(
                    fracOfTotalAsk, quotePriceUSD, asks, lvr
                )
            if exchange in getConfig()["CPMMExchanges"]:
                topPair = market["orderBookData"]
                debtLimits[coin] = getUniV2DebtLimit(
                    fracOfTotalAsk, quotePriceUSD, topPair, lvr
                )

    return debtLimits


if __name__ == "__main__":
    assetReserve = 1
    quoteReserve = 1
    quotePriceUSD = 0.062
    fracOfTotalBid = 1
    valueOfAsk = quotePriceUSD * quoteReserve
    for i in range(9):
        lvr = (i + 1) * (1 / 10)
        estimatedX = estMinDebtLimitXCoord(lvr, assetReserve, quoteReserve)
        debtLimit = calcDebtLimitForX(estimatedX, lvr, assetReserve, quoteReserve, True)
        debtLimit = (debtLimit * quotePriceUSD) / fracOfTotalBid
        # print(str(lvr) + ",", debtLimit / valueOfAsk)
