# India boundaries

India boundaries by the DataMeet Community Maps Project.
Source: https://github.com/datameet/maps
Pinned revision: `b3fbbde595310b397a55d718e0958ce249a4fa1f`.

- `india-districts.topo.json`: 641 features from `Districts/Census_2011/2011_Dist`.
- `india-states.topo.json`: 36 features from `States/Admin2`.
- Objects are named `districts` and `states`. Properties are `name` and `state`.

The upstream district dataset is licensed under **Creative Commons Attribution 2.5 India**:
https://creativecommons.org/licenses/by/2.5/in/
Published licence and original source details:
https://github.com/datameet/maps/blob/b3fbbde595310b397a55d718e0958ce249a4fa1f/Districts/README.md
The state dataset follows the repository data licence: DataMeet India community under **CC BY 4.0**:
https://github.com/datameet/maps/blob/b3fbbde595310b397a55d718e0958ce249a4fa1f/README.md
https://creativecommons.org/licenses/by/4.0/
Credit both the project and these terms when redistributing these derived files.

These are historic geographic reference layers for visualisation. District coverage follows the upstream Census 2011 dataset and includes some older extents. State boundaries are the upstream snapshot. They do not represent a verified current administrative register. Do not infer that an unmatched modern district has zero records.

Changes: simplified each polygon with Shapely's topology-preserving algorithm at 0.018 degrees. Converted to shared-arc TopoJSON with quantisation 100000. Retained only district and state labels. Files are under 0.5 MB each. `source.json` records sizes, feature counts and SHA-256 checksums. Rebuild with `benchmarks/runs/2026-11-14-unmask-visuals/build_geo.py` using pyshp, shapely and topojson. Runtime needs only the Python standard library.
