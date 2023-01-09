import sys
from os import path
import json
import time
from datetime import datetime
from pathlib import Path

sys.path.insert(0, path.dirname(__file__))

import debtLimit.calcDebtLimits as debtLimit


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


def updateDebtLimitLog(compiledDebtLimits):
    currentTime = time.time()
    now = datetime.now()
    date_time = now.strftime("%m/%d/%Y--%H:%M:%S")
    debtLimitLogPath = getAbsPath("../../data/debtLimit/debtLimitHistory.json")
    debtLimitLogFile = Path(debtLimitLogPath)
    debtLimitLogFile.touch(exist_ok=True)
    logFileText = open(debtLimitLogPath, "r").read()
    logFileText = logFileText if logFileText else "{}"
    debtLimitHistory = json.loads(logFileText)
    for coin in compiledDebtLimits:
        if coin not in debtLimitHistory:
            debtLimitHistory[coin] = {}
        coinDebtLimits = compiledDebtLimits[coin]
        for debtLimit in coinDebtLimits:
            debtLimitValue = coinDebtLimits[debtLimit]
            if debtLimit not in debtLimitHistory[coin]:
                debtLimitHistory[coin][debtLimit] = []
            debtLimitHistory[coin][debtLimit].append(
                [currentTime, date_time, debtLimitValue]
            )
            debtLimitHistory[coin][debtLimit] = sorted(
                debtLimitHistory[coin][debtLimit], key=lambda l: l[0]
            )
        with open(debtLimitLogPath, "w") as debtLimitLogFile:
            debtLimitLogFile.write(json.dumps(debtLimitHistory, indent=4))


def logAndReturnDebtLimits():
    compiledDebtLimits = debtLimit.returnDebtLimits()
    updateDebtLimitLog(compiledDebtLimits)
    return compiledDebtLimits


if __name__ == "__main__":
    logAndReturnDebtLimits()
