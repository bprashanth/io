"""Local map validation, boundary loading and conservative district matching."""
import copy
import difflib
from functools import lru_cache
import json
import math
from pathlib import Path
import re
import unicodedata

GEO = Path(__file__).resolve().parent / 'geo'
FILES = {'india-states.topo.json': 'states', 'india-districts.topo.json': 'districts'}


class MapError(ValueError):
    pass


@lru_cache(maxsize=2)
def boundary(name):
    if name not in FILES:
        raise MapError('Use /geo/india-states.topo.json or /geo/india-districts.topo.json.')
    try:
        obj = json.loads((GEO / name).read_text())
        if obj['type'] != 'Topology' or not obj['arcs'] or not obj['objects'][FILES[name]]['geometries']:
            raise ValueError()
        return obj
    except (OSError, ValueError, KeyError, TypeError):
        raise MapError('The local map boundaries are missing or invalid. Ask to restore the bundled boundary file.') from None


def _features(name):
    topo = boundary(name)
    transform = topo.get('transform')
    arcs = []
    for arc in topo['arcs']:
        coords = []
        x = y = 0
        for a, b in arc:
            if transform:
                x, y = x + a, y + b
                coords.append([x * transform['scale'][0] + transform['translate'][0],
                               y * transform['scale'][1] + transform['translate'][1]])
            else:
                coords.append([a, b])
        arcs.append(coords)
    def ring(indices):
        result = []
        for index in indices:
            arc = arcs[index] if index >= 0 else list(reversed(arcs[~index]))
            result.extend(arc if not result else arc[1:])
        return result
    out = []
    for geo in topo['objects'][FILES[name]]['geometries']:
        if geo['type'] == 'Polygon':
            coordinates = [ring(r) for r in geo['arcs']]
        elif geo['type'] == 'MultiPolygon':
            coordinates = [[ring(r) for r in polygon] for polygon in geo['arcs']]
        else:
            raise MapError('The local boundary has an unsupported shape.')
        out.append({'type': 'Feature', 'properties': geo.get('properties', {}),
                    'geometry': {'type': geo['type'], 'coordinates': coordinates}})
    return out


@lru_cache(maxsize=2)
def features(name):
    try:
        return _features(name)
    except MapError:
        raise
    except (KeyError, IndexError, TypeError, ValueError):
        raise MapError('The local boundary geometry is invalid. Ask to restore the bundled boundary file.') from None


ALIASES = {'poona': 'pune', 'bengaluru': 'bangalore', 'bengaluruurban': 'bangalore', 'bangaloreurban': 'bangalore',
           'bengalururural': 'bangalorerural', 'gurugram': 'gurgaon', 'prayagraj': 'allahabad',
           'ayodhya': 'faizabad', 'mysuru': 'mysore', 'mangaluru': 'dakshinkannada',
           'orissa': 'odisha', 'uttaranchal': 'uttarakhand', 'pondicherry': 'puducherry',
           'ahmadnagar': 'ahmednagar', 'ahmadabad': 'ahmedabad', 'hugli': 'hooghly',
           'bombay': 'mumbai', 'calcutta': 'kolkata'}


def normalise(name):
    name = unicodedata.normalize('NFKD', str(name)).casefold().strip()
    name = re.sub(r'\bdistrict\s*$', '', name).strip()
    name = re.sub(r'[^a-z0-9]', '', name)
    return ALIASES.get(name, name)


def match_district(name, state=None):
    choices = features('india-districts.topo.json')
    if state:
        choices = [f for f in choices if normalise(f['properties'].get('state', '')) == normalise(state)]
    needle = normalise(name)
    exact = [f for f in choices if normalise(f['properties']['name']) == needle]
    if len(exact) == 1:
        return exact[0]
    if exact or not needle:
        return None
    ranked = sorted([(difflib.SequenceMatcher(None, needle, normalise(f['properties']['name'])).ratio(), i, f)
                     for i, f in enumerate(choices)], reverse=True)
    if ranked and ranked[0][0] >= .86 and (len(ranked) == 1 or ranked[0][0] - ranked[1][0] >= .04):
        return ranked[0][2]
    return None


def _walk(node):
    if isinstance(node, dict):
        yield node
        for value in node.values():
            yield from _walk(value)
    elif isinstance(node, list):
        for value in node:
            yield from _walk(value)


