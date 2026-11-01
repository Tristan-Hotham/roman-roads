"""Step 2. Travel time from Rome over the Itiner-e network.
Model (stated on the page, in the paper and the blog):
  time on a section (days) = length km / (speed km per day x passability)
  speeds from English Wikipedia 'Roman roads' (middle of each range): on foot 22.5, horse-drawn cart 45, courier 80 km a day;
  passability is Itiner-e's own field: 1 on gentle sections, falling with average slope (it matches Tobler's hiking
  function, exp(-3.5 tan slope), for average slopes above about 3.4 degrees);
  each short sea crossing (Channel, Messina, Otranto, Gibraltar) counts as one day; the Euripus bridge counts as road;
  off the mapped network, the last stretch to a point is counted at half the road speed, up to 50 km.
Dijkstra from the node nearest the Forum in Rome. Also: lowest and highest speeds of each range, a network without the
'Hypothetical' sections, a network with no sea crossings, and flat ground (passability ignored).
Writes WORK/travel.pkl, data/travel_from_rome.csv, data/network.json (graph for the page) and the isochrone lookup
grid data/grid_edge.png + data/grid_dist.png (Web Mercator).
Run: python3 code/02_travel.py
"""
import os, sys, pickle
import numpy as np, pandas as pd
import scipy.sparse as sp
from scipy.sparse.csgraph import dijkstra
from scipy.spatial import cKDTree
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import *

N = pickle.load(open(f"{WORK}/net.pkl", "rb"))
S, nodes, X = N["S"], N["nodes"], N["X"]
k = len(nodes); m = len(S)
DEG = nodes.deg.values


def snap(lon, lat):
    d = haversine(lon, lat, nodes.lon.values, nodes.lat.values)
    d = np.where(nodes.net.values, d, np.inf)
    near = np.where(d <= 3)[0]
    i = int(near[np.lexsort((d[near], -DEG[near]))[0]]) if len(near) else int(np.argmin(d))
    return i, float(d[i])


ROME_N, d0 = snap(*ROME); assert d0 < 1 and nodes.name[ROME_N] == "Roma", (nodes.name[ROME_N], d0)
CITY_N = {}
for key, lat_name, en, xy in CITIES:
    i, d = snap(*xy); assert d < 3, (key, d, nodes.name[i])
    CITY_N[key] = i
print({k_: (nodes.name[i]) for k_, i in CITY_N.items()})


def graph(kmd, use_pass=True, crossings=True, drop_hyp=False, cross_days=CROSSING_DAYS):
    sel = (S.u != S.v).values.copy()
    if drop_hyp:
        sel &= (S.cert != "Hypothetical").values
    s = S[sel]
    w = s.km.values / (kmd * (s.pas.values if use_pass else 1.0))
    U, V, W, E = list(s.u), list(s.v), list(w), list(s.index)
    if crossings:
        for j, x in enumerate(X):
            U.append(x["u"]); V.append(x["v"]); W.append(x["km"] / kmd if x["bridge"] else cross_days); E.append(m + j)
    else:
        for j, x in enumerate(X):
            if x["bridge"]:
                U.append(x["u"]); V.append(x["v"]); W.append(x["km"] / kmd); E.append(m + j)
    U, V, W, E = map(np.array, (U, V, W, E))
    # keep the quickest of parallel edges (csgraph sums duplicates otherwise)
    key = np.minimum(U, V) * k + np.maximum(U, V)
    o = np.lexsort((W, key)); first = np.r_[True, key[o][1:] != key[o][:-1]]; o = o[first]
    A = sp.coo_matrix((W[o], (U[o], V[o])), shape=(k, k)).tocsr()
    return A, (U[o], V[o], W[o], E[o])


def run(kmd, src=None, **kw):
    A, (U, V, W, E) = graph(kmd, **kw)
    t, pred = dijkstra(A, directed=False, indices=src if src is not None else ROME_N, return_predecessors=True)
    return t, pred, (U, V, W, E)


def path_sections(pred, dst, edges):
    U, V, W, E = edges
    look = {}
    for u, v, e in zip(U, V, E):
        look[(u, v)] = e; look[(v, u)] = e
    out = []; n = dst
    while pred[n] >= 0:
        out.append(look[(pred[n], n)]); n = pred[n]
    return out[::-1]


T = {}; P = {}; EDG = {}
for md in MODE_ORDER:
    T[md], P[md], EDG[md] = run(MODES[md]["kmd"])
