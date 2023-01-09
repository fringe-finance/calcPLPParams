from email.quoprimime import quote
import sys
from os import path
import time
import math
import base64
import hmac
import hashlib

sys.path.insert(0, path.dirname(__file__))

from debtLimUtils import *


def getBinanceOrderbook(coin, quoteAsset):
    pairName = (coin.strip("_") + quoteAsset).upper()
    orderBookUrl = (
        "https://api.binance.com/api/v3/depth?symbol=" + pairName + "&limit=100000"
    )
    for i in range(6):
        try:
            orderbook = retryRequest(orderBookUrl, sleep=2)
            bids, asks = orderbook["bids"], orderbook["asks"]
        except:
            if i == 5:
                logger.exception(str(orderBookUrl) + "\n\n" + str(orderbook))
        else:
            break

    return bids, asks


# def getFTXOrderbook(coin, quoteAsset): ##doesn't return enough depth. Only 6% price manip w/ 100 (max= 100)depth for KNC USD
#     pairName = (coin.strip("_") + "/" + quoteAsset).upper()
#     orderBookUrl = "https://ftx.com/api/markets/" + pairName + "/orderbook?depth=100"
#     orderbook = retryRequest(orderBookUrl, sleep=0.5)["result"]
#     bids, asks = orderbook["bids"], orderbook["asks"]

#     return bids, asks


def getGateOrderbook(coin, quoteAsset):
    pairName = (coin.strip("_") + "_" + quoteAsset).upper()
    orderBookUrl = (
        "https://api.gateio.ws/api/v4/spot/order_book?limit=5000&currency_pair="
        + pairName
    )
    orderbook = retryRequest(orderBookUrl, sleep=0.5)
    bids, asks = orderbook["bids"], orderbook["asks"]

    return bids, asks


def getGeminiOrderbook(coin, quoteAsset):
    pairName = (coin.strip("_") + quoteAsset).lower()
    orderBookUrl = (
        "https://api.gemini.com/v1/book/" + pairName + "?limit_bids=0&limit_asks=0"
    )
    orderbook = retryRequest(orderBookUrl, sleep=0.5)
    bids = [[bid["price"], bid["amount"]] for bid in orderbook["bids"]]
    asks = [[ask["price"], ask["amount"]] for ask in orderbook["asks"]]

    return bids, asks


def getHuobiOrderbook(coin, quoteAsset):
    pairName = (coin.strip("_") + quoteAsset).lower()
    orderBookUrl = (
        "https://api.huobi.pro/market/depth?symbol=" + pairName + "&type=step3"
    )
    orderbook = retryRequest(orderBookUrl, sleep=0.5)
    bids = orderbook["tick"]["bids"]
    asks = orderbook["tick"]["asks"]

    return bids, asks


def getPoloniexOrderbook(coin, quoteAsset, scaleOfPrice):
    pairName = (coin.strip("_") + "_" + quoteAsset).lower()
    orderBookUrl = (
        "https://api.poloniex.com/markets/"
        + pairName
        + "/orderBook?limit=150&scale="
        + str(scaleOfPrice)
    )
    orderbook = retryRequest(orderBookUrl, sleep=1)

    bids, asks = [], []
    for i in range(0, len(orderbook["bids"]), 2):
        bids.append(orderbook["bids"][i : i + 2])
    for i in range(0, len(orderbook["asks"]), 2):
        asks.append(orderbook["asks"][i : i + 2])

    return bids, asks


def getMexcOrderbook(coin, quoteAsset):
    pairName = (coin.strip("_") + quoteAsset).upper()
    orderBookUrl = (
        "https://api.mexc.com/api/v3/depth?symbol=" + pairName + "&limit=5000"
    )
    orderbook = retryRequest(orderBookUrl, sleep=0.5)
    bids = orderbook["bids"]
    asks = orderbook["asks"]

    return bids, asks


# def getCurrencyComOrderbook(coin, quoteAsset): #very weird orderbook data (discontinuous jumps btwn liq & iliq sections) https://marketcap.backend.currency.com/api/v1/token_crypto/orderbook?symbol=KNC/USDT
#     pairName = (coin.strip("_") + "/" + quoteAsset).upper()
#     pairName = pairName.replace("0X", "0x")  # WTF is going on
#     orderBookUrl = (
#         "https://marketcap.backend.currency.com/api/v1/token_crypto/orderbook?symbol="
#         + pairName
#     )
#     orderbook = retryRequest(orderBookUrl, sleep=0.5)
#     bids = orderbook["bids"]
#     asks = orderbook["asks"]

