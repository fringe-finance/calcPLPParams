import json
from os import path
import requests
from loguru import logger
import time
import math


def getAbsPath(relPath):
    basepath = path.dirname(__file__)
    return path.abspath(path.join(basepath, relPath))


logger.add(getAbsPath("../../../logging/debtLimits.log"), rotation="10 days")


def getConfig():
    configFileName = getAbsPath("../../../config/config.json")
    with open(configFileName) as config:
        config = json.load(config)

    configFileName = getAbsPath("../../../config/coins.json")
    with open(configFileName) as coinsFile:
        config["coins"] = json.load(coinsFile)

    return config


def retryRequest(url, method="GET", headers={}, json={}, sleep=0):
    retries = 6
    for i in range(retries):
        try:
            print(url)
            if json != {}:
                response = requests.request(method, url, headers=headers, json=json)
            else:
                response = requests.request(method, url, headers=headers)
            responseJson = response.json()
            time.sleep(sleep)
        except:
            if i == retries - 1:
                logger.exception(str(url) + "\n\n" + str(json) + "\n\n" + response.text)
        else:
            break
    return responseJson


def getCMCSymbolSlugMap():
    symbolSlugMap = {}
    crypto = retryRequest(
        "https://s3.coinmarketcap.com/generated/core/crypto/cryptos.json", sleep=1
    )
    for coin in crypto["values"]:
        slug = coin[3]
        symbol = coin[2]
        symbolSlugMap[symbol] = slug
    return symbolSlugMap


def orderOfMagnitude(number):
    return 10 ** round(math.log(number, 10), 0)
