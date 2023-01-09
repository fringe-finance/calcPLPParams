import sys
from os import path
import json
import os
import shutil
import csv


sys.path.insert(0, path.dirname(__file__))

import LVR.calcLVR as lvr
import logDebtLimits


def getAbsPath(relPath):
    basepath = path.dirname(__file__)
    return path.abspath(path.join(basepath, relPath))


def getConfig():
    configFileName = getAbsPath("../../config/config.json")
    with open(configFileName) as config:
        config = json.load(config)

    configFileName = getAbsPath("../../config/coins.json")
    with open(configFileName) as coinsFile:
        config["coins"] = json.load(coinsFile)

    return config


def adjustLVR(lvr, lvrConservativeFactor, percentSlippageThreshold):
    slippageThreshold = int(percentSlippageThreshold) / 100
    lvrAdjustedBySlippagethreshold = 1 - ((1 - lvr) * (1 + slippageThreshold))
    finalLVR = lvrAdjustedBySlippagethreshold * lvrConservativeFactor
    return finalLVR


def adjustDebtLimit(debtLimit, debtLimitConservativeFactor):
    return debtLimit * debtLimitConservativeFactor


def calcAdjustedLVRs(latestLVRs):
    lvrConservativeFactor = getConfig()["adjustedParamCalcs"]["lvrConservativeFactor"]
    percentSlippageThreshold = getConfig()["adjustedParamCalcs"][
        "percentSlippageThreshold"
    ]
    adjustedLVRs = {}
    for timeperiod in latestLVRs:
        timeperiodLVRs = latestLVRs[timeperiod]
        adjustedLVRs[timeperiod] = {}
        for coin in timeperiodLVRs:
            coinLVRs = timeperiodLVRs[coin]
            adjustedLVRs[timeperiod][coin] = {}
            for lvrType in coinLVRs:
                lvrTypeLVRs = coinLVRs[lvrType]
                adjustedLVRs[timeperiod][coin][lvrType] = []
                for lvr in lvrTypeLVRs:
                    adjustedLVR = (
                        lvr[0],
                        lvr[1],
                        adjustLVR(
                            lvr[2], lvrConservativeFactor, percentSlippageThreshold
                        ),
                    )
                    adjustedLVRs[timeperiod][coin][lvrType].append(adjustedLVR)
    return adjustedLVRs


def caldAdjustedDebtLimits(compiledDebtLimits):
    adjustedDebtLimits = {}
    lvrConservativeFactor = getConfig()["adjustedParamCalcs"][
        "debtLimitConservativeFactor"
    ]
    for coin in compiledDebtLimits:
        adjustedDebtLimits[coin] = {}
        coinDebtLimits = compiledDebtLimits[coin]
        for debtLimit in coinDebtLimits:
            adjustedDebtLimits[coin][debtLimit] = adjustDebtLimit(
                coinDebtLimits[debtLimit], lvrConservativeFactor
            )
    return adjustedDebtLimits


def adjustHistoricalDebtLimitValues(historicalDebtLimitValues):
    lvrConservativeFactor = getConfig()["adjustedParamCalcs"][
        "debtLimitConservativeFactor"
    ]
    adjustedDebtLimits = []
    for debtLimit in historicalDebtLimitValues:
        adjustedDebtLimit = adjustDebtLimit(debtLimit[2], lvrConservativeFactor)
        adjustedDebtLimits.append([debtLimit[0], debtLimit[1], adjustedDebtLimit])
    return adjustedDebtLimits


def amalgamateDebtLimitTypes(coinDebtLimits):
    amalgamatedDebtLimits = {}
    for debtLimitType in coinDebtLimits:
        historicalDebtLimitValues = coinDebtLimits[debtLimitType]
        adjustedHistoricalDebtLimits = adjustHistoricalDebtLimitValues(
            historicalDebtLimitValues
        )
        for debtLimit in adjustedHistoricalDebtLimits:
            unixTime = debtLimit[0]
            dateTime = debtLimit[1]
            debtLimit = debtLimit[2]
            if unixTime not in amalgamatedDebtLimits:
                amalgamatedDebtLimits[unixTime] = {}
            amalgamatedDebtLimits[unixTime][debtLimitType] = debtLimit
            amalgamatedDebtLimits[unixTime]["dateTime"] = dateTime
            amalgamatedDebtLimits[unixTime]["unixTime"] = unixTime
            for key in coinDebtLimits.keys():
                if not key in amalgamatedDebtLimits[unixTime]:
                    amalgamatedDebtLimits[unixTime][key] = ""

    keys = ["unixTime", "dateTime"]
    keys.extend(coinDebtLimits.keys())

    return list(amalgamatedDebtLimits.values()), keys


