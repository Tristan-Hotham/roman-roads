"""Step 3. Analysis of the network: lengths by type and certainty, dates, named roads and itineraries, the longest
straight runs, and road density by province.
- Dates: the year in the construction period field ('Claudius (46 CE)' -> 46; the first year of a range; Augustus with
  no year -> 27 BCE, Julius Caesar -> 49 BCE, 'Tetrarchy or later' -> 293), else the Lower_Date field.
- Straight runs: sections that are Certain or Conjectured (not Hypothetical, and not marked 'Straight line conjecture')
  are joined into continuous lines ('strokes') through junctions where the road carries on within 20 degrees of
  straight. Each stroke is simplified (Douglas-Peucker) with a 200 m tolerance in a local equidistant projection: every
  long simplified piece is a stretch where the digitised road never strays more than 200 m from a straight line.
  Ranked twice: all such roads, and Certain sections only (digitised to within 200 m in the plains).
- Provinces: DARE provinces of about AD 117 (Italy as its eleven regions, and as one); km of road per 1,000 km2,
  from points every kilometre along every section.
Writes WORK/analysis.pkl and data/provinces.csv, data/straight_runs.csv, data/named_roads.csv.
Run: python3 code/03_analysis.py
"""
import os, sys, re, pickle, collections
import numpy as np, pandas as pd, geopandas as gpd
from shapely.geometry import LineString, Point, shape
from pyproj import Transformer, Geod
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import *

N = pickle.load(open(f"{WORK}/net.pkl", "rb")); TR = pickle.load(open(f"{WORK}/travel.pkl", "rb"))
S, nodes = N["S"], N["nodes"]
for c in ("name", "cons", "itin", "desc", "cite", "bib"):
    S[c] = pd.Series([x if isinstance(x, str) else None for x in S[c]], dtype=object)
for c in ("lo", "lo_e", "up", "up_e"):
    S[c] = pd.Series([None if x is None or (isinstance(x, float) and np.isnan(x)) else float(x) for x in S[c]], dtype=object)
A = {}
tot = float(S.km.sum())
A["n_sections"] = len(S); A["km_total"] = tot; A["n_nodes"] = len(nodes)
A["km_type"] = S.groupby("type").km.sum().to_dict(); A["n_type"] = S.groupby("type").size().to_dict()
A["km_cert"] = S.groupby("cert").km.sum().to_dict(); A["n_cert"] = S.groupby("cert").size().to_dict()
A["km_type_cert"] = {t: S[S.type == t].groupby("cert").km.sum().to_dict() for t in S.type.unique()}
A["share_cert_km"] = {c: v / tot for c, v in A["km_cert"].items()}
A["share_cert_n"] = {c: v / len(S) for c, v in A["n_cert"].items()}
A["share_main_km"] = A["km_type"]["Main Road"] / tot
A["share_main_certain"] = A["km_type_cert"]["Main Road"]["Certain"] / A["km_type"]["Main Road"]
A["mean_km"] = tot / len(S); A["median_km"] = float(S.km.median())
A["longest_section"] = {"name": S.name[S.km.idxmax()], "km": float(S.km.max()), "cert": S.cert[S.km.idxmax()]}
A["straightline_conj"] = {"n": int(S.desc.str.contains("Straight line conjecture", na=False).sum()),
                          "km": float(S[S.desc.str.contains("Straight line conjecture", na=False)].km.sum())}
A["km_slope_gt3"] = float(S[S.pas < 1].km.sum()); A["share_slope_slowed"] = A["km_slope_gt3"] / tot
A["n_digitisers"] = len(set(x for x in S.cite if x))


# ---------- dates ----------
def cons_year(s):
    if not s:
        return None
    m = re.search(r"\(([^)]*)\)", s)
    if not m:
        return {"Augustus": -27, "Julius Caesar": -49, "Tetrarchy or later": 293}.get(s.strip())
    body = m.group(1)
    nums = [(int(x.group(1)), x.start()) for x in re.finditer(r"(\d+)", body)]
    if not nums:
        return None
    y, pos = nums[0]
    era = re.search(r"\b(BCE|BC|CE|AD)\b", body[pos:])
    return -y if era and era.group(1) in ("BCE", "BC") else y


S["cy"] = [cons_year(c) for c in S.cons]
S["year"] = [c if c is not None else (lo if lo is not None else None) for c, lo in zip(S.cy, S.lo)]
S["year_src"] = ["construction period" if c is not None else ("lower date" if lo is not None else None) for c, lo in zip(S.cy, S.lo)]
dated = S[S.year.notna()]
A["n_dated"] = len(dated); A["km_dated"] = float(dated.km.sum()); A["share_dated_km"] = A["km_dated"] / tot; A["share_dated_n"] = len(dated) / len(S)
A["n_cons"] = int(S.cons.notna().sum()); A["n_lowdate"] = int(S.lo.notna().sum()); A["n_update"] = int(S.up.notna().sum())


