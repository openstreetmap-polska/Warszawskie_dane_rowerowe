#!/usr/bin/env python

import h3
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
MISSING_COUNT_THRESHOLD = 10
MISSING_COUNT_PERCENTAGE_THRESHOLD = 0.2
H3_RESOLUTION = 11
NEIGHBOURHOOD_SIZE = 1


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


def processLineIntoH3Set(line: list[tuple[float, float]], result: set[str]) -> set[str]:
    for pointA, pointB in zip(line[:-1], line[1:]):
        start = h3.geo_to_h3(pointA[1], pointA[0], H3_RESOLUTION)
        end = h3.geo_to_h3(pointB[1], pointB[0], H3_RESOLUTION)
        for point in h3.h3_line(start, end):
            result.update(h3.k_ring(point, NEIGHBOURHOOD_SIZE))
    return result


@log_duration
def processOSMDataIntoH3Set(osmData) -> set[str]:
    result = set()
    for element in osmData:
        if element["geometry"]["type"] != "LineString":
            print(f'Unsupported geometry type {element["geometry"]["type"]}')
            continue
        coords = element["geometry"]["coordinates"]
        result = processLineIntoH3Set(coords, result)
    return result


def outputMissingFeaturesGeojson(name: str, missingFeatures):
    nameSlugified = slugify(name, lowercase=False)
    outputFile = outputDirectory / (nameSlugified + ".geojson")
    if len(missingFeatures) == 0:
        if outputFile.exists():
            outputFile.unlink()
        return
    with outputFile.open("w") as f:
        geojson.dump(
            geojson.FeatureCollection(missingFeatures), fp=f, separators=(",", ":")
        )


def processDistrict(district, districtFeatures, osmH3Set: set[str]):
    missingFeatures = []
    for feature in districtFeatures:
        featureH3Set = set()
        if feature["geometry"]["type"] == "LineString":
            featureH3Set = processLineIntoH3Set(feature["geometry"]["coordinates"], featureH3Set)
        elif feature["geometry"]["type"] == "MultiLineString":
            for line in feature["geometry"]["coordinates"]:
                featureH3Set = processLineIntoH3Set(line, featureH3Set)
        else:
            print(f'Unsupported geometry type {feature["geometry"]["type"]}')
            continue
        count = len(featureH3Set)
        missingCount = count - len(osmH3Set & featureH3Set)
        if (
            missingCount >= MISSING_COUNT_THRESHOLD
            or missingCount / count > MISSING_COUNT_PERCENTAGE_THRESHOLD
        ):
            # print(count, missingCount, feature["properties"]["LOKALIZ"])
            missingFeatures.append(feature)
    outputMissingFeaturesGeojson(district, missingFeatures)


@log_duration
def generateOSMDiff(warsawData, osmH3Set: set[str]):
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
        "Radzymin",
        "Raszyn",
        "Stare Babice",
        "Sulejówek",
        "Wiązowna",
        "Wieliszew",
        "Wołomin",
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
        processDistrict(areaName, districtFeatures, osmH3Set)


def main():
    outputDirectory.mkdir(exist_ok=True)
    warsawData = openDataGeojson()
    osmData = getOSMDataFromOverpass()
    h3Set = processOSMDataIntoH3Set(osmData)
    generateOSMDiff(warsawData, h3Set)


if __name__ == "__main__":
    main()
