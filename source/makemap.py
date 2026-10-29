# encoding: utf-8


'''
author: Taehong Kim
email: peppy0510@hotmail.com
'''


import json
import os
import sys


EPSILON = 0.35
MIN_SPAN = 1.6
SCALE = 20


def get_output_path():
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(root, 'assets', 'map', 'land.json')


def get_distance(point, start, end):
    (x, y), (x0, y0), (x1, y1) = point, start, end
    dx, dy = x1 - x0, y1 - y0
    if dx == 0 and dy == 0:
        return abs(x - x0) + abs(y - y0)
    return abs(dy * x - dx * y + x1 * y0 - y1 * x0) / (dx * dx + dy * dy) ** 0.5


def simplify(points, epsilon):
    if len(points) < 3:
        return points

    index, worst = 0, 0.0
    for position in range(1, len(points) - 1):
        distance = get_distance(points[position], points[0], points[-1])
        if distance > worst:
            index, worst = position, distance

    if worst <= epsilon:
        return [points[0], points[-1]]
    return simplify(points[:index + 1], epsilon)[:-1] + simplify(points[index:], epsilon)


def get_rings(feature):
    geometry = feature['geometry']
    if geometry['type'] == 'Polygon':
        return geometry['coordinates']
    return [ring for polygon in geometry['coordinates'] for ring in polygon]


def is_large_enough(ring):
    longitudes = [point[0] for point in ring]
    latitudes = [point[1] for point in ring]
    return (max(longitudes) - min(longitudes) >= MIN_SPAN or
            max(latitudes) - min(latitudes) >= MIN_SPAN)


def main():
    if len(sys.argv) < 2:
        raise SystemExit('usage: makemap.py <ne_110m_land.geojson>')

    with open(sys.argv[1], encoding='utf-8') as file:
        data = json.load(file)

    rings = []
    source_points = 0
    for feature in data['features']:
        for ring in get_rings(feature):
            source_points += len(ring)
            if not is_large_enough(ring):
                continue
            reduced = simplify([tuple(point[:2]) for point in ring], EPSILON)
            if len(reduced) < 4:
                continue
            flat = []
            for longitude, latitude in reduced:
                flat.append(int(round(longitude * SCALE)))
                flat.append(int(round(latitude * SCALE)))
            rings.append(flat)

    path = get_output_path()
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, 'w', encoding='utf-8') as file:
        json.dump({'scale': SCALE, 'rings': rings}, file, separators=(',', ':'))

    kept = sum(len(ring) for ring in rings) // 2
    print(f'rings {len(rings)}, points {source_points} -> {kept}, '
          f'{os.path.getsize(path)} bytes')


if __name__ == '__main__':
    main()