def createHistoricalDebtLimitCSV():
    debtLimitLogPath = getAbsPath("../../data/debtLimit/debtLimitHistory.json")
    logFileText = open(debtLimitLogPath, "r").read()
    logFileText = logFileText if logFileText else "{}"
    debtLimitHistory = json.loads(logFileText)
    try:
        shutil.rmtree(getAbsPath("../../output/historicalDebtLimitCSV/"))
    except OSError as e:
        pass
    os.mkdir(getAbsPath("../../output/historicalDebtLimitCSV/"))
    for coin in debtLimitHistory:
        coinCSVPath = getAbsPath("../../output/historicalDebtLimitCSV/" + coin + ".csv")
        coinDebtLimits = debtLimitHistory[coin]
        amalgamatedDebtLimits, keys = amalgamateDebtLimitTypes(coinDebtLimits)
        with open(coinCSVPath, "w", newline="") as output_file:
            dict_writer = csv.DictWriter(output_file, keys)
            dict_writer.writeheader()
            dict_writer.writerows(amalgamatedDebtLimits)


def saveLatestDebtLimits(debtLimits):
    sortedDebtLimits = {}
    for coin in debtLimits:
        sortedDebtLimits[coin] = [
            [key, round(debtLimits[coin][key], 1)] for key in debtLimits[coin].keys()
        ]
        sortedDebtLimits[coin] = sorted(sortedDebtLimits[coin], key=lambda x: x[1])
    sortedDebtLimitsPath = getAbsPath("../../output/sortedLatestDebtLimits.json")
    with open(sortedDebtLimitsPath, "w") as sortedDebtLimitsFile:
        sortedDebtLimitsFile.write(json.dumps(sortedDebtLimits, indent=4))


def saveLatestAdjustedLVRs(adjustedLVRs):
    outputFilePath = getAbsPath("../../output/latestAdjustedLVRs.json")
    with open(outputFilePath, "w") as outputFile:
        outputFile.write(json.dumps(adjustedLVRs, indent=4))


def saveLatestAdjustedLVRsAndDebtLimits(debtLimits, adjustedLVRs):
    coinAttributes = {}

    coins = sorted(
        getConfig()["coins"].keys(),
        reverse=True,
        key=lambda x: len(x),
    )

    for coin in coins:
        coinAttributes[coin] = {"coin": coin}

    pairs = sorted(adjustedLVRs[list(adjustedLVRs.keys())[0]].keys())
    pairToCoinMapping = {}

    for pair in pairs:
        for coin in coins:
            if pair.lower().startswith(coin.lower()):
                pairToCoinMapping[pair] = coin
                break

    allDictKeys = ["coin"]
    for timeperiod in adjustedLVRs:
        timeperiodLVRs = adjustedLVRs[timeperiod]
        for pair in timeperiodLVRs:
            pairLVRs = timeperiodLVRs[pair]
            for lvrType in pairLVRs:
                lvrTypeLVRs = pairLVRs[lvrType]
                chosenLVR = lvrTypeLVRs[0][2]
                if pair in pairToCoinMapping:
                    coin = pairToCoinMapping[pair]
                    coinAttributes[coin][
                        "lvr" + str(timeperiod) + "H|" + lvrType
                    ] = chosenLVR
                    allDictKeys.append("lvr" + str(timeperiod) + "H|" + lvrType)

    for coin in debtLimits:
        for debtLimit in debtLimits[coin].keys():
            debtLimitValue = debtLimits[coin][debtLimit]
            coinAttributes[coin]["debtLimit" + str(debtLimit)] = debtLimitValue
            allDictKeys.append("debtLimit" + str(debtLimit))
        coinAttributes[coin]["debtLimitMin"] = min(debtLimits[coin].values())
        allDictKeys.append("debtLimitMin")

    allDictKeys = sorted(list(set(allDictKeys)))

    for coin in coinAttributes:
        for key in allDictKeys:
            if key not in coinAttributes[coin].keys():
                coinAttributes[coin][key] = ""

    lvrAndDebtLimitCSVPath = getAbsPath("../../output/latestLVRsAndDebtLimits.csv")

    with open(lvrAndDebtLimitCSVPath, "w", newline="") as output_file:
        dict_writer = csv.DictWriter(output_file, allDictKeys)
        dict_writer.writeheader()
        dict_writer.writerows(list(coinAttributes.values()))


if __name__ == "__main__":
    sortedLVRs = lvr.returnLVRs()
    adjustedLVRs = calcAdjustedLVRs(sortedLVRs)
    saveLatestAdjustedLVRs(adjustedLVRs)
    compiledDebtLimits = logDebtLimits.logAndReturnDebtLimits()
    adjustedDebtLimits = caldAdjustedDebtLimits(compiledDebtLimits)
    saveLatestDebtLimits(adjustedDebtLimits)
    createHistoricalDebtLimitCSV()
    saveLatestAdjustedLVRsAndDebtLimits(adjustedDebtLimits, adjustedLVRs)
