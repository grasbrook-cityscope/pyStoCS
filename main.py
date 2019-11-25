import json
import requests
import time

class Table:
    cellSize = 0
    ncols = 0
    nrows = 0

    @staticmethod
    def fromCityIO(data):
        ret = Table()
        ret.cellSize = data["spatial"]["cellSize"]
        ret.ncols = data["spatial"]["ncols"]
        ret.nrows = data["spatial"]["nrows"]
        ret.mapping = data["mapping"]["type"]
        ret.typeidx = data["block"].index("type")
        return ret

def getFromCfg(key : str) -> str:
    #import os#os.path.dirname(os.path.realpath(__file__)+
    with open("config.json") as file:
        js = json.load(file)
        return js[key]

def getCurrentState(topic="", token=None):
    get_address = getFromCfg("input_url")+topic
    if token is None:
        r = requests.get(get_address, headers={'Content-Type': 'application/json'})
    else:
        r = requests.get(get_address, headers={'Content-Type': 'application/json', 'Authorization': 'Bearer '+token})
    
    if not r.status_code == 200:
        print("could not get from cityIO")
        print("Error code", r.status_code)

    return r.json()

def sendToCityIO(data, token=None):
    post_address = getFromCfg("output_url")

    if token is None:
        r = requests.post(post_address, json=data, headers={'Content-Type': 'application/json'})
    else:
        r = requests.post(post_address, json=data, headers={'Content-Type': 'application/json', 'Authorization': 'Bearer '+token})
    print(r)
    if not r.status_code == 200:
        print("could not post result to cityIO")
        print("Error code", r.status_code)
    else:
        print("Successfully posted to cityIO", r.status_code)

def run(token=None):
    gridDef = Table.fromCityIO(getCurrentState("header", token))
    if not gridDef:
        print("couldn't load input_url!")
        exit()

    gridData = getCurrentState("grid", token)
    gridHash = getCurrentState("meta/hashes/grid", token)

    typejs = {}
    with open("typedefs.json") as file:
        typejs = json.load(file)

    numWhiteCells = 0
    numGreyCells = 0
    numUnknownCells = 0
        
    for cell in gridData:
        if(cell is None or not "type" in gridDef.mapping[cell[gridDef.typeidx]]): continue
        curtype = gridDef.mapping[cell[gridDef.typeidx]]["type"]
        if curtype in typejs["white"]:
            numWhiteCells += 1
        elif curtype in typejs["grey"]:
            numGreyCells += 1
        else:
            numUnknownCells += 1

    expectedRain = 0.750 # in m³/m²a # todo: get from config

    whitewater_m3 = numWhiteCells * gridDef.cellSize * gridDef.cellSize * expectedRain
    graywater_m3 = numGreyCells * gridDef.cellSize * gridDef.cellSize * expectedRain
    unknown_m3 = numUnknownCells * gridDef.cellSize * gridDef.cellSize * expectedRain

    print("m³ white water to be handled: ", whitewater_m3)
    print("m³ grey water to be handled: ", graywater_m3)
    print("m³ unknown water to be handled: ", unknown_m3)

    data = {"unit":"cubic meters per annum","white":whitewater_m3,"grey":graywater_m3,"unknown":unknown_m3,"grid_hash":gridHash}

    sendToCityIO(data, token)
    

if __name__ == "__main__":
    oldHash = ""

    try:
        with open("token.txt") as f:
            token=f.readline()
        if token=="": token = None # happens with empty file
    except IOError:
        token=None

    while True:
        gridHash = getCurrentState("meta/hashes/grid", token)
        if gridHash != oldHash:
            run()
            oldHash = gridHash
        else:
            print("waiting for grid change")
            time.sleep(10)