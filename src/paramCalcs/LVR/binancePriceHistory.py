import os
from lvrUtils import *
import subprocess


def clearOldData():
    dataFolder = getAbsPath("../../../data/LVR/")
    for timePeriod in getConfig()["lvrConfig"]["timePeriods"]:
        os.system("rm -rf " + dataFolder + "/" + timePeriod + ".hr")
        os.system("mkdir " + dataFolder + "/" + timePeriod + ".hr")


def reloadBinanceData(timePeriods, topMarketForEachCoin):
    dataFolder = getAbsPath("../../../data/LVR/")
    generateCSVSHPath = getAbsPath("./generateCSV.sh")
    APIURLs = []
    for timePeriod in timePeriods:
        for coin in topMarketForEachCoin:
            market = topMarketForEachCoin[coin]
            exchange = market["exchange"]
            quoteAsset = market["quoteAsset"]
            pairName = (coin + quoteAsset).upper()
            if exchange != "binance":
                continue
            APIURL = (
                "https://s3-ap-northeast-1.amazonaws.com/data.binance.vision?delimiter=/&prefix=data/spot/monthly/klines/"
                + pairName
                + "/"
                + timePeriod
                + "h/"
            )
            APIURLs.append(APIURL)
    with open(dataFolder + "/OHLCUrls.txt", "w") as URLFile:
        URLFile.write("\n".join(APIURLs))

    process = subprocess.Popen([generateCSVSHPath, dataFolder])
    process.wait()

    clearOldData()
    for timePeriod in getConfig()["lvrConfig"]["timePeriods"]:
        os.system(
            "mv "
            + dataFolder
            + "/"
            + "*"
            + timePeriod
            + "h* "
            + dataFolder
            + "/"
            + timePeriod
            + ".hr"
        )
