#!/usr/bin/env python
from pathlib import Path
from typing import Union

from geojson import FeatureCollection, Feature

import geojson
import geopandas
import subprocess

dataDirectory = Path("rowery_wawa")
shapefilePath = dataDirectory / "rowery.shp"
geojsonDirectory = Path("geojson")


def headHash() -> str:
    return (
        subprocess.check_output(["git", "rev-parse", "--short", "HEAD"])
        .decode("utf-8")
        .strip()
    )


def checkGitHashes():
    return list(
        map(
            lambda line: line.split(" ")[0][:7],
            subprocess.check_output(["git", "log", "--pretty=oneline", shapefilePath])
            .decode("utf-8")
            .split("\n"),
        )
    )[:-1]


def gitCheckout(gitHash: str):
    subprocess.check_output(["git", "checkout", gitHash])


def generateCurrentGeojson(outputPath: Path):
    data = geopandas.read_file(
        shapefilePath,
        crs='PROJCS["ETRS_1989_Poland_CS2000_Zone_7",GEOGCS["GCS_ETRS_1989",DATUM["D_ETRS_1989",SPHEROID["GRS_1980",6378137.0,298.257222101]],PRIMEM["Greenwich",0.0],UNIT["Degree",0.0174532925199433]],PROJECTION["Transverse_Mercator"],PARAMETER["False_Easting",7500000.0],PARAMETER["False_Northing",0.0],PARAMETER["Central_Meridian",21.0],PARAMETER["Scale_Factor",0.999923],PARAMETER["Latitude_Of_Origin",0.0],UNIT["Meter",1.0]]',
    )
    data.to_crs("epsg:4326").to_file(outputPath, driver="GeoJSON", crs="epsg:4326")


def generateGeojsonGit(gitHash: str) -> Path:
    outputPath = geojsonDirectory / f"{gitHash}.geojson"
    if outputPath.exists():
        print(f"File already exists: {outputPath}. Skipping")
        return outputPath
    needsReturn = False
    if checkGitHashes()[0] != gitHash:
        gitCheckout(gitHash)
        needsReturn = True
    generateCurrentGeojson(outputPath)
    if needsReturn:
        gitCheckout("-")
    return outputPath


def propsComparedString(feature: Feature) -> str:
    keysCompared = [
        "DATA",
        "TYP_TRASY",
        "JEDNOKIERU",
        "DZIELNICA",
        "BUDOWA",
        "TYP_NAW",
    ]
    return ",".join([f'{key}={feature["properties"][key]}' for key in keysCompared])


def geometryCompare(
    geometry: list[Union[float, list[float]]],
    oldGeometry: list[Union[float, list[float]]],
) -> bool:
    eps = 0.01

    def simplify(data: list[Union[float, list[float]]]) -> list[int]:
        result = []
        for x in data:
            for y in x:
                if type(y) == float:
                    result.append(int(y / eps))
                else:
                    for z in y:
                        result.append(int(z / eps))
        return result

    return simplify(geometry) == simplify(oldGeometry)


def generateDiff(lastPath: Path, previousPath: Path):
    with lastPath.open() as f:
        new = geojson.load(f)
    with previousPath.open() as f:
        old = geojson.load(f)

    updatedFeatures = []

    oldFeaturesByProps: dict[str, list[Feature]] = dict()
    for oldFeature in old.features:
        propsString = propsComparedString(oldFeature)
        if propsString not in oldFeaturesByProps:
            oldFeaturesByProps[propsString] = []
        oldFeaturesByProps[propsString].append(oldFeature)

    for feature in new.features:
        updated = True
        propsString = propsComparedString(feature)
        if propsString not in oldFeaturesByProps:
            oldFeaturesByProps[propsString] = []
        for oldFeature in oldFeaturesByProps[propsString]:
            if geometryCompare(
                feature["geometry"]["coordinates"],
                oldFeature["geometry"]["coordinates"],
            ):
                updated = False
                break
        if updated:
            updatedFeatures.append(feature)
    with Path("latestDiff.geojson").open("w") as f:
        geojson.dump(FeatureCollection(updatedFeatures), f)


def main():
    gitHashes = checkGitHashes()
    lastHash = gitHashes[0]
    previousHash = gitHashes[1]
    lastPath = generateGeojsonGit(lastHash)
    previousPath = generateGeojsonGit(previousHash)
    generateCurrentGeojson(geojsonDirectory / "latest.geojson")
    generateDiff(lastPath, previousPath)


if __name__ == "__main__":
    main()
