# gpx-tally

Count tracks, segments, and points in a GPX 1.1 file, estimate the distance between recorded points, and report an elevation range. Coordinates, timestamps, names, and descriptions are never printed. Input is streamed and limited to 128 MiB.

## Use

Requires Python 3.8+; no packages to install.

```sh
python gpx_tally.py walk.gpx
```

Distance is an approximate straight-line sum between consecutive points in each track segment; separate segments are not joined. Elevation is summarized only for points that include it. This is not a GPX schema validator and does not inspect routes or waypoints. Exit status is 0 for a supported file, 1 for malformed or unsupported GPX, and 2 for unreadable input.

## License

MIT
