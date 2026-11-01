"""Step 4. data/results.json (every number quoted anywhere), the page data (data/roads_site.json, data/provinces.geojson,
data/runs.json) and the clean section table data/roads.csv.
Run: python3 code/04_results.py
"""
import os, sys, re, pickle, html as _html
import numpy as np, pandas as pd
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import *

N = pickle.load(open(f"{WORK}/net.pkl", "rb")); TR = pickle.load(open(f"{WORK}/travel.pkl", "rb")); AN = pickle.load(open(f"{WORK}/analysis.pkl", "rb"))
S, nodes, X = AN["S"], N["nodes"], N["X"]; A = AN["A"]; T = TR["T"]; TV = TR["res"]
R = {"meta": {"itinere_doi": ITINERE_DOI, "itinere_paper_doi": ITINERE_PAPER_DOI, "itinere_version": "static version 2024 (Zenodo record version 1.3)",
              "page": PAGE_URL, "repo": REPO, "year": 2026}}

# ---------- the network ----------
tot = A["km_total"]
R["n_sections"] = A["n_sections"]; R["km_total"] = tot; R["n_nodes"] = A["n_nodes"]
R["km_main"] = A["km_type"]["Main Road"]; R["km_secondary"] = A["km_type"]["Secondary Road"]
R["n_main"] = A["n_type"]["Main Road"]; R["n_secondary"] = A["n_type"]["Secondary Road"]
R["share_main"] = R["km_main"] / tot; R["share_secondary"] = R["km_secondary"] / tot
R["cert"] = {c: {"km": A["km_cert"][c], "n": A["n_cert"][c], "share_km": A["share_cert_km"][c], "share_n": A["share_cert_n"][c]} for c in A["km_cert"]}
R["type_cert"] = A["km_type_cert"]
R["main_certain_share"] = A["share_main_certain"]
R["secondary_certain_share"] = A["km_type_cert"]["Secondary Road"]["Certain"] / R["km_secondary"]
R["secondary_hyp_share"] = A["km_type_cert"]["Secondary Road"]["Hypothetical"] / R["km_secondary"]
R["median_section_km"] = A["median_km"]; R["longest_section"] = A["longest_section"]
R["n_digitisers"] = A["n_digitisers"]
R["earth_circ_times"] = tot / 40075.0
# Wikipedia's estimate, read from the page text so the quote cannot drift
wk = jload(f"{ROMAN}/wiki_Roman_roads.json"); wtxt = re.sub(r"\s+", " ", _html.unescape(re.sub(r"<[^>]+>", "", wk["html"])).replace("\xa0", " "))
m = re.search(r"more than ([\d,]+) kilometres \([\d,]+ miles\) of roads, of which over ([\d,]+) kilometres", wtxt)
R["wiki"] = {"total_km": int(m.group(1).replace(",", "")), "paved_km": int(m.group(2).replace(",", "")), "revid": wk["revid"]}
for q in ("pedestrians traveled 20 to 25 kilometres", "40 to 50 kilometres (25 to 31 mi) per day", "a relay of horses could carry a letter 80 kilometres",
          "hastened 296 kilometres (184 mi) in 24 hours"):
    assert q in wtxt, q
R["wiki"]["tiberius_km"] = 296
R["share_of_wiki"] = tot / R["wiki"]["total_km"]
# passability field against Tobler's function
sl = S.slope.values; pa = S.pas.values; low = pa < 1
dif = np.abs(np.exp(-3.5 * np.tan(np.radians(sl[low]))) - pa[low])
R["pass"] = {"median_absdiff": float(np.median(dif)), "max_absdiff": float(dif.max()), "slope_threshold": float(sl[low].min()),
             "n_below1": int(low.sum()), "km_below1": float(S.km[low].sum()), "share_km_below1": float(S.km[low].sum() / tot),
             "min": float(pa.min()), "slope_max": float(sl.max())}
R["pass"]["median_absdiff_r"] = f"{R['pass']['median_absdiff']:.3f}"
assert R["pass"]["median_absdiff"] < 0.005 and 3.3 < R["pass"]["slope_threshold"] < 3.5
R["straightline_conj"] = A["straightline_conj"]

# ---------- dates, builders, itineraries ----------
R["dated"] = {"n": A["n_dated"], "km": A["km_dated"], "share_km": A["share_dated_km"], "share_n": A["share_dated_n"],
              "n_cons": A["n_cons"], "n_lowdate": A["n_lowdate"], "n_update": A["n_update"], "share_undated_km": 1 - A["share_dated_km"]}
