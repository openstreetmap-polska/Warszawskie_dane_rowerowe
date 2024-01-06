#!/usr/bin/env python

from math import radians, sin, atan2, sqrt, cos, ceil
from dataclasses import dataclass
import httpx
from tqdm import tqdm

import geojson
from pathlib import Path
import geopandas

from funcy import log_durations

dataDirectory = Path("rowery_wawa")
shapefilePath = dataDirectory / "rowery.shp"
outputDirectory = Path("osm_diffs")
OVERPASS_URL = "https://overpass-api.de/api/interpreter"  # "http://localhost:12345/api/interpreter"
LINE_STEP_METRES = 1
POINT_DISTANCE_METRES = 10
MISSING_COUNT_THRESHOLD = 20


log_duration = log_durations(lambda msg: print("⌛ " + msg))


@log_duration
def generateGeojson():
    data = geopandas.read_file(
        shapefilePath,
        crs='PROJCS["ETRS_1989_Poland_CS2000_Zone_7",GEOGCS["GCS_ETRS_1989",DATUM["D_ETRS_1989",SPHEROID["GRS_1980",6378137.0,298.257222101]],PRIMEM["Greenwich",0.0],UNIT["Degree",0.0174532925199433]],PROJECTION["Transverse_Mercator"],PARAMETER["False_Easting",7500000.0],PARAMETER["False_Northing",0.0],PARAMETER["Central_Meridian",21.0],PARAMETER["Scale_Factor",0.999923],PARAMETER["Latitude_Of_Origin",0.0],UNIT["Meter",1.0]]',
    )
    return geojson.loads(data.to_crs("epsg:4326").to_json())


@log_duration
def getOSMDataFromOverpass():
    query = f"""
    [out:json][timeout:25];
    area[name="Warszawa"][admin_level=8]->.searchArea;
    (
        way["cycleway"~"(lane|track)"](area.searchArea);
        way[bicycle=designated](area.searchArea);
        way["oneway:bicycle"=no](area.searchArea);
        way[highway=cycleway](area.searchArea);
        way[~"cycleway:(both|left|right)"~"lane"](area.searchArea);
    );
    convert item ::=::,::geom=geom(),_osm_type=type();
    out geom;
    """
    response = httpx.post(OVERPASS_URL, data=dict(data=query))
    response.raise_for_status()
    return geojson.loads(response.text)["elements"]


@dataclass
class GeoPoint:
    lat: float
    lon: float

    @staticmethod
    def fromTuple(tup):
        return GeoPoint(tup[1], tup[0])


warsawCenter = GeoPoint(lat=52.2319581, lon=21.0067249)


def geoDistance(point: GeoPoint, other: GeoPoint) -> int:
    R = 6373.0
    lon1, lat1, lon2, lat2 = map(radians, [point.lon, point.lat, other.lon, other.lat])

    deltaLon = lon2 - lon1
    deltaLat = lat2 - lat1
    a = (sin(deltaLat / 2)) ** 2 + cos(lat1) * cos(lat2) * (sin(deltaLon / 2)) ** 2
    c = 2 * atan2(sqrt(a), sqrt(1 - a))
    return int(R * c * 1000)


DictPoint = dict[int, list[GeoPoint]]


def pointsToDictPoint(points: list[GeoPoint]) -> DictPoint:
    result = dict()
    for point in points:
        distance = geoDistance(point, warsawCenter)
        if distance not in result:
            result[distance] = []
        result[distance].append(point)
    return result


def processLineIntoDictPoint(line: list[tuple[float, float]]) -> DictPoint:
    points = []
    for pointA, pointB in zip(line[:-1], line[1:]):
        latDelta = pointB[1] - pointA[1]
        lonDelta = pointB[0] - pointA[0]
        distance = geoDistance(GeoPoint.fromTuple(pointA), GeoPoint.fromTuple(pointB))
        stepsCount = int(ceil(distance / LINE_STEP_METRES))
        if stepsCount == 0:
            continue
        stepLat = latDelta / stepsCount
        stepLon = lonDelta / stepsCount
        for i in range(stepsCount):
            points.append(
                GeoPoint(lon=pointA[0] + stepLon * i, lat=pointA[1] + stepLat * i)
            )
    result = pointsToDictPoint(points)
    return result


