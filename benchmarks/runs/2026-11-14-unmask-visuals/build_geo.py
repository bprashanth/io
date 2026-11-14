"""Rebuild the bundled simplified DataMeet boundaries. Network needed only to rebuild."""
import hashlib
import json
from pathlib import Path
import tempfile
import urllib.request
import shapefile
from shapely.geometry import shape, mapping
from topojson import Topology

ROOT = Path(__file__).resolve().parents[1] / '2026-11-06-oss-desktop-independent/cowork/lib/geo'
COMMIT = 'b3fbbde595310b397a55d718e0958ce249a4fa1f'
ROOT.mkdir(parents=True, exist_ok=True)
manifest = {'source': 'https://github.com/datameet/maps', 'commit': COMMIT, 'files': {}}
with tempfile.TemporaryDirectory() as temp:
    for name, folder, stem in [('states','States','Admin2'),('districts','Districts/Census_2011','2011_Dist')]:
        for ext in ['shp','shx','dbf','prj']:
            url=f'https://raw.githubusercontent.com/datameet/maps/{COMMIT}/{folder}/{stem}.{ext}'
            urllib.request.urlretrieve(url, Path(temp)/f'{stem}.{ext}')
        reader=shapefile.Reader(str(Path(temp)/stem))
        print(name, [f[0] for f in reader.fields[1:]])
        features=[]
        for record in reader.iterShapeRecords():
            attrs=record.record.as_dict()
            # Print only public boundary metadata to identify upstream field names.
            if not features: print(attrs)
            geom=shape(record.shape.__geo_interface__).simplify(.018, preserve_topology=True)
            district=attrs.get('DISTRICT') or attrs.get('District') or attrs.get('DIST_NAME')
            state=attrs.get('ST_NM') or attrs.get('STATE') or attrs.get('State_Name')
            features.append({'type':'Feature','properties':{'name':district if name=='districts' else state,'state':state},'geometry':mapping(geom)})
        topo=Topology({'type':'FeatureCollection','features':features}, prequantize=100000, object_name=name).to_dict()
        payload=json.dumps(topo,separators=(',',':')).encode()
        assert len(payload)<2_000_000
        (ROOT/f'india-{name}.topo.json').write_bytes(payload)
        manifest['files'][name]={'bytes':len(payload),'features':len(features),'sha256':hashlib.sha256(payload).hexdigest()}
(ROOT/'source.json').write_text(json.dumps(manifest,indent=2)+'\n')