R["date_bands"] = A["date_bands"]
R["builders"] = A["builders"]; R["named_roads"] = A["named_roads"]; R["n_named"] = A["n_named"]
R["itin"] = {"km_peutinger": A["km_peutinger"], "km_antonine": A["km_antonine"], "km_any": A["km_any_itin"], "share_any": A["share_any_itin"]}

# ---------- straight runs ----------
def nice(n):
    return re.sub(r"^road junction near ", "near ", n or "")


def runrec(r):
    return {"km": float(r["km"]), "maxdev_m": float(r["maxdev_m"]), "n_vertices": int(r["n_vertices"]), "share_certain": float(r["share_certain"]),
            "road": r["road"] if isinstance(r["road"], str) else None, "from": nice(r["from"]), "to": nice(r["to"]),
            "sections": r["sections"], "lon0": r["lon0"], "lat0": r["lat0"], "lon1": r["lon1"], "lat1": r["lat1"]}


runs = AN["runs"]
R["runs"] = [runrec(r) for r in runs.head(12).to_dict("records")]
R["runs_certain"] = [runrec(r) for r in runs[runs.share_certain >= 0.9].head(8).to_dict("records")]
R["n_runs_30"] = A["n_runs_30"]; R["n_runs_20"] = A["n_runs_20"]; R["n_runs_cert_20"] = A["n_runs_cert_20"]
R["n_runs_sparse_dropped"] = A["n_runs_sparse_dropped"]
# hand labels for the top runs (checked against their end points below)
RUNLAB = [("Viromandis", "Samarobriva", "Between Saint-Quentin and Amiens"), ("Vicetia", "Iulia Concordia", "Via Postumia, between Vicenza and Concordia"),
          ("Tarracinae", "Velitrae", "Via Appia, across the Pontine plain to Terracina"), ("Coriovallum", "Colonia Claudia Ara Agrippinensium", "Via Belgica, between Heerlen and Cologne"),
          ("Ad Silarum", "Bononia", "Via Aemilia, east of Bologna")]
for r, (a, b, lab) in zip(R["runs"], RUNLAB):
    assert a in r["from"] + r["to"] and b in r["from"] + r["to"], (r["from"], r["to"], a, b)
    r["label"] = lab
for r in R["runs"][len(RUNLAB):]:
    r["label"] = (r["road"] + ", " if r["road"] else "") + f"{r['from']} to {r['to']}"
for r in R["runs_certain"]:
    r["label"] = next((x["label"] for x in R["runs"] if abs(x["km"] - r["km"]) < 1e-6), (r["road"] + ", " if r["road"] else "") + f"{r['from']} to {r['to']}")

# ---------- provinces ----------
PR = A["provinces"]
R["provinces"] = [{"name": p["prov"], "km": p["km"], "area_km2": p["area_km2"], "density": p["density"], "share_certain": p["share_certain"],
                   "km_main": p["km_main"], "italy": p["italy"]} for p in PR]
R["n_provinces"] = A["n_provinces"]; R["italia"] = A["italia"]; R["empire_density"] = A["empire_density"]
R["km_outside_provinces"] = A["km_outside_provinces"]; R["share_outside"] = A["share_outside"]
noit = [p for p in R["provinces"] if not p["italy"]]
R["top_prov"] = R["provinces"][:10]; R["top_prov_noit"] = noit[:6]; R["bottom_prov"] = R["provinces"][-5:]
R["prov_by"] = {p["name"]: p for p in R["provinces"]}
R["cert_top_prov"] = [p["prov"] for p in sorted(PR, key=lambda p: -p["km_certain"])[:4]]