def mergeDictPoints(dictPoints: list[DictPoint]) -> DictPoint:
    result = dict()
    for dictPoint in dictPoints:
        for distance, pointsInDistance in dictPoint.items():
            if distance not in result:
                result[distance] = []
            result[distance].extend(pointsInDistance)
    return result


@log_duration
def processOSMDataIntoDictPoint(osmData) -> DictPoint:
    dictPoints = []
    for element in osmData:
        if element["geometry"]["type"] != "LineString":
            print(f'Unsupported geometry type {element["geometry"]["type"]}')
            continue
        coords = element["geometry"]["coordinates"]
        dictPoints.append(processLineIntoDictPoint(coords))
    return mergeDictPoints(dictPoints)


@log_duration
def outputMissingFeaturesGeojson(name: str, missingFeatures):
    with (outputDirectory / (name + ".geojson")).open("w") as f:
        geojson.dump(geojson.FeatureCollection(missingFeatures), indent=2, fp=f)


@log_duration
def processDistrict(district, districtFeatures, osmDictPoint):
    missingFeatures = []
    for feature in tqdm(districtFeatures):
        if feature["geometry"]["type"] == "LineString":
            warsawDataPoints = processLineIntoDictPoint(
                feature["geometry"]["coordinates"]
            )
        elif feature["geometry"]["type"] == "MultiLineString":
            warsawDataPoints = mergeDictPoints(
                [
                    processLineIntoDictPoint(line)
                    for line in feature["geometry"]["coordinates"]
                ]
            )
        else:
            print(f'Unsupported geometry type {feature["geometry"]["type"]}')
            continue
        missingCount = 0
        count = 0
        for distanceFromCenter, pointsInDist in warsawDataPoints.items():
            count += len(pointsInDist)
            for point in pointsInDist:
                found = False
                for dist in range(
                    distanceFromCenter - POINT_DISTANCE_METRES,
                    distanceFromCenter + POINT_DISTANCE_METRES + 1,
                ):
                    for osmPoint in osmDictPoint.get(dist, []):
                        if geoDistance(point, osmPoint) < POINT_DISTANCE_METRES:
                            found = True
                            break
                if not found:
                    missingCount += 1
        if missingCount >= MISSING_COUNT_THRESHOLD:
            # print(count, missingCount, feature["properties"]["LOKALIZ"])
            missingFeatures.append(feature)
    outputMissingFeaturesGeojson(district, missingFeatures)


def generateOSMDiff(warsawData, osmDictPoint):
    warsawDistricts = [
        "Bemowo",
        "Białołęka",
        "Bielany",
        "Mokotów",
        "Ochota",
        "Praga-Północ",
        "Praga-Południe",
        "Rembertów",
        "Śródmieście",
        "Targówek",
        "Ursus",
        "Ursynów",
        "Wawer",
        "Wesoła",
        "Wilanów",
        "Włochy",
        "Wola",
        "Żoliborz",
    ]
    allDistricts = {
        feature["properties"]["DZIELNICA"] for feature in warsawData["features"]
    }
    print(f"Skipping: {allDistricts - set(warsawDistricts)}")
    warsawFeatures = [
        feature
        for feature in warsawData["features"]
        if feature["properties"]["BUDOWA"] != "tak"
        and feature["properties"]["TYP_TRASY"] != "inny"
        and feature["properties"]["DZIELNICA"] in warsawDistricts
    ]
    for district in tqdm(warsawDistricts):
        districtFeatures = [
            feature
            for feature in warsawFeatures
            if feature["properties"]["DZIELNICA"] == district
        ]
        processDistrict(district, districtFeatures, osmDictPoint)


def main():
    outputDirectory.mkdir(exist_ok=True)
    warsawData = generateGeojson()
    osmData = getOSMDataFromOverpass()
    osmDictPoint = processOSMDataIntoDictPoint(osmData)
    generateOSMDiff(warsawData, osmDictPoint)


if __name__ == "__main__":
    main()
