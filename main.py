import json
import urllib.request 

def getFromCfg(key : str) -> str:
    #import os#os.path.dirname(os.path.realpath(__file__)+
    with open("config.json") as file:
        js = json.load(file)
        return js[key]

def getCurrentState():
    with urllib.request.urlopen(getFromCfg("input_url")) as url:    # todo: do with requests instead of urllib
        return json.loads(url.read().decode())
    return None

class Grid:
    cellSize = 0
    ncols = 0
    nrows = 0

    @staticmethod
    def fromCityIO(data):
        ret = Grid()
        ret.cellSize = data["header"]["spatial"]["cellSize"]
        ret.ncols = data["header"]["spatial"]["ncols"]
        ret.nrows = data["header"]["spatial"]["nrows"]
        ret.mapping = data["header"]["mapping"]["type"]
        ret.typeidx = data["header"]["block"].index("type")
        return ret

def sendToCityIO(data):
    post_address = getFromCfg("output_url")

    import requests
    r = requests.post(post_address, json=data, headers={'Content-Type': 'application/json'})
    print(r)
    if not r.status_code == 200:
        print("could not post result to cityIO")
        print("Error code", r.status_code)
    else:
        print("Successfully posted to cityIO", r.status_code)

if __name__ == "__main__":
    data = getCurrentState()
    if not data:
        print("couldn't load input_url!")
        exit()

    gridDef = Grid.fromCityIO(data)
    gridData = data["grid"]
    gridHash = data["meta"]["hashes"]["grid"]

    typejs = {}
    with open("typedefs.json") as file:
        typejs = json.load(file)

    numWhiteCells = 0
    numGreyCells = 0
    numUnknownCells = 0
        
    for cell in gridData:
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

    sendToCityIO(data)