reach = np.isfinite(T["foot"])
print("nodes reached", reach.sum(), "of", k)
res = {"rome_node": ROME_N, "city": {}, "modes": MODES}
for key, lat_name, en, xy in CITIES:
    n = CITY_N[key]; secs = path_sections(P["foot"], n, EDG["foot"])
    road_km = float(sum(S.km[e] for e in secs if e < m)); sea = [X[e - m]["key"] for e in secs if e >= m]
    sea_km = float(sum(X[e - m]["km"] for e in secs if e >= m))
    straight = float(haversine(*ROME, *xy))
    r = {"key": key, "latin": lat_name, "name": en, "node": n, "node_name": nodes.name[n],
         "days": {md: float(T[md][n]) for md in MODE_ORDER}, "road_km": road_km, "sea": sea, "sea_km": sea_km,
         "straight_km": straight, "detour": road_km / straight if straight else None, "sections": len(secs),
         "route_cert_km": {c: float(sum(S.km[e] for e in secs if e < m and S.cert[e] == c)) for c in ("Certain", "Conjectured", "Hypothetical")},
         "route": [int(e) for e in secs if e < m]}
    for md in ("foot", "cart"):
        lo = run(MODES[md]["hi"])[0][n]; hi = run(MODES[md]["lo"])[0][n]
        r[f"{md}_range"] = [float(lo), float(hi)]
    r["foot_nohyp"] = float(run(MODES["foot"]["kmd"], drop_hyp=True)[0][n])
    r["foot_nosea"] = float(run(MODES["foot"]["kmd"], crossings=False)[0][n])
    r["foot_flat"] = float(run(MODES["foot"]["kmd"], use_pass=False)[0][n])
    res["city"][key] = r
    print(f"{en:28s} foot {r['days']['foot']:6.1f} cart {r['days']['cart']:5.1f} courier {r['days']['courier']:5.1f}  road {road_km:6.0f} km sea {sea} "
          f"range {r['foot_range'][0]:.0f}-{r['foot_range'][1]:.0f} nohyp {r['foot_nohyp']:.1f} nosea {r['foot_nosea']:.1f} flat {r['foot_flat']:.1f}")

# road length by days on foot from Rome (section midpoint time)
mid = {}
for md in MODE_ORDER:
    w = S.km.values / (MODES[md]["kmd"] * S.pas.values)
    tu, tv = T[md][S.u.values], T[md][S.v.values]
    # time to the middle of a section: half way along from the nearer end
    mid[md] = np.minimum(tu + w / 2, tv + w / 2)
S_reach = np.isfinite(mid["foot"])
res["km_reachable"] = float(S.km[S_reach].sum()); res["km_unreachable"] = float(S.km[~S_reach].sum())
bands = []
for a, b in zip(DAYBREAKS, DAYBREAKS[1:] + [9999]):
    s = S_reach & (mid["foot"] >= a) & (mid["foot"] < b)
    bands.append({"a": a, "b": b if b < 9999 else None, "km": float(S.km[s].sum())})
res["foot_bands"] = bands
for md in MODE_ORDER:
    for dd in (7, 30):
        res.setdefault("km_within", {}).setdefault(md, {})[str(dd)] = float(S.km[S_reach & (mid[md] <= dd)].sum())
res["max_foot"] = float(np.nanmax(np.where(reach, T["foot"], np.nan)))
far = int(np.nanargmax(np.where(reach, T["foot"], np.nan)))
res["farthest"] = {"node": far, "name": nodes.name[far], "lon": float(nodes.lon[far]), "lat": float(nodes.lat[far]),
                   "days": {md: float(T[md][far]) for md in MODE_ORDER}}
print("farthest", res["farthest"])
res["crossings"] = [{k_: x[k_] for k_ in ("key", "label", "a", "b", "km", "bridge", "names")} for x in X]
res["unjoined"] = [c for c in N["comps"] if not c["joined"]]

# ---------- per-node table ----------
tab = nodes[["name", "lon", "lat"]].copy(); tab.insert(0, "node", np.arange(k))
for md in MODE_ORDER:
    tab[f"days_{md}"] = np.where(np.isfinite(T[md]), np.round(T[md], 2), np.nan)
tab.round({"lon": 5, "lat": 5}).to_csv(f"{DATA}/travel_from_rome.csv", index=False)
S_mid = pd.DataFrame({"id": S.id, **{f"mid_{md}": mid[md] for md in MODE_ORDER}})

# ---------- graph for the page ----------
net = {"nodes": [[round(float(x), 4), round(float(y), 4)] for x, y in zip(nodes.lon, nodes.lat)],
       "names": list(nodes.name), "edges": [[int(u), int(v), round(float(km), 3), round(float(p), 3)] for u, v, km, p in zip(S.u, S.v, S.km, S.pas)],
       "crossings": [[x["u"], x["v"], round(x["km"], 1), 1 if x["bridge"] else 0, x["label"], x["a"], x["b"]] for x in X],
       "rome": ROME_N, "cities": [[key, lat_name, en, CITY_N[key]] for key, lat_name, en, xy in CITIES],
       "modes": [[md, MODES[md]["label"], MODES[md]["kmd"]] for md in MODE_ORDER],
       "cross_days": CROSSING_DAYS, "off_factor": OFFROAD_FACTOR, "off_max": OFFROAD_MAX_KM}

