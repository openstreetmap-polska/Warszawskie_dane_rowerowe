#!/usr/bin/env python

from math import radians, sin, atan2, sqrt, cos, ceil
from dataclasses import dataclass
import httpx
from tqdm import tqdm

import geojson
from pathlib import Path

from funcy import log_durations
from slugify import slugify

dataDirectory = Path("rowery_wawa")
shapefilePath = dataDirectory / "rowery.shp"
outputDirectory = Path("osm_diffs")
OVERPASS_URL = "https://overpass-api.de/api/interpreter"  # "http://localhost:12345/api/interpreter"
LINE_STEP_METRES = 1
POINT_DISTANCE_METRES = 10
MISSING_COUNT_THRESHOLD = 20
MISSING_COUNT_PERCENTAGE_THRESHOLD = 0.2


log_duration = log_durations(lambda msg: print("⌛ " + msg))


def openDataGeojson():
    with Path("geojson/latest.geojson").open() as f:
        return geojson.load(f)


@log_duration
def getOSMDataFromOverpass():
    bbox = "(52,20.5,52.5,21.5)"
    query = f"""
    [out:json][timeout:25];
    (
        way["cycleway"~"(lane|track)"]{bbox};
        way[bicycle=designated]{bbox};
        way["oneway:bicycle"=no]{bbox};
        way[highway=cycleway]{bbox};
        way[~"cycleway:(both|left|right)"~"lane"]{bbox};
    );
    convert item ::=::,::geom=geom(),_osm_type=type();
    out geom;
    """
    response = httpx.post(OVERPASS_URL, data=dict(data=query), timeout=30.0)
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
    nameSlugified = slugify(name, lowercase=False)
    outputFile = outputDirectory / (nameSlugified + ".geojson")
    if len(missingFeatures) == 0 and outputFile.exists():
        outputFile.unlink()
        return
    with outputFile.open("w") as f:
        geojson.dump(
            geojson.FeatureCollection(missingFeatures), fp=f, separators=(",", ":")
        )


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
        if (
            missingCount >= MISSING_COUNT_THRESHOLD
            or missingCount / count > MISSING_COUNT_PERCENTAGE_THRESHOLD
        ):
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
    supportedTowns = [
        "Góra Kalwaria",
        "Izabelin",
        "Jabłonna",
        "Józefów",
        "Kobyłka",
        "Konstancin-Jeziorna",
        "Legionowo",
        "Lesznowola",
        "Łomianki",
        "Marki",
        "Michałowice",
        "Nieporęt",
        "Nowy Dwór Mazowieck",
        "Otwock",
        "Ożarów Mazowiecki",
        "Piaseczno",
        "Piastów",
        "Pruszków",
        "Raszyn",
        "Stare Babice",
        "Sulejówek",
        "Wiązowna",
        "Wieliszew",
        "Ząbki",
        "Zielonka",
    ]
    areasAnalyzed = warsawDistricts + supportedTowns
    allAreas = {
        feature["properties"]["DZIELNICA"] for feature in warsawData["features"]
    }
    print(f"Skipping: {allAreas - set(areasAnalyzed)}")
    analyzedFeatures = [
        feature
        for feature in warsawData["features"]
        if feature["properties"]["BUDOWA"] != "tak"
        and feature["properties"]["TYP_TRASY"] != "inny"
        and feature["properties"]["DZIELNICA"] in areasAnalyzed
    ]
    for areaName in tqdm(areasAnalyzed):
        districtFeatures = [
            feature
            for feature in analyzedFeatures
            if feature["properties"]["DZIELNICA"] == areaName
        ]
        processDistrict(areaName, districtFeatures, osmDictPoint)


def main():
    outputDirectory.mkdir(exist_ok=True)
    warsawData = openDataGeojson()
    osmData = getOSMDataFromOverpass()
    osmDictPoint = processOSMDataIntoDictPoint(osmData)
    generateOSMDiff(warsawData, osmDictPoint)


if __name__ == "__main__":
    main()