def prepare(spec, rows):
    """Expand the small idli_map contract into normal Vega-Lite layers with local geometry."""
    spec = copy.deepcopy(spec)
    meta = spec.get('usermeta') or {}
    cfg = meta.get('idli_map') if isinstance(meta, dict) else None
    has_geo = any(n.get('mark') == 'geoshape' or isinstance(n.get('mark'), dict)
                  and n['mark'].get('type') == 'geoshape' for n in _walk(spec))
    if not cfg and not has_geo:
        return spec
    for node in _walk(spec):
        if 'url' in node and (not isinstance(node['url'], str) or node['url'] not in {'/geo/' + n for n in FILES}):
            raise MapError('Maps must use the bundled /geo/ India boundaries. External boundary URLs are not supported.')
    if not isinstance(cfg, dict) or cfg.get('type') not in ('gps', 'district'):
        raise MapError('Map specs need usermeta.idli_map with type gps or district. Use the newsroom-charts map templates.')
    for node in _walk(spec):
        if 'url' in node:
            name = node['url'][5:]
            fmt = node.get('format', {})
            if fmt.get('type') != 'topojson' or fmt.get('feature') != FILES[name]:
                raise MapError('Use TopoJSON format with the states or districts object matching the boundary file.')
    states = features('india-states.topo.json')
    background = {'data': {'values': states}, 'mark': {'type': 'geoshape', 'fill': '#aaa', 'fillOpacity': .12,
                   'stroke': '#888', 'strokeWidth': .5, 'clip': True}}
    if cfg['type'] == 'gps':
        lat, lon = cfg.get('lat'), cfg.get('lon')
        coordinates = []
        for row in rows:
            try:
                a, b = float(row[lat]), float(row[lon])
                if not math.isfinite(a + b) or not (-90 <= a <= 90 and -180 <= b <= 180):
                    raise ValueError()
                coordinates.append([b, a])
            except (KeyError, ValueError, TypeError):
                raise MapError('GPS maps need numeric latitude and longitude in every row. Remove blanks and invalid coordinates first.') from None
        if not coordinates:
            raise MapError('The GPS CSV has no points to show.')
        # Add a small extent so a single point also produces a usable map.
        xs, ys = zip(*coordinates)
        pad = max(.05, (max(xs)-min(xs))*.08, (max(ys)-min(ys))*.08)
        extent = {'type':'MultiPoint', 'coordinates': [[min(xs)-pad,min(ys)-pad],[max(xs)+pad,max(ys)+pad]]}
        encoding = spec.get('encoding', {})
        layer = {'mark': {'type': 'point', 'filled': True, 'size': 75, 'color': '#41788b', 'clip': True},
                 'encoding': {**encoding, 'latitude': {'field': lat, 'type': 'quantitative'},
                              'longitude': {'field': lon, 'type': 'quantitative'}}}
        spec['layer'] = [background, layer]
        label = cfg.get('label')
        if label:
            if any(label not in row for row in rows):
                raise MapError('The GPS label field is missing from the CSV.')
            spec['layer'].append({'mark': {'type': 'text', 'dx': 7, 'dy': -10, 'align': 'left', 'clip': True},
                                  'encoding': {**layer['encoding'], 'text': {'field': label, 'type': 'nominal'}}})
    else:
        field, value, state = cfg.get('field'), cfg.get('value'), cfg.get('state')
        if not field or not value or any(field not in r or value not in r for r in rows):
            raise MapError('District maps need field and value columns from the CSV. A state column can resolve duplicate names.')
        mapped, unmatched, seen = [], [], set()
        for row in rows:
            feature = match_district(row[field], row.get(state) if state else None)
            if feature is None:
                unmatched.append(str(row[field]))
                continue
            key = (feature['properties']['name'], feature['properties']['state'])
            if key in seen:
                raise MapError('The CSV has more than one row for a district. Combine its rows before drawing the map.')
            seen.add(key)
            try:
                if not math.isfinite(float(row[value])):
                    raise ValueError()
            except (ValueError, TypeError):
                raise MapError('District map values must be numbers. Remove blanks before drawing the map.') from None
            f = copy.deepcopy(feature)
            f['properties'] = {**row, '__district': key[0], '__state': key[1]}
            # A local planar centroid of the largest ring is sufficient for direct labels.
            polygons = f['geometry']['coordinates'] if f['geometry']['type'] == 'MultiPolygon' else [f['geometry']['coordinates']]
            ring = max((p[0] for p in polygons), key=lambda r: abs(sum(a[0]*b[1]-b[0]*a[1] for a,b in zip(r,r[1:]))))
            area = sum(a[0]*b[1]-b[0]*a[1] for a,b in zip(ring,ring[1:]))
            if area:
                cx = sum((a[0]+b[0])*(a[0]*b[1]-b[0]*a[1]) for a,b in zip(ring,ring[1:]))/(3*area)
                cy = sum((a[1]+b[1])*(a[0]*b[1]-b[0]*a[1]) for a,b in zip(ring,ring[1:]))/(3*area)
                f['properties'].update(__lon=cx, __lat=cy, __label=key[0]+': '+str(row[value]))
            mapped.append(f)
        if not mapped:
            raise MapError('No district names matched the bundled boundaries. Check spelling or add a state column. Unmatched: ' + ', '.join(unmatched[:12]))
        extent = {'type': 'FeatureCollection', 'features': mapped}
        spec['layer'] = [background, {'data': {'values': mapped},
            'mark': {'type': 'geoshape', 'stroke': '#888', 'strokeWidth': .6, 'clip': True},
            'encoding': {'color': {'field': 'properties.'+value, 'type': 'quantitative',
                                   'scale': {'range': ['#dbe5e5', '#41788b']}, 'legend': None},
                         'tooltip': [{'field':'properties.'+field, 'type':'nominal'},
                                     {'field':'properties.'+value, 'type':'quantitative'}]}}]
        if len(mapped) <= 12:
            spec['layer'].append({'data': {'values': mapped}, 'mark': {'type': 'text', 'fontSize': 12, 'color': '#1b3036', 'stroke': '#fff', 'strokeWidth': .3, 'clip': True},
                                  'encoding': {'longitude': {'field': 'properties.__lon', 'type': 'quantitative'},
                                               'latitude': {'field': 'properties.__lat', 'type': 'quantitative'},
                                               'text': {'field': 'properties.__label', 'type': 'nominal'}}})
        spec['description'] = (spec.get('description', '') + '\nUnmatched districts: ' +
                               (', '.join(dict.fromkeys(unmatched)) if unmatched else 'none') + '.').strip()
    for key in ('mark', 'encoding', 'data', 'transform', 'projection'):
        spec.pop(key, None)
    spec['projection'] = {'type': 'mercator', 'fit': extent}
    return spec