# ---------- isochrone lookup grid (Web Mercator) ----------
LON0, LON1, LAT0, LAT1 = -12.0, 47.0, 21.5, 58.5
NX = 1000
R_E = 6378137.0
merc = lambda lat: R_E * np.log(np.tan(np.pi / 4 + np.radians(lat) / 2))
X0, X1 = np.radians(LON0) * R_E, np.radians(LON1) * R_E; Y0, Y1 = merc(LAT0), merc(LAT1)
NY = int(round(NX * (Y1 - Y0) / (X1 - X0)))
xs = X0 + (np.arange(NX) + .5) * (X1 - X0) / NX; ys = Y1 - (np.arange(NY) + .5) * (Y1 - Y0) / NY
glon = np.degrees(xs / R_E); glat = np.degrees(2 * np.arctan(np.exp(ys / R_E)) - np.pi / 2)
# samples every 1 km along every section, with the fraction of the way along
se, sf, sx, sy = [], [], [], []
for i, gm in enumerate(S.geom):
    L = gm.length
    n = max(2, int(np.ceil(S.km[i] / 1.0)) + 1)
    for f in np.linspace(0, 1, n):
        p = gm.interpolate(f * L); se.append(i); sf.append(f); sx.append(p.x); sy.append(p.y)
se, sf, sx, sy = map(np.array, (se, sf, sx, sy))
P3 = lambda lon, lat: np.column_stack([np.cos(np.radians(lat)) * np.cos(np.radians(lon)), np.cos(np.radians(lat)) * np.sin(np.radians(lon)), np.sin(np.radians(lat))])
tree = cKDTree(P3(sx, sy))
GL, GA = np.meshgrid(glon, glat)
chord, idx = tree.query(P3(GL.ravel(), GA.ravel()))
dkm = 2 * 6371.0088 * np.arcsin(np.clip(chord / 2, 0, 1))
# land mask (Natural Earth 10m countries)
import rasterio.features, rasterio.transform
from shapely.geometry import shape
from shapely.ops import transform as stransform
land = [shape(f["geometry"]) for f in jload(f"{GEO}/ne_10m_admin_0_countries.geojson")["features"]]
tm = rasterio.transform.from_bounds(X0, Y0, X1, Y1, NX, NY)
to_m = lambda x, y, z=None: (np.radians(np.asarray(x)) * R_E, merc(np.clip(np.asarray(y), -85, 85)))
from shapely.geometry import box
clipb = box(LON0 - 1, LAT0 - 1, LON1 + 1, LAT1 + 1)
shapes = [stransform(to_m, g_.intersection(clipb)) for g_ in land if g_.intersects(clipb)]
mask = rasterio.features.rasterize(((s_, 1) for s_ in shapes if not s_.is_empty), out_shape=(NY, NX), transform=tm, fill=0, all_touched=True).astype(bool)
ok = mask.ravel() & (dkm <= OFFROAD_MAX_KM)
code = (se[idx].astype(np.int64) << 8) | np.round(sf[idx] * 255).astype(np.int64)
code = np.where(ok, code, 0xFFFFFF)
from PIL import Image
rgb = np.stack([(code >> 16) & 255, (code >> 8) & 255, code & 255], -1).reshape(NY, NX, 3).astype(np.uint8)
Image.fromarray(rgb, "RGB").save(f"{DATA}/grid_edge.png", optimize=True)
dq = np.where(ok, np.clip(np.round(dkm * 4), 0, 200), 255).reshape(NY, NX).astype(np.uint8)
Image.fromarray(dq, "L").save(f"{DATA}/grid_dist.png", optimize=True)
net["grid"] = {"lon0": LON0, "lon1": LON1, "lat0": LAT0, "lat1": LAT1, "nx": NX, "ny": NY, "dist_scale": 4}
jsave(net, f"{DATA}/network.json")
print("grid", NX, NY, "edge png", os.path.getsize(f"{DATA}/grid_edge.png") // 1024, "KB; dist png", os.path.getsize(f"{DATA}/grid_dist.png") // 1024, "KB; network.json",
      os.path.getsize(f"{DATA}/network.json") // 1024, "KB")


def grid_days(md, t=None):
    """Days from the source to every grid cell, as the page computes it (NaN where no time is shown)."""
    t = T[md] if t is None else t
    kmd = MODES[md]["kmd"]
    e = se[idx]; f = sf[idx]
    f = np.round(f * 255) / 255
    w = S.km.values[e] / (kmd * S.pas.values[e])
    tt = np.minimum(t[S.u.values[e]] + f * w, t[S.v.values[e]] + (1 - f) * w)
    dd = np.round(dkm * 4) / 4
    out = tt + dd / (kmd * OFFROAD_FACTOR)
    return np.where(ok, out, np.nan).reshape(NY, NX)


G = {md: grid_days(md) for md in MODE_ORDER}
pickle.dump({"T": T, "P": P, "res": res, "mid": S_mid, "grid": G, "glon": glon, "glat": glat, "CITY_N": CITY_N,
             "samples": (se, sf, sx, sy), "EDG": EDG}, open(f"{WORK}/travel.pkl", "wb"))
jsave(res, f"{WORK}/travel.json", indent=1)