#     return bids, asks


# def getBitrueOrderbook(coin, quoteAsset): #not enough depth https://openapi.bitrue.com/api/v1/depth?limit=1000000&symbol=FXSUSDT
#     pairName = (coin.strip("_") + quoteAsset).upper()
#     orderBookUrl = (
#         "https://openapi.bitrue.com/api/v1/depth?limit=1000000&symbol=" + pairName
#     )
#     orderbook = retryRequest(orderBookUrl, sleep=0.5)
#     bids = [bid[:2] for bid in orderbook["bids"]]
#     asks = [ask[:2] for ask in orderbook["asks"]]

#     return bids, asks


def getBiboxOrderbook(coin, quoteAsset):
    pairName = (coin.strip("_") + "_" + quoteAsset).upper()
    orderBookUrl = (
        "https://api.bibox.com/api/v4/marketdata/order_book?level=1000&symbol="
        + pairName
    )
    orderbook = retryRequest(orderBookUrl, sleep=0.5)
    bids = orderbook["b"]
    asks = orderbook["a"]

    return bids, asks


def getPexpayOrderbook(coin, quoteAsset):
    pairName = (coin.strip("_") + quoteAsset).upper()
    orderBookUrl = (
        "https://www.commonservice.io/api/v3/depth?limit=100000000000&symbol="
        + pairName
    )
    orderbook = retryRequest(orderBookUrl, sleep=0.5)
    bids = orderbook["bids"]
    asks = orderbook["asks"]

    return bids, asks


# Other exchanges:
# https://www.biconomy.com/api/v1/depth?symbol=BTC_USDT&size=100 #insufficiently liquid
# https://api.crypto.com/v2/public/get-book?instrument_name=ZRX_USDT&depth=150 ##not good for v liquid assets like btc due to no aggregation
# https://open-api.bingx.com/openApi/spot/v1/market/depth?limit=100&symbol=ZRX-USDT #not enough data
# https://api.bybit.com/v2/public/orderBook/L2?symbol=BTCUSD ##extremely low depth :/
# https://api.coinw.com/api/v1/public?command=returnOrderBook&symbol=BTC_CNYT&size=20 does not work ("param error" in chinese chars)
# https://nominex.io/api/rest/v1/orderbook/ETH/BTC/A2/100 500 cloudflare error


# def getBitgetOrderbook(coin, quoteAsset): ###Doesn't work most of time, due to sometimes wantint SPBL postfix, and other times UMCBL
#     pairName = (coin.strip("_") + quoteAsset).upper()
#     orderBookUrl = (
#         "https://api.bitget.com/api/mix/v1/market/depth?symbol=" + pairName + "_SPBL"
#     )
#     orderbook = retryRequest(orderBookUrl, sleep=0.5)
#     bids = orderbook["data"]["bids"]
#     asks = orderbook["data"]["asks"]

#     return bids, asks


# def getAexOrderbook(coin, quoteAsset): #only returns a few percent depth, not configurable
#     pairName = ("?coinname=" + coin.strip("_") + "&mk_type=" + quoteAsset).lower()
#     orderBookUrl = "https://api.aex.zone/v3/depth.php" + pairName
#     orderbook = retryRequest(orderBookUrl, sleep=0.5)
#     bids = orderbook["data"]["bids"]
#     asks = orderbook["data"]["asks"]

#     return bids, asks


# def getDigifinexOrderbook(coin, quoteAsset): #insufficient depth max 5% on ask side returned w/150 limit for KNC usdt :/
#     pairName = (coin.strip("_") + "_" + quoteAsset).lower()
#     orderBookUrl = (
#         "https://openapi.digifinex.com/v3/order_book?symbol=" + pairName + "&limit=150"
#     )
#     orderbook = retryRequest(orderBookUrl, sleep=0.5)
#     bids = orderbook["bids"]
#     asks = orderbook["asks"]
#     asks.reverse()
#     return bids, asks


# def getCoinDCXOrderbook(coin, quoteAsset): #only returns a few % depth for I- markets (indicating coindcx markets rather than other exs), doesn't have any further customisation
#     pairName = (coin.strip("_") + "_" + quoteAsset).upper()
#     orderBookUrl = "https://public.coindcx.com/market_data/orderbook?pair=I-" + pairName
#     orderbook = retryRequest(orderBookUrl, sleep=0.5)
#     bids = [[price, orderbook["bids"][price]] for price in orderbook["bids"]]
#     asks = [[price, orderbook["asks"][price]] for price in orderbook["asks"]]
#     return bids, asks


# def getBKexOrderbook(coin, quoteAsset, scaleOfPrice):  # max 50 depth but does not return enough depth for some reason even when within 50 order limit...
#     pairName = (coin.strip("_") + "_" + quoteAsset).upper()
#     precision = 0 - int(round(math.log(scaleOfPrice, 10)))
#     orderBookUrl = (
#         "https://api.bkex.com/v2/q/depth?symbol="
#         + pairName
#         + "&depth=50&precision="
#         + str(precision)
#     )
#     orderbook = retryRequest(orderBookUrl, sleep=0.5)
#     bids = orderbook["data"]["bid"]
#     asks = orderbook["data"]["ask"]
#     return bids, asks


def getFmfwOrderbook(coin, quoteAsset):
    pairName = (coin.strip("_") + quoteAsset).upper()
    orderBookUrl = (
        "https://api.fmfw.io/api/3/public/orderbook?depth=0&symbols=" + pairName
    )
    orderbook = retryRequest(orderBookUrl, sleep=0.5)
    bids = orderbook[pairName]["bid"]
    asks = orderbook[pairName]["ask"]
    return bids, asks


def getKucoinOrderbook(coin, quoteAsset):
    pairName = (coin.strip("_") + "-" + quoteAsset).upper()
    exchangeApiKeys = getConfig()["exchangeApiKeys"]
    timestamp = int(time.time() * 1000)
    str_to_sign = (
        str(timestamp) + "GET" + "/api/v3/market/orderbook/level2?symbol=" + pairName
    )

    signature = base64.b64encode(
        hmac.new(
            exchangeApiKeys["kucoinSecret"].encode("utf-8"),
            str_to_sign.encode("utf-8"),
            hashlib.sha256,
        ).digest()
    ).decode("utf-8")
    passphrase = base64.b64encode(
        hmac.new(
            exchangeApiKeys["kucoinSecret"].encode("utf-8"),
            exchangeApiKeys["kucoinPass"].encode("utf-8"),
            hashlib.sha256,
        ).digest()
    ).decode("utf-8")

    snapshot_url = (
        f"https://api.kucoin.com/api/v3/market/orderbook/level2?symbol={pairName}"
    )
    headers = {
        "KC-API-KEY": exchangeApiKeys["kucoinKey"],
        "KC-API-PASSPHRASE": passphrase,
        "KC-API-TIMESTAMP": str(int(time.time() * 1000)),
        "KC-API-KEY-VERSION": "2",
        "KC-API-SIGN": signature,
    }
    orderbook = retryRequest(snapshot_url, sleep=1, headers=headers)
    # print("KUCOIN:\n\n\n" + str(orderbook))
    bids = orderbook["data"]["bids"]
    asks = orderbook["data"]["asks"]
    return bids, asks


