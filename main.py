import json
import requests
import time
import argparse
from typing import Optional


class Table:
    cellSize = 0
    ncols = 0
    nrows = 0

    @staticmethod
    def fromCityIO(data):
        print("data", data)
        ret = Table()
        ret.cellSize = data["spatial"]["cellSize"]
        ret.ncols = data["spatial"]["ncols"]
        ret.nrows = data["spatial"]["nrows"]
        ret.mapping = data["mapping"]["type"]
        ret.typeidx = data["block"].index("type")
        return ret


def getFromCfg(key: str) -> str:
    # import os#os.path.dirname(os.path.realpath(__file__)+
    with open("config.json") as file:
        js = json.load(file)
        return js[key]


def getCurrentState(topic="", endpoint=-1, token=None):
    if endpoint == -1 or endpoint == None:
        get_address = getFromCfg("input_url") + topic
    else:
        get_address = getFromCfg("input_urls")[endpoint] + topic

    try:
        if token is None:
            r = requests.get(get_address, headers={'Content-Type': 'application/json'})
        else:
            r = requests.get(get_address, headers={'Content-Type': 'application/json',
                                                'Authorization': 'Bearer {}'.format(token).rstrip()})
        if not r.status_code == 200:
            print("could not get from cityIO")
            print("Error code", r.status_code)
            return {}

        return r.json()
    except requests.exceptions.RequestException as e:
        print("CityIO error while GETting!" + str(e))
        return {}


def sendToCityIO(data, endpoint=-1, token=None):
    if endpoint == -1 or endpoint == None:
        post_address = getFromCfg("output_url")
    else:
        post_address = getFromCfg("output_urls")[endpoint]

    try:
        if token is None:
            r = requests.post(post_address, json=data, headers={'Content-Type': 'application/json'})
        else:
            r = requests.post(post_address, json=data,
                            headers={'Content-Type': 'application/json',
                                    'Authorization': 'Bearer {}'.format(token).rstrip()})
            print(r)
        if not r.status_code == 200:
            print("could not post result to cityIO", post_address)
            print("Error code", r.status_code)
        else:
            print("Successfully posted to cityIO", post_address, r.status_code)
    
    except requests.exceptions.RequestException as e:
        print("CityIO error while POSTing!" + e)
        return


def run(endpoint=-1, token=None):
    gridDef = Table.fromCityIO(getCurrentState("header", endpoint, token))
    if not gridDef:
        print("couldn't load input_url!")
        exit()

    gridData = getCurrentState("grid", endpoint, token)
    gridHash = getCurrentState("meta/hashes/grid", endpoint, token)

    # dictionary of type(/openspace_type) : [["grey","white"], [0,1]], i.e. first index, wether it creates grey or white water, second index, drainage coefficient
    coefficients = {}
    with open("drainagecoefficients.json") as file:
        coefficients = json.load(file)

    numWhiteCells = 0
    numGreyCells = 0
    numUnknownCells = 0
    numStreetCells = 0
    numBuildingCells = 0
    numOpenCells = 0

    specificVolumes = {}

    for cell in gridData:
        if (cell is None or not "type" in gridDef.mapping[cell[gridDef.typeidx]]): continue
        curtype = gridDef.mapping[cell[gridDef.typeidx]]["type"]


        if curtype == "street":
            # handle promenade
            if gridDef.mapping[cell[gridDef.typeidx]]["str_numLanes"] == 0:
                curtype = "promenade"

        if curtype == "open_space":
            if gridDef.mapping[cell[gridDef.typeidx]]["os_type"] is None:
                numUnknownCells += 1
                print(curtype, "unknown")
                continue
            curtype += "/" + gridDef.mapping[cell[gridDef.typeidx]]["os_type"]

        if not curtype in coefficients:
            numUnknownCells += 1
            print(curtype, "unknown")
            continue

        if curtype in specificVolumes:
            specificVolumes[curtype] += coefficients[curtype][1]
        else:
            specificVolumes[curtype] = coefficients[curtype][1]

        if coefficients[curtype][0] == "white":
            numWhiteCells += coefficients[curtype][1]
        elif coefficients[curtype][0] == "grey":
            numGreyCells += coefficients[curtype][1]

        elif coefficients[curtype][0] == "street":
            numStreetCells += coefficients[curtype][1]
        elif coefficients[curtype][0] == "building":
            numBuildingCells += coefficients[curtype][1]
        elif coefficients[curtype][0] == "open":
            numOpenCells += coefficients[curtype][1]
        else:
            numUnknownCells += 1
            # print(curtype, "unknown")

    expectedRain = getFromCfg("expectedAnnualRain")  # in m³/m²a

    whitewater_m3 = int(numWhiteCells * gridDef.cellSize * gridDef.cellSize * expectedRain)
    graywater_m3 = int(numGreyCells * gridDef.cellSize * gridDef.cellSize * expectedRain)
    unknown_m3 = int(numUnknownCells * gridDef.cellSize * gridDef.cellSize * expectedRain)

    streetwater_m3 = int(numStreetCells * gridDef.cellSize * gridDef.cellSize * expectedRain)
    buildingwater_m3 = int(numBuildingCells * gridDef.cellSize * gridDef.cellSize * expectedRain)
    open_m3 = int(numOpenCells * gridDef.cellSize * gridDef.cellSize * expectedRain)

    for key in specificVolumes:
        specificVolumes[key] = int(specificVolumes[key] * gridDef.cellSize * gridDef.cellSize * expectedRain)

    # print("m³ white water to be handled: ", whitewater_m3)
    # print("m³ grey water to be handled: ", graywater_m3)
    # print("m³ unknown water to be handled: ", unknown_m3)

    data = {"unit": "cubic meters per annum", "white": whitewater_m3, "grey": graywater_m3, "unknown": unknown_m3,
            "street_total": streetwater_m3, "building_total": buildingwater_m3, "open_total": open_m3,
            "grid_hash": gridHash}
    data.update(specificVolumes)
    print(data)

    sendToCityIO(data, endpoint, token)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='calculate storm water amounts from cityIO.')
    parser.add_argument('--endpoint', type=int, default=-1, help="endpoint url to choose from config.ini/input_urls")
    args = parser.parse_args()
    print("endpoint", args.endpoint)

    try:
        with open("token.txt") as f:
            token = f.readline()
        if token == "": token = None  # happens with empty file
    except IOError:
        token = None

    oldHash = ""

    while True:
        gridHash = getCurrentState("meta/hashes/grid", int(args.endpoint), token)
        if gridHash != {} and gridHash != oldHash:
            run(int(args.endpoint), token)
            oldHash = gridHash
        else:
            print("waiting for grid change")
            time.sleep(5)
