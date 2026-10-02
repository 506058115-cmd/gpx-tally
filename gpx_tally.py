#!/usr/bin/env python3
"""Summarize GPX track structure without exposing location data."""

import argparse
import math
from pathlib import Path
import stat
import sys
from xml.etree import ElementTree


GPX = "{http://www.topografix.com/GPX/1/1}"
MAX_BYTES = 128 * 1024 * 1024
EARTH_RADIUS_KM = 6371.0088


class GpxError(ValueError):
    pass


def distance_km(first, second):
    lat1, lon1 = map(math.radians, first)
    lat2, lon2 = map(math.radians, second)
    dlat, dlon = lat2 - lat1, lon2 - lon1
    arc = math.sin(dlat / 2) ** 2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon / 2) ** 2
    return 2 * EARTH_RADIUS_KM * math.asin(min(1, math.sqrt(arc)))


def inspect(path):
    source = Path(path)
    file_stat = source.stat()
    if not stat.S_ISREG(file_stat.st_mode):
        raise GpxError("input must be a regular file")
    if file_stat.st_size > MAX_BYTES:
        raise GpxError("input exceeds the 128 MiB limit")

    tracks = segments = points = 0
    total_distance = 0.0
    lowest = highest = None
    previous = None
    stack = []
    root_seen = False

    with source.open("rb") as stream:
        for event, element in ElementTree.iterparse(stream, events=("start", "end")):
            if event == "start":
                stack.append(element)
                parent = stack[-2] if len(stack) > 1 else None
                if not root_seen:
                    root_seen = True
                    if element.tag != GPX + "gpx" or element.get("version") != "1.1":
                        raise GpxError("expected a GPX 1.1 document")
                elif element.tag == GPX + "trk" and parent is not None and parent.tag == GPX + "gpx":
                    tracks += 1
                elif element.tag == GPX + "trkseg" and parent is not None and parent.tag == GPX + "trk":
                    segments += 1
                    previous = None
                continue

            parent = stack[-2] if len(stack) > 1 else None
            if (
                element.tag == GPX + "trkpt"
                and len(stack) >= 4
                and stack[-2].tag == GPX + "trkseg"
                and stack[-3].tag == GPX + "trk"
                and stack[-4].tag == GPX + "gpx"
            ):
                try:
                    point = (float(element.attrib["lat"]), float(element.attrib["lon"]))
                except (KeyError, ValueError) as error:
                    raise GpxError("track point has missing or invalid coordinates") from error
                if not all(math.isfinite(value) for value in point):
                    raise GpxError("track point coordinates must be finite numbers")
                if not -90 <= point[0] <= 90 or not -180 <= point[1] <= 180:
                    raise GpxError("track point coordinates are out of range")
                if previous is not None:
                    total_distance += distance_km(previous, point)
                previous = point
                points += 1

                elevation = element.find(GPX + "ele")
                if elevation is not None:
                    try:
                        value = float(elevation.text)
                    except (TypeError, ValueError) as error:
                        raise GpxError("track point has invalid elevation") from error
                    if not math.isfinite(value):
                        raise GpxError("track point elevation must be finite")
                    lowest = value if lowest is None else min(lowest, value)
                    highest = value if highest is None else max(highest, value)

            if parent is not None and parent.tag == GPX + "trkpt":
                if element.tag != GPX + "ele":
                    element.clear()
            else:
                if parent is not None:
                    parent.remove(element)
                element.clear()
            stack.pop()

    if not root_seen:
        raise GpxError("empty XML document")
    return tracks, segments, points, total_distance, lowest, highest


def main():
    parser = argparse.ArgumentParser(
        description="Count GPX 1.1 tracks and estimate distance without printing coordinates."
    )
    parser.add_argument("input", help="GPX 1.1 file")
    args = parser.parse_args()

    try:
        tracks, segments, points, distance, lowest, highest = inspect(args.input)
    except (ElementTree.ParseError, GpxError) as error:
        print(f"gpx-tally: invalid or unsupported GPX: {error}", file=sys.stderr)
        return 1
    except OSError as error:
        print(f"gpx-tally: {error.strerror or 'unable to read input'}", file=sys.stderr)
        return 2

    print(f"Tracks: {tracks}")
    print(f"Segments: {segments}")
    print(f"Track points: {points}")
    print(f"Estimated path distance: {distance:.3f} km")
    if lowest is None:
        print("Elevation range: unavailable")
    else:
        print(f"Elevation range: {lowest:.1f} to {highest:.1f} m")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
