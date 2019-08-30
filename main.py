import json
import urllib.request 

def getFromCfg(key : str) -> str:
    #import os#os.path.dirname(os.path.realpath(__file__)+
    with open("config.json") as file:
        js = json.load(file)
        return js[key]

def getCurrentState():
    with urllib.request.urlopen(getFromCfg("input_url")) as url:
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
        return ret



if __name__ == "__main__":
    data = getCurrentState()
    if not data:
        print("couldn't load input_url!")
        exit()

    gridDef = Grid.fromCityIO(data)
    gridData = data["grid"]

    js = {}
    with open("typedefs.json") as file:
        js = json.load(file)

    numWhiteCells = 0
    numGreyCells = 0
    numUnknownCells = 0
        
    for cell in gridData:
        curtype = cell[0]
        if curtype in js["white"]:
            numWhiteCells += 1
        elif curtype in js["grey"]:
            numGreyCells += 1
        else:
            numUnknownCells += 1

    expectedRain = 0.750 # in m³/m²a

    print("m³ white water to be handled: ",   numWhiteCells * gridDef.cellSize * gridDef.cellSize * expectedRain)
    print("m³ grey water to be handled: ",    numGreyCells * gridDef.cellSize * gridDef.cellSize * expectedRain)
    print("m³ unknown water to be handled: ", numUnknownCells * gridDef.cellSize * gridDef.cellSize * expectedRain)