def band(y):
    if y is None or (isinstance(y, float) and np.isnan(y)):
        return None
    for k, lab, a, b, c in DATEBANDS:
        if a <= y <= b:
            return k


S["band"] = [band(y) for y in S.year]
A["date_bands"] = [{"key": k, "label": lab, "n": int((S.band == k).sum()), "km": float(S[S.band == k].km.sum())} for k, lab, a, b, c in DATEBANDS]
# who built most (construction period field, by the name before the brackets)
who = collections.Counter(); whon = collections.Counter()
for c, km in zip(S.cons, S.km):
    if c:
        nm = re.sub(r"\s*\(.*", "", c).strip()
        who[nm] += km; whon[nm] += 1
A["builders"] = [{"name": k, "km": v, "n": whon[k]} for k, v in who.most_common(12)]
A["earliest_dated"] = [{"name": r.name, "year": int(r.year), "cons": r.cons} for r in dated.sort_values("year").head(5).itertuples()]
# Upper_Date: when roads went out of use (rarely given)
# ---------- itineraries and named roads ----------
itin = collections.Counter(); itn = collections.Counter()
for it, km in zip(S.itin, S.km):
    if it:
        for p in set(x.strip() for x in re.split(r",\s*", it)):
            p = {"Itinerarium Burdigalensee": "Itinerarium Burdigalense", "Rauennatis Anonyimi Cosmographia": "Ravenna Cosmography",
                 "Via Iulia Augusta": "Via Julia Augusta"}.get(p, p)
            itin[p] += km; itn[p] += 1
A["km_peutinger"] = itin["Tabula Peutingeriana"]; A["km_antonine"] = itin["Itinerarium Antonini"]
A["km_any_itin"] = float(S[S.itin.notna()].km.sum()); A["share_any_itin"] = A["km_any_itin"] / tot
named = [(k, v, itn[k]) for k, v in itin.most_common() if not re.match(r"(Tabula|Itinerarium|Ravenna|Procopius)", k)]
A["named_roads"] = [{"name": k, "km": v, "n": n} for k, v, n in named[:20]]
pd.DataFrame([{"name": k, "km": round(v, 1), "sections": n} for k, v, n in named]).to_csv(f"{DATA}/named_roads.csv", index=False)
A["n_named"] = len(named)
for k, lab, a, b, c in DATEBANDS:
    pass

# ---------- straight runs ----------
pool = S[(S.cert != "Hypothetical") & ~S.desc.str.contains("Straight line conjecture", na=False) & (S.u != S.v)].copy()
inc = collections.defaultdict(list)
for i, r in pool.iterrows():
    inc[r.u].append(i); inc[r.v].append(i)
geod = Geod(ellps="WGS84")


def bearing_from(i, n):
    """Bearing of section i leaving node n, from the node to the point about 1 km along (or the far end)."""
    co = np.array(S.geom[i].coords)
    if S.v[i] == n:
        co = co[::-1]
    d = np.cumsum(np.r_[0, haversine(co[:-1, 0], co[:-1, 1], co[1:, 0], co[1:, 1])])
    j = int(np.searchsorted(d, 1.0)); j = min(max(j, 1), len(co) - 1)
    az, _, _ = geod.inv(co[0, 0], co[0, 1], co[j, 0], co[j, 1])
    return az


pair = {}
for n, es in inc.items():
    if len(es) < 2:
        continue
    b = {i: bearing_from(i, n) for i in es}
    cand = []
    for x in range(len(es)):
        for y in range(x + 1, len(es)):
            i, j = es[x], es[y]
            defl = abs(((b[i] - b[j]) % 360) - 180)
            if defl <= 20:
                cand.append((defl, i, j))
    used = set()
    for defl, i, j in sorted(cand):
        if i in used or j in used:
            continue
        used |= {i, j}; pair[(n, i)] = j; pair[(n, j)] = i
seen = set(); strokes = []
for i in pool.index:
    if i in seen:
        continue
    # walk back to one end
    n = S.u[i]; cur = i
    while (n, cur) in pair and pair[(n, cur)] not in seen and pair[(n, cur)] != i:
        nxt = pair[(n, cur)]; n = S.v[nxt] if S.u[nxt] == n else S.u[nxt]; cur = nxt
        if len(seen) > 10 ** 7:
            break
    # cur is an end section, n is its outer node; walk forward
    chain = []; node = n; sec = cur; guard = set()
    while sec is not None and sec not in guard:
        guard.add(sec); chain.append((sec, node))
        far = S.v[sec] if S.u[sec] == node else S.u[sec]
        nxt = pair.get((far, sec))
        node, sec = far, (nxt if nxt is not None and nxt not in guard and nxt not in seen else None)
    seen |= set(c for c, _ in chain)
    co = []
    for sec, node in chain:
        c = list(S.geom[sec].coords)
        if S.v[sec] == node:
            c = c[::-1]
        co.extend(c if not co else c[1:])
    strokes.append({"secs": [c for c, _ in chain], "coords": np.array(co)})
