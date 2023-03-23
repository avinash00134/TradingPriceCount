import json
import random
import re
import string
import datetime
import requests
from websocket import create_connection


def search(query, type):
    # type = 'stock' | 'futures' | 'forex' | 'cfd' | 'crypto' | 'index' | 'economic'
    # query = what you want to search!
    # it returns first matching item
    res = requests.get(
        f"https://symbol-search.tradingview.com/symbol_search/?text={query}&type={type}"
    )
    if res.status_code == 200:
        res = res.json()
        assert len(res) != 0, "Nothing Found."
        return res[0]
    else:
        print("Network Error!")
        exit(1)


def generateSession():
    stringLength = 12
    letters = string.ascii_lowercase
    random_string = "".join(random.choice(letters) for i in range(stringLength))
    return "qs_" + random_string


def prependHeader(st):
    return "~m~" + str(len(st)) + "~m~" + st


def constructMessage(func, paramList):
    return json.dumps({"m": func, "p": paramList}, separators=(",", ":"))


def createMessage(func, paramList):
    return prependHeader(constructMessage(func, paramList))


def sendMessage(ws, func, args):
    ws.send(createMessage(func, args))


def sendPingPacket(ws, result):
    pingStr = re.findall(".......(.*)", result)
    if len(pingStr) != 0:
        pingStr = pingStr[0]
        ws.send("~m~" + str(len(pingStr)) + "~m~" + pingStr)



def socketJob(ws):
    last_update_time = None
    while True:
        try:
            result = ws.recv()
            if "quote_completed" in result or "session_id" in result:
                continue
            Res = re.findall("^.*?({.*)$", result)
            if len(Res) != 0:
                jsonRes = json.loads(Res[0])

                if jsonRes["m"] == "qsd":
                    symbol = jsonRes["p"][1]["n"]
                    price = jsonRes["p"][1]["v"]["lp"]
                    current_time = datetime.datetime.now()
                    if last_update_time is not None:
                        time_diff = current_time - last_update_time
                        # getting the date & time and also the
                        print(f"{current_time.strftime('%Y-%m-%d %H:%M:%S')} {symbol} -> {price} ({time_diff.total_seconds()} seconds)")
                    else:
                        print(f"{current_time.strftime('%Y-%m-%d %H:%M:%S')} {symbol} -> {price}")
                    last_update_time = current_time
            else:
                sendPingPacket(ws, result)
        except KeyboardInterrupt:
            print("\nGoodbye!")
            exit(0)
        except Exception as e:
            print(f"ERROR: {e}\nTradingView message: {result}")
            continue



def getSymbolId(pair, market):
    data = search(pair, market)
    symbol_name = data["symbol"]
    try:
        broker = data["prefix"]
    except KeyError:
        broker = data["exchange"]
    symbol_id = f"{broker.upper()}:{symbol_name.upper()}"
    print(symbol_id, end="\n\n")
    return symbol_id


def main(pair, market):

    # serach btcusdt from crypto category
    symbol_id = getSymbolId(pair, market)

    # create tunnel
    tradingViewSocket = "wss://data.tradingview.com/socket.io/websocket"
    headers = json.dumps({"Origin": "https://data.tradingview.com"})
    ws = create_connection(tradingViewSocket, headers=headers)
    session = generateSession()

    # Send messages
    sendMessage(ws, "quote_create_session", [session])
    sendMessage(ws, "quote_set_fields", [session, "lp"])
    sendMessage(ws, "quote_add_symbols", [session, symbol_id])

    # Start job
    socketJob(ws)


if __name__ == "__main__":
    pair = "btcusdt"
    market = "crypto"
    main(pair, market)
