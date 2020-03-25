from pyproj import Transformer
import json
import math

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
        ret.tablerotation = data["spatial"]["rotation"]

        proj = Transformer.from_crs(getFromCfg("input_crs"), getFromCfg("compute_crs"))
        ret.origin = proj.transform(data["spatial"]["latitude"], data["spatial"]["longitude"])

        return ret

    # def updateGrid(self,endpoint=-1, token=None):
    #     self.grid = getCurrentState("grid", endpoint, token)

    def Local2Geo(self, x, y):
        bearing = self.tablerotation

        x *= self.cellSize
        y *= -self.cellSize # flip y axis (for northern hemisphere)

        # rotate and scale
        new_x = x * math.cos(math.radians(bearing)) - y * math.sin(math.radians(bearing))
        new_y = x * math.sin(math.radians(bearing)) + y * math.cos(math.radians(bearing))

        # convert to geo coords
        return (new_x + self.origin[0], new_y + self.origin[1])

def getFromCfg(key: str) -> str:
    # import os#os.path.dirname(os.path.realpath(__file__)+
    with open("config.json") as file:
        js = json.load(file)
        return js[key]

def PolyToGeoJSON(points, id, properties):
    ret = "{\"type\": \"Feature\",\"id\": \"" 
    ret += str(id) 
    ret += "\",\"geometry\": {\"type\": \"Polygon\",\"coordinates\": [["

    # lat,lon order
    for p in points:
        ret+="["+str(p[1])+","+str(p[0])+"],"
    ret+="["+str(points[0][1])+","+str(points[0][0])+"]" # closed ring, last one without trailing comma

    ret += "]]},"
    ret += "\"properties\": {"
    for key in properties: # properties to string
        ret += "\""+key+"\""
        ret += ":"
        if type(properties[key]) is str:
            ret += "\""
        ret += str(properties[key])
        if type(properties[key]) is str:
            ret += "\""
        ret += ","
    if len(properties) > 0:
        ret=ret[:-1] # delete trailing comma after properties
    ret += "}}"
    return ret

def makeCellsJSON(filledGrid : list, cityioTable : Table, skipkeys = [], skipvalues = [float("inf"),float("-inf")]):
    # filledGrid = list(filledGrids.values())[0]
    resultjson = ""

    proj = Transformer.from_crs(getFromCfg("compute_crs"), getFromCfg("output_crs"))

    for idx in range(len(filledGrid)):
        x = idx % cityioTable.ncols
        y = idx // cityioTable.ncols

        properties = {}
        for prop in filledGrid[idx]:
            if prop in skipkeys:
                print("Warning: Grid cell", str(idx), "with property", prop, "is skipped!")
                continue # non-initialised cell, skip
            value = filledGrid[idx][prop]
            if value in skipvalues:
                print("Warning: Grid cell", str(idx), "with value", value, "is skipped!")
                continue # inf can't be parsed as geojson, skip this type
            properties[prop] = value
        if len(properties) == 0:
            continue # no properties, so don't create a feature

        pointlist = []

        fromPoint = cityioTable.Local2Geo(x,y) # upper left
        fromPoint = proj.transform(fromPoint[0],fromPoint[1])
        pointlist.append(fromPoint)

        toPoint = cityioTable.Local2Geo(x+1,y) # upper right
        toPoint = proj.transform(toPoint[0],toPoint[1])
        pointlist.append(toPoint)
        toPoint = cityioTable.Local2Geo(x+1,y+1) # bottom right
        toPoint = proj.transform(toPoint[0],toPoint[1])
        pointlist.append(toPoint)
        toPoint = cityioTable.Local2Geo(x,y+1) # bottom left
        toPoint = proj.transform(toPoint[0],toPoint[1])
        pointlist.append(toPoint)

        resultjson += PolyToGeoJSON(pointlist, idx, properties) # append feature, closes loop
        resultjson +=","

    resultjson = resultjson[:-1] # trim trailing comma
    return resultjson

def writeFile(filepath, data):
    f= open(filepath,"w+")
    f.write(data)

def createGeoJSON(filledgrid, cityiotable):
    jsonstring = "{\"type\": \"FeatureCollection\",\"features\": [" # geojson front matter

    # find all grid cells with type as in typejs
    jsonstring += makeCellsJSON(filledgrid, cityiotable)

    jsonstring += "]}" # geojson end matter

    # writeFile("test.json",jsonstring)
    
    return jsonstring