def getUniV2Pair(url, quoteAsset):
    pairId = url.replace("https://coinmarketcap.com/dexscan/ethereum/", "").lower()
    query = """{
    pair(id: "%(pairId)s") {
    {
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
        "pairId": pairId,
    }

    pair = retryRequest(
        "https://api.thegraph.com/subgraphs/name/uniswap/uniswap-v2",
        "POST",
        json={"query": query},
        sleep=0.5,
    )["data"]["pair"]

    if pair["token0"]["symbol"].lower() == quoteAsset.lower():
        pair["assetIndex"] = 0
    else:
        pair["assetIndex"] = 1

    return pair


def getSushiPair(url, quoteAsset):
    pairId = url.replace("https://coinmarketcap.com/dexscan/ethereum/", "").lower()
    query = """{
    pair(id: "%(pairId)s") {
    {
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
        "pairId": pairId,
    }

    pair = retryRequest(
        "https://api.thegraph.com/subgraphs/name/sushiswap/exchange",
        "POST",
        json={"query": query},
        sleep=0.5,
    )["data"]["pair"]

    if pair["token0"]["symbol"].lower() == quoteAsset.lower():
        pair["assetIndex"] = 0
    else:
        pair["assetIndex"] = 1

    return pair


def getSunSwapPair(coin, quoteAsset):
    pairs = []
    page = 1
    hasMore = True
    while hasMore:
        response = retryRequest(
            "https://pabc.endjgfsv.link/swapv2/scan/searchPairList?pageNo="
            + str(page)
            + "&keyword="
            + coin.lower(),
            sleep=0.5,
        )
        hasMore = response["data"]["hasMore"]
        newPairs = response["data"]["list"]
        pairs.extend(newPairs)
        page += 1

    relevantPairs = []
    for pair in pairs:
        symbols = [pair["token1Symbol"].lower(), pair["token0Symbol"].lower()]
        if coin.lower() in symbols and quoteAsset.lower() in symbols:
            relevantPairs.append(pair)

    topPair = sorted(pairs, key=lambda pair: float(pair["liquidity"]), reverse=False)[0]

    if topPair["token0Symbol"].lower() == quoteAsset.lower():
        pair["assetIndex"] = 0
    else:
        pair["assetIndex"] = 1

    return pair


# def getUniV2Pair(url, quoteAsset):

#     tokenAddress = url.replace("https://uniswap.exchange/swap/", "").lower()
#     allPairs = []
#     for tokenIndex in range(0, 2):
#         tokenIndex = str(tokenIndex)
#         quoteIndex = str((int(tokenIndex) + 1) % 2)
#         query = """{  pairs (orderBy: reserveUSD, orderDirection: desc, where: {token%(tokenIndex)s: "%(tokenAddress)s"})
#     {
#         id
#         token0 {
#             id
#             symbol
#         }
#         token1 {
#             id
#             symbol
#         }
#         reserve0
#         reserve1
#         token0Price
#         token1Price
#         reserveUSD
#         }
#     }""" % {
#             "tokenIndex": tokenIndex,
#             "tokenAddress": tokenAddress,
#         }

#         pairs = retryRequest(
#             "https://api.thegraph.com/subgraphs/name/uniswap/uniswap-v2",
#             "POST",
#             json={"query": query},
#             sleep=0.5,
#         )["data"]["pairs"]

#         indexedPairs = []
#         for pair in pairs:
#             pair["assetIndex"] = tokenIndex
#             if quoteAsset in pair["token" + quoteIndex]["symbol"].lower():
#                 indexedPairs.append(pair)

#         allPairs.extend(indexedPairs)

#     topPair = sorted(
#         allPairs, key=lambda pair: float(pair["reserveUSD"]), reverse=False
#     )[0]

#     return topPair


# def getSushiPair(url, quoteAsset):

#     tokenAddress = (
#         url.replace("https://app.sushi.com/swap?inputCurrency=", "")
#         .lower()
#         .split("&outputcurrency=")
#     )[0]

#     allPairs = []
#     for tokenIndex in range(0, 2):
#         tokenIndex = str(tokenIndex)
#         quoteIndex = str((int(tokenIndex) + 1) % 2)
#         query = """{  pairs (orderBy: reserveUSD, orderDirection: desc, where: {token%(tokenIndex)s: "%(tokenAddress)s"})
#     {
#         id
#         token0 {
#             id
#             symbol
#         }
#         token1 {
#             id
#             symbol
#         }
#         reserve0
#         reserve1
#         token0Price
#         token1Price
#         reserveUSD
#         }
#     }""" % {
#             "tokenIndex": tokenIndex,
#             "tokenAddress": tokenAddress,
#         }

#         pairs = retryRequest(
#             "https://api.thegraph.com/subgraphs/name/sushiswap/exchange",
#             "POST",
#             json={"query": query},
#             sleep=0.5,
#         )["data"]["pairs"]

#         indexedPairs = []
#         for pair in pairs:
#             pair["assetIndex"] = tokenIndex
#             if quoteAsset.lower() in pair["token" + quoteIndex]["symbol"].lower():
#                 indexedPairs.append(pair)

#         allPairs.extend(indexedPairs)

#     topPair = sorted(
#         allPairs, key=lambda pair: float(pair["reserveUSD"]), reverse=False
#     )[0]

#     return topPair


if __name__ == "__main__":
    print(getFmfwOrderbook("BTC", "USDT"))