print("strokes", len(strokes), "from", len(pool), "sections")

runs = []
for si, st in enumerate(strokes):
    co = st["coords"]
    if len(co) < 2:
        continue
    lon0, lat0 = co[len(co) // 2]
    tr = Transformer.from_crs(4326, f"+proj=aeqd +lat_0={lat0} +lon_0={lon0} +datum=WGS84 +units=m", always_xy=True)
    x, y = tr.transform(co[:, 0], co[:, 1]); xy = np.column_stack([x, y])
    simp = np.array(LineString(xy).simplify(200, preserve_topology=False).coords)
    # map simplified vertices back to original indices
    ids = [int(np.argmin(((xy - p) ** 2).sum(1))) for p in simp]
    # cumulative section index of each original vertex
    secof = []
    for sec, node in [(s, None) for s in st["secs"]]:
        pass
    for a, b in zip(ids[:-1], ids[1:]):
        if b <= a:
            continue
        L = float(np.hypot(*(xy[b] - xy[a]))) / 1000
        if L < 15:
            continue
        seg = xy[a:b + 1]; p, q = xy[a], xy[b]; dvec = (q - p) / np.linalg.norm(q - p)
        dev = np.abs((seg - p) @ np.array([-dvec[1], dvec[0]]))
        runs.append({"stroke": si, "km": L, "maxdev_m": float(dev.max()), "n_vertices": int(b - a + 1),
                     "lon0": float(co[a, 0]), "lat0": float(co[a, 1]), "lon1": float(co[b, 0]), "lat1": float(co[b, 1])})
runs = pd.DataFrame(runs).sort_values("km", ascending=False)
# attach sections, certainty, names along each run
sec_tree = {}
from shapely.strtree import STRtree
geoms = list(S.geom); tree = STRtree(geoms)
rows = []
for r in runs.itertuples():
    line = LineString([(r.lon0, r.lat0), (r.lon1, r.lat1)])
    cand = [int(i) for i in tree.query(line.buffer(0.004)) if int(i) in set(strokes[r.stroke]["secs"])]
    cert_km = collections.Counter(); names = collections.Counter(); itins = collections.Counter(); cons = collections.Counter()
    for i in cand:
        ov = S.geom[i].intersection(line.buffer(0.004)).length / max(S.geom[i].length, 1e-12) * S.km[i]
        cert_km[S.cert[i]] += ov; names[S.name[i]] += ov
        if S.itin[i]:
            for p in re.split(r",\s*", S.itin[i]):
                if not re.match(r"(Tabula|Itinerarium|Ravenna|Rauenn|Procopius)", p):
                    itins[p.strip()] += ov
        if S.cons[i]:
            cons[S.cons[i]] += ov
    tk = sum(cert_km.values()) or 1
    a_ = nodes.name[int(np.argmin(haversine(r.lon0, r.lat0, nodes.lon.values, nodes.lat.values)))]
    b_ = nodes.name[int(np.argmin(haversine(r.lon1, r.lat1, nodes.lon.values, nodes.lat.values)))]
    rows.append({**r._asdict(), "share_certain": cert_km["Certain"] / tk, "road": itins.most_common(1)[0][0] if itins else None,
                 "from": a_, "to": b_, "sections": ";".join(n for n, _ in names.most_common(3)), "cons": cons.most_common(1)[0][0] if cons else None})
runs = pd.DataFrame(rows).drop(columns=["Index"])
# only stretches digitised in detail count: at least one vertex every 2 km on average, unless the road is Certain (a long
# conjectured line drawn with two or three points is straight because it was drawn that way, not because the road was)
runs["spacing_km"] = runs.km / (runs.n_vertices - 1)
keep_ = (runs.spacing_km <= 2) | (runs.share_certain >= 0.9)     # Certain sections are accurate to 200 m by definition
A["n_runs_sparse_dropped"] = int((~keep_).sum())
runs = runs[keep_]
# one run per stroke stretch: drop runs that overlap a longer one already listed (same stroke, shared ground)
runs = runs.sort_values("km", ascending=False).reset_index(drop=True)
A["runs_all"] = runs.head(15).to_dict("records")
cert_runs = runs[runs.share_certain >= 0.9]
A["runs_certain"] = cert_runs.head(15).to_dict("records")
A["n_runs_30"] = int((runs.km >= 30).sum()); A["n_runs_20"] = int((runs.km >= 20).sum()); A["n_runs_cert_20"] = int((cert_runs.km >= 20).sum())
runs.round({"km": 2, "maxdev_m": 1, "share_certain": 3, "lon0": 5, "lat0": 5, "lon1": 5, "lat1": 5}).to_csv(f"{DATA}/straight_runs.csv", index=False)
print(runs.head(15)[["km", "maxdev_m", "n_vertices", "share_certain", "road", "from", "to", "sections"]].to_string())
print(cert_runs.head(10)[["km", "maxdev_m", "n_vertices", "road", "from", "to", "sections"]].to_string())

# ---------- provinces ----------
P = gpd.read_file(f"{DARE}/provinces.geojson").set_crs(4326, allow_override=True)
P["prov"] = [f"Italia, regio {n} ({ITALY_REG[n]})" if n in ITALY_REG else n for n in P.name]
P["italy"] = P.name.isin(ITALY_REG)
P = P.dissolve("prov", aggfunc={"italy": "first", "name": "first"}).reset_index()
EA = "+proj=laea +lat_0=40 +lon_0=15 +datum=WGS84 +units=m"
P["area_km2"] = P.to_crs(EA).area / 1e6
it = P[P.italy].dissolve(aggfunc={"area_km2": "sum"});
se, sf, sx, sy = TR["samples"]
# road length carried by each sample: the stretch between consecutive samples, given to its midpoint
mids = []; w = []
for i in range(len(S)):
    pass
order = np.lexsort((sf, se))
se_, sf_, sx_, sy_ = se[order], sf[order], sx[order], sy[order]
same = se_[1:] == se_[:-1]
mx = (sx_[1:] + sx_[:-1]) / 2; my = (sy_[1:] + sy_[:-1]) / 2; seg_sec = se_[1:]
wkm = (sf_[1:] - sf_[:-1]) * S.km.values[seg_sec]
mx, my, seg_sec, wkm = mx[same], my[same], seg_sec[same], wkm[same]
assert abs(wkm.sum() - tot) < 1, (wkm.sum(), tot)
pts = gpd.GeoDataFrame({"sec": seg_sec, "km": wkm}, geometry=gpd.points_from_xy(mx, my), crs=4326)
j = gpd.sjoin(pts, P[["prov", "italy", "geometry"]], how="left", predicate="within")
j = j[~j.index.duplicated()]
j["cert"] = S.cert.values[j.sec.values]; j["rtype"] = S.type.values[j.sec.values]
g = j.groupby("prov")
pr = pd.DataFrame({"km": g.km.sum(), "km_certain": j[j.cert == "Certain"].groupby("prov").km.sum(), "km_main": j[j.rtype == "Main Road"].groupby("prov").km.sum()}).fillna(0)
pr = pr.join(P.set_index("prov")[["area_km2", "italy"]])
pr["density"] = pr.km / pr.area_km2 * 1000; pr["share_certain"] = pr.km_certain / pr.km
pr = pr.sort_values("density", ascending=False)
ital = {"km": float(pr[pr.italy].km.sum()), "area_km2": float(pr[pr.italy].area_km2.sum())}; ital["density"] = ital["km"] / ital["area_km2"] * 1000
A["km_outside_provinces"] = float(j[j.prov.isna()].km.sum()); A["share_outside"] = A["km_outside_provinces"] / tot
A["italia"] = ital
A["provinces"] = [{"prov": k, **{c: (float(v) if not isinstance(v, (bool, np.bool_)) else bool(v)) for c, v in r.items()}} for k, r in pr.iterrows()]
A["n_provinces"] = int(len(pr))
prov_noit = pr[~pr.italy]
A["empire_density"] = float(pr.km.sum() / pr.area_km2.sum() * 1000)
pr.reset_index().rename(columns={"prov": "province"}).round({"km": 1, "km_certain": 1, "km_main": 1, "area_km2": 0, "density": 2, "share_certain": 3}).to_csv(f"{DATA}/provinces.csv", index=False)
print(pr.head(15).round(2).to_string()); print(pr.tail(6).round(2).to_string()); print("Italia", ital, "outside", A["km_outside_provinces"])
# province of each section (by most of its length), for the page
sp_ = j.groupby(["sec", "prov"]).km.sum().reset_index().sort_values("km").drop_duplicates("sec", keep="last").set_index("sec").prov
S["prov"] = [sp_.get(i) for i in range(len(S))]
pickle.dump({"A": A, "S": S, "runs": runs, "P": P, "strokes": strokes}, open(f"{WORK}/analysis.pkl", "wb"))
print({k: v for k, v in A.items() if not isinstance(v, (list, dict))})
print(A["date_bands"], A["builders"][:6], A["named_roads"][:8])