# ---------- travel ----------
C = TV["city"]
R["modes"] = {k: {"label": v["label"], "kmd": v["kmd"], "lo": v["lo"], "hi": v["hi"]} for k, v in MODES.items()}
R["offroad_factor"] = OFFROAD_FACTOR; R["offroad_max_km"] = OFFROAD_MAX_KM; R["crossing_days"] = CROSSING_DAYS
fin = lambda v: float(v) if np.isfinite(v) else None   # None: not reachable that way
R["city"] = {}
for k, c in C.items():
    R["city"][k] = {"name": c["name"], "latin": c["latin"], "node_name": c["node_name"], "foot": c["days"]["foot"], "cart": c["days"]["cart"],
                    "courier": c["days"]["courier"], "foot_lo": c["foot_range"][0], "foot_hi": c["foot_range"][1],
                    "cart_lo": c["cart_range"][0], "cart_hi": c["cart_range"][1], "road_km": c["road_km"], "sea": c["sea"],
                    "straight_km": c["straight_km"], "detour": c["detour"], "foot_nohyp": fin(c["foot_nohyp"]), "foot_nosea": fin(c["foot_nosea"]),
                    "foot_flat": c["foot_flat"], "foot_weeks": c["days"]["foot"] / 7,
                    "route_cert_km": c["route_cert_km"], "route_share_certain": c["route_cert_km"]["Certain"] / c["road_km"] if c["road_km"] else 0}
R["city_order"] = [k for k in sorted(C, key=lambda k: C[k]["days"]["foot"]) if k != "rome"]
R["n_cities"] = len(R["city_order"])
R["farthest"] = TV["farthest"]; R["max_foot"] = TV["max_foot"]
R["km_reachable"] = TV["km_reachable"]; R["km_unreachable"] = TV["km_unreachable"]; R["share_unreachable"] = TV["km_unreachable"] / tot
R["unjoined"] = [{"km": c["km"], "lon": c["lon"], "lat": c["lat"], "n": c["n"]} for c in TV["unjoined"]]
R["foot_bands"] = TV["foot_bands"]
R["km_within"] = TV["km_within"]
R["share_within"] = {md: {d: v / tot for d, v in dd.items()} for md, dd in TV["km_within"].items()}
R["crossings"] = TV["crossings"]
R["n_crossings"] = sum(1 for x in TV["crossings"] if not x["bridge"])
# road km within 30 days on foot, as a share of what can be reached at all
R["share_reach_30_foot"] = TV["km_within"]["foot"]["30"] / TV["km_reachable"]
lon_ = R["city"]["london"]; con = R["city"]["constantinople"]; alx = R["city"]["alexandria"]; car = R["city"]["carthago"]
R["alex_vs_london"] = alx["foot"] / lon_["foot"]
R["carthage_vs_alex"] = car["foot"] - alx["foot"]

# ---------- facts stated in words (page, paper, blog, collage, post) ----------
assert R["cert"]["Conjectured"]["share_km"] > .85 and R["cert"]["Certain"]["share_km"] < .03
assert lon_["sea"] == ["channel"] and con["sea"] == ["otranto"] and alx["sea"] == ["otranto"] and car["sea"] == ["gibraltar"]
assert car["foot"] > alx["foot"] > con["foot"] and lon_["foot"] > con["foot"]
assert lon_["foot_nosea"] is None and con["foot_nosea"] > con["foot"]
assert R["farthest"]["name"] == "Murzuq"
assert R["cert_top_prov"] == ["Arabia", "Syria", "Galatia et Cappadocia", "Iudaea"], R["cert_top_prov"]
assert abs(con["foot_nohyp"] - con["foot"]) < 1 and abs(alx["foot_nohyp"] - alx["foot"]) < 1
assert {"Aegyptus", "Creta et Cyrene", "Armenia Mesopotamia", "Mauretania Tingitana", "Italia, regio VI (Umbria)"} <= {p["name"] for p in R["provinces"][-6:]}
assert R["provinces"][0]["name"].startswith("Italia, regio I ") and [p["name"] for p in noit[:3]] == ["Cyprus", "Iudaea", "Lycia et Pamphylia"]
assert R["bottom_prov"][-1]["name"] == "Armenia Mesopotamia"
assert R["builders"][0]["name"] == "Claudius"
assert R["named_roads"][0]["name"] == "Via Egnatia"
assert R["runs_certain"][0]["road"] == "Via Appia" and R["runs"][2]["road"] == "Via Appia"
assert lon_["route_cert_km"]["Certain"] == 0 and alx["route_cert_km"]["Certain"] > 0
assert [b["name"] for b in R["builders"][:3]] == ["Claudius", "Trajan", "Hadrian"]
assert R["date_bands"][-1]["km"] == max(b["km"] for b in R["date_bands"])
jsave(R, f"{DATA}/results.json", indent=1)

# ---------- page data ----------
band_i = {k: i for i, (k, *_ ) in enumerate(DATEBANDS)}
cert_i = {c: i for i, (c, *_ ) in enumerate(CERT)}
tabs = {k: [] for k in ("name", "cons", "itin", "bib", "cite", "prov")}
tix = {k: {} for k in tabs}


def tid(k, v):
    if not isinstance(v, str) or not v:
        return -1
    if v not in tix[k]:
        tix[k][v] = len(tabs[k]); tabs[k].append(dash(v))
    return tix[k][v]


rows, geo = [], []
for r in S.itertuples():
    gs = r.geom.simplify(0.0012, preserve_topology=False)
    co = np.array(gs.coords); co[0] = r.geom.coords[0]; co[-1] = r.geom.coords[-1]
    q = np.round(co * 1e4).astype(int); d = np.vstack([q[:1], np.diff(q, axis=0)]).ravel().tolist()
    geo.append(d)
    yr = None if r.year is None or (isinstance(r.year, float) and np.isnan(r.year)) else int(r.year)
    rows.append([0 if r.type == "Main Road" else 1, cert_i[r.cert], band_i.get(r.band, -1), yr, tid("name", r.name), tid("cons", r.cons),
                 tid("itin", r.itin), tid("bib", r.bib), tid("cite", r.cite), tid("prov", r.prov), round(float(r.km), 2), round(float(r.slope), 1), round(float(r.pas), 2)])
site = {"cols": ["type", "cert", "band", "year", "name", "cons", "itin", "bib", "cite", "prov", "km", "slope", "pass"], "rows": rows, "geo": geo, **tabs}
jsave(site, f"{DATA}/roads_site.json")
print("roads_site.json", os.path.getsize(f"{DATA}/roads_site.json") // 1024, "KB")
# provinces for the page (DARE outlines, simplified) with density
import geopandas as gpd
P = AN["P"].copy(); P["geometry"] = P.geometry.simplify(0.02)
feats = []
for r in P.itertuples():
    p = R["prov_by"].get(r.prov)
    if p is None:
        continue
    gj = gpd.GeoSeries([r.geometry]).__geo_interface__["features"][0]["geometry"]
    def rnd(c):
        return [rnd(x) for x in c] if isinstance(c[0], (list, tuple)) else [round(c[0], 3), round(c[1], 3)]
    gj["coordinates"] = rnd(gj["coordinates"])
    feats.append({"type": "Feature", "geometry": gj, "properties": {"name": r.prov, "km": round(p["km"], 1), "area_km2": round(p["area_km2"]),
                  "density": round(p["density"], 2), "share_certain": round(p["share_certain"], 3)}})
jsave({"type": "FeatureCollection", "source": "Provinces of about AD 117: Digital Atlas of the Roman Empire (DARE), Johan Ahlfeldt, via github.com/klokantech/roman-empire; simplified", "features": feats}, f"{DATA}/provinces.geojson")
print("provinces.geojson", os.path.getsize(f"{DATA}/provinces.geojson") // 1024, "KB")
# clean section table
out = S[["id", "name", "type", "cert", "year", "year_src", "lo", "lo_e", "up", "up_e", "cons", "itin", "desc", "cite", "bib", "km", "slope", "pas", "u", "v", "prov"]].copy()
out = out.rename(columns={"cert": "certainty", "year": "date_used", "year_src": "date_source", "lo": "lower_date", "lo_e": "lower_date_error", "up": "upper_date",
                          "up_e": "upper_date_error", "cons": "construction_period", "itin": "itinerary", "desc": "description", "cite": "digitised_by",
                          "bib": "bibliography", "slope": "avg_slope_deg", "pas": "passability", "u": "from_node", "v": "to_node", "prov": "province_ad117"})
mid = TR["mid"]
for md in MODE_ORDER:
    out[f"days_from_rome_{md}"] = np.where(np.isfinite(mid[f"mid_{md}"].values), np.round(mid[f"mid_{md}"].values, 2), np.nan)
for c in out.columns:
    if out[c].dtype == object:
        out[c] = [dash(x) if isinstance(x, str) else x for x in out[c]]
out.round({"km": 3, "avg_slope_deg": 3, "passability": 4}).to_csv(f"{DATA}/roads.csv", index=False)
print("roads.csv", os.path.getsize(f"{DATA}/roads.csv") // 1024, "KB")
print({k: R["city"][k]["foot"] for k in R["city_order"]})
