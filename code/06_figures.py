"""Step 6. Figures for the blog (release/blog/b_*.png), the paper (release/paper/fig_*.png, same images) and the header
card (header.png, 1200 x 630). Every number drawn comes from data/results.json or the work files of steps 1 to 4.
Run: python3 code/06_figures.py
"""
import os, sys, shutil
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from figlib import *
from matplotlib.colors import ListedColormap
import matplotlib.patheffects as pe

N, TR, AN, R = load()
S = AN["S"]; T = TR["T"]
BLOG = os.path.join(ROOT, "release", "blog"); PAP = os.path.join(ROOT, "release", "paper")
os.makedirs(BLOG, exist_ok=True); os.makedirs(PAP, exist_ok=True)
XY = road_xy(S)
EXT = empire_extent()
halo = [pe.withStroke(linewidth=3.2, foreground=PAPER)]
CITYXY = {k: proj(*xy) for k, _, _, xy in CITIES}


def base(ax, ext=EXT):
    ax.set_facecolor(SEA); draw_land(ax, lw=.4)
    ax.set_xlim(ext[0], ext[1]); ax.set_ylim(ext[2], ext[3]); ax.set_aspect("equal"); ax.set_xticks([]); ax.set_yticks([])
    for s in ax.spines.values(): s.set_visible(False)


def roads(ax, colours, lw_main=.55, lw_sec=.32, z=4, dashed_hyp=False, alpha=1):
    main = (S.type == "Main Road").values; hyp = (S.cert == "Hypothetical").values
    for sel, lw in ((~main, lw_sec), (main, lw_main)):
        for h in ((False, True) if dashed_hyp else (None,)):
            idx = np.where(sel & (hyp == h if h is not None else True))[0]
            if not len(idx): continue
            lc = LineCollection([XY[i] for i in idx], colors=[colours[i] for i in idx], linewidths=lw, zorder=z, alpha=alpha,
                                linestyles=(0, (2.5, 2)) if h else "solid", capstyle="round")
            ax.add_collection(lc)


def iso_rgba(D, alpha=.5):
    """Ramp colours; grey where no road leads from Rome (islands), transparent where there is no road nearby."""
    fin = np.isfinite(D)
    rgb = ramp_rgb(np.where(fin, D, 0)); rgb[~fin & ~np.isnan(D)] = (.62, .6, .56)
    a = np.where(np.isnan(D), 0, alpha)
    return np.dstack([rgb, a])


def ramp_bar(ax, x, y, w, h, ticks=(0, 30, 60, 90, 120, 150, 200), label="days on foot from Rome", fs=9, trans=None):
    from matplotlib.patches import Rectangle
    n = 200
    for i in range(n):
        d = RAMP[-1][0] * i / n
        ax.add_patch(Rectangle((x + w * i / n, y), w / n * 1.02, h, transform=trans or ax.transAxes, fc=ramp_rgb(d), ec="none", clip_on=False, zorder=20))
    for t in ticks:
        ax.text(x + w * t / RAMP[-1][0], y - h * .5, f"{t}{'+' if t == RAMP[-1][0] else ''}", transform=trans or ax.transAxes, ha="center", va="top", fontsize=fs, color=FG, zorder=20)
    ax.text(x, y + h * 1.5, label, transform=trans or ax.transAxes, ha="left", va="bottom", fontsize=fs, color=MUT, zorder=20)


mid = sec_mid_days(S, T)
road_col = [ramp_rgb(d) if np.isfinite(d) else (.62, .6, .56) for d in mid]

# ---------- 1. days from Rome on foot ----------
D, dist, ext = days_raster(TR, S, EXT, res_m=5000)
fig = plt.figure(figsize=(12, 10.2), facecolor=BG); ax = fig.add_axes([0.01, 0.01, 0.98, 0.89]); base(ax)
ax.imshow(iso_rgba(D, .42), extent=ext, origin="upper", zorder=2, interpolation="bilinear")
roads(ax, road_col, .6, .35)
LAB = {"london": (-1, 1, "left"), "constantinople": (1, 1, "left"), "alexandria": (1, -1, "left"), "carthago": (0, -1, "center"),
       "lutetia": (-1, 0, "right"), "athenae": (0, -1, "center"), "hierosolyma": (1, 0, "left"), "gades": (0, -1, "center"),
       "antiochia": (1, 0, "left"), "sirmium": (0, 1, "center"), "rome": (-1, -1, "right"), "eboracum": (1, 0, "left"), "lugdunum": (-1, 0, "right")}
for k, (dx, dy, ha) in LAB.items():
    x, y = CITYXY[k]; c = R["city"].get(k)
    ax.plot(x, y, "o", ms=5, mfc=PAPER, mec=FG, mew=1.3, zorder=8)
    txt = "Roma" if k == "rome" else f"{c['latin']}\n{c['foot']:.0f} days"
    ax.annotate(txt, (x, y), xytext=(dx * 7, dy * 7), textcoords="offset points", ha=ha, va="bottom" if dy > 0 else ("top" if dy < 0 else "center"),
                fontsize=10, color=FG, fontweight="medium", zorder=9, path_effects=halo, linespacing=1.05)
ramp_bar(ax, .02, .06, .32, .016)
fig.text(.02, .975, "Days on foot from Rome, by road", fontproperties=DISPB, fontsize=19, va="top", color=FG)
fig.text(.02, .935, f"{MODES['foot']['kmd']} km a day, slowed on slopes; one day per sea crossing; grey: islands with no road link", fontsize=10, va="top", color=MUT)
ax.text(.985, .015, "Roads: Itiner-e (CC BY 4.0). Modelled times.", transform=ax.transAxes, ha="right", fontsize=8.5, color=MUT)
save(fig, f"{BLOG}/b_days.png", dpi=170)

# ---------- 2. certainty ----------
fig = plt.figure(figsize=(12, 9.3), facecolor=BG); ax = fig.add_axes([0.01, 0.01, 0.98, 0.98]); base(ax)
cc = {c: tuple(int(col[i:i + 2], 16) / 255 for i in (1, 3, 5)) for c, _, col in CERT}
order = np.argsort([{"Hypothetical": 0, "Conjectured": 1, "Certain": 2}[c] for c in S.cert])
for cert, lw, ls in (("Hypothetical", .5, (0, (2.5, 2))), ("Conjectured", .42, "solid"), ("Certain", 1.1, "solid")):
    idx = np.where(S.cert.values == cert)[0]
    ax.add_collection(LineCollection([XY[i] for i in idx], colors=[cc[cert]], linewidths=lw, linestyles=ls, zorder=4 + (cert == "Certain")))
from matplotlib.lines import Line2D
hs = [Line2D([], [], color=cc[c], lw=w, ls=ls, label=f"{c}: {R['cert'][c]['km']:,.0f} km ({R['cert'][c]['share_km'] * 100:.1f}%)") for c, w, ls in
      (("Certain", 2.2, "-"), ("Conjectured", 1.4, "-"), ("Hypothetical", 1.2, (0, (2.5, 2))))]
lg = ax.legend(handles=hs, loc="lower left", bbox_to_anchor=(.015, .04), frameon=True, fontsize=10, title="How sure we are of each road's course", title_fontsize=10.5)
lg.get_frame().set_facecolor(PAPER); lg.get_frame().set_edgecolor(RULE)
ax.text(.02, .975, "Certain, conjectured, hypothetical", transform=ax.transAxes, fontproperties=DISPB, fontsize=19, va="top", color=FG)
ax.text(.02, .935, f"Only {R['cert']['Certain']['share_km'] * 100:.1f}% of the {R['km_total']:,.0f} km is mapped as certain", transform=ax.transAxes, fontsize=10, va="top", color=MUT)
ax.text(.985, .015, "Roads: Itiner-e (CC BY 4.0)", transform=ax.transAxes, ha="right", fontsize=8.5, color=MUT)
save(fig, f"{BLOG}/b_certainty.png", dpi=170)

# ---------- 3. cities by mode ----------
K = R["city_order"]
fig, ax = plt.subplots(figsize=(10, 7.4), facecolor=BG); ax.set_facecolor(BG)
y = np.arange(len(K))[::-1]
for yi, k in zip(y, K):
    c = R["city"][k]
    ax.barh(yi, c["foot"], color=ramp_rgb(c["foot"]), height=.62, zorder=3)
    ax.plot([c["foot_lo"], c["foot_hi"]], [yi, yi], color=FG, lw=1, zorder=4)
    ax.plot(c["cart"], yi, "D", ms=6, mfc=PAPER, mec=FG, mew=1.2, zorder=5)
    ax.plot(c["courier"], yi, "o", ms=6, mfc=FG, mec=FG, zorder=5)
    ax.text(c["foot_hi"] + 3, yi, f"{c['foot']:.0f}", va="center", fontsize=10, color=FG)
ax.set_yticks(y); ax.set_yticklabels([R["city"][k]["name"] for k in K], fontsize=10)
ax.set_xlabel("days from Rome", color=MUT); ax.set_xlim(0, 260); style(ax)
hs = [plt.Rectangle((0, 0), 1, 1, color=ramp_rgb(80), label=f"On foot ({MODES['foot']['kmd']} km a day; line: 20 to 25)"),
      Line2D([], [], marker="D", ls="", mfc=PAPER, mec=FG, label=f"Horse-drawn cart ({MODES['cart']['kmd']:.0f} km a day)"),
      Line2D([], [], marker="o", ls="", mfc=FG, mec=FG, label=f"Courier ({MODES['courier']['kmd']:.0f} km a day)")]
ax.legend(handles=hs, loc="lower right", frameon=False, fontsize=9.5)
ax.set_title("Modelled days from Rome by road", loc="left", fontproperties=DISPB, fontsize=17, color=FG, pad=12)
fig.tight_layout(); save(fig, f"{BLOG}/b_cities.png", dpi=170)

# ---------- 4. province density ----------
import geopandas as gpd
P = AN["P"].to_crs(LAEA)
dens = {p["name"]: p["density"] for p in R["provinces"]}
fig = plt.figure(figsize=(12, 9.3), facecolor=BG); ax = fig.add_axes([0.01, 0.01, 0.98, 0.98]); base(ax)
a_, b_ = np.array([0xF3, 0xE3, 0xC3]) / 255, np.array([0x7A, 0x1F, 0x2B]) / 255
for r in P.itertuples():
    d = dens.get(r.prov)
    if d is None: continue
    t = min(1, d / 140); col = a_ + (b_ - a_) * t
    gpd.GeoSeries([r.geometry]).plot(ax=ax, color=col, edgecolor=PAPER, linewidth=.6, zorder=2)
ax.add_collection(LineCollection(XY, colors=[(0.12, 0.1, 0.09, .35)], linewidths=.18, zorder=4))
for p in R["provinces"][:5] + R["provinces"][-2:]:
    g = P[P.prov == p["name"]].geometry.iloc[0]; pt = g.representative_point()
    nm = p["name"].replace("Italia, regio I (Latium et Campania)", "Latium et Campania")
    ax.annotate(f"{nm}\n{p['density']:.0f}", (pt.x, pt.y), ha="center", va="center", fontsize=9, color=FG, zorder=9, path_effects=halo)
from matplotlib.patches import Rectangle
for i, v in enumerate(range(0, 141, 20)):
    t = v / 140; ax.add_patch(Rectangle((.02 + i * .04, .06), .04, .02, transform=ax.transAxes, fc=a_ + (b_ - a_) * t, ec="none", zorder=20))
    ax.text(.02 + i * .04, .05, f"{v}", transform=ax.transAxes, fontsize=8.5, ha="center", va="top")
ax.text(.02, .09, "km of road per 1,000 km² (140 and more darkest)", transform=ax.transAxes, fontsize=9, color=MUT)
ax.text(.02, .975, "Road density by province, about AD 117", transform=ax.transAxes, fontproperties=DISPB, fontsize=19, va="top", color=FG)
ax.text(.02, .935, f"Empire average {R['empire_density']:.0f} km per 1,000 km²; provinces from DARE, roads from Itiner-e", transform=ax.transAxes, fontsize=10, va="top", color=MUT)
save(fig, f"{BLOG}/b_provinces.png", dpi=170)

# ---------- 5. straight runs ----------
from shapely.geometry import LineString as LS
runs = R["runs"][:6]
fig, axs = plt.subplots(2, 3, figsize=(12, 7.0), facecolor=BG)
for ax, r in zip(axs.ravel(), runs):
    lon0, lat0 = (r["lon0"] + r["lon1"]) / 2, (r["lat0"] + r["lat1"]) / 2
    tr = Transformer.from_crs(4326, f"+proj=aeqd +lat_0={lat0} +lon_0={lon0} +datum=WGS84 +units=m", always_xy=True)
    half = 36000
    ax.set_facecolor(PAPER)
    bx = box(lon0 - .7, lat0 - .5, lon0 + .7, lat0 + .5)
    for i, gm in enumerate(S.geom):
        b = gm.bounds
        if b[2] < bx.bounds[0] or b[0] > bx.bounds[2] or b[3] < bx.bounds[1] or b[1] > bx.bounds[3]: continue
        co = np.array(gm.coords); x, yv = tr.transform(co[:, 0], co[:, 1])
        ax.plot(x / 1000, yv / 1000, color="#B8AE9E", lw=.8, zorder=2)
    x0, y0 = tr.transform(r["lon0"], r["lat0"]); x1, y1 = tr.transform(r["lon1"], r["lat1"])
    ax.plot([x0 / 1000, x1 / 1000], [y0 / 1000, y1 / 1000], color=HOT, lw=4, alpha=.45, zorder=3, solid_capstyle="round")
    # the digitised road along the run
    for i, gm in enumerate(S.geom):
        pass
    ax.set_xlim(-half / 1000, half / 1000); ax.set_ylim(-half / 1000 * .75, half / 1000 * .75); ax.set_aspect("equal")
    ax.set_xticks([]); ax.set_yticks([])
    for s in ax.spines.values(): s.set_color(RULE)
    ax.set_title(f"{r['km']:.1f} km", loc="left", fontproperties=DISPB, fontsize=14, color=FG)
    ax.text(0.02, 0.02, r["label"], transform=ax.transAxes, fontsize=8.6, color=FG, va="bottom", wrap=True, path_effects=halo)
    ax.plot([half / 1000 - 12, half / 1000 - 2], [half / 1000 * .75 - 4] * 2, color=FG, lw=1.5, zorder=6); ax.text(half / 1000 - 7, half / 1000 * .75 - 2.8, "10 km", ha="center", fontsize=8, zorder=6, path_effects=halo)
fig.suptitle("The longest straight runs: never more than 200 m off a straight line", x=.02, ha="left", fontproperties=DISPB, fontsize=16, color=FG)
fig.text(.02, .915, "Red band: the straight run. Grey: all Itiner-e roads nearby, at the same scale.", fontsize=9.5, color=MUT)
fig.tight_layout(rect=(0, 0, 1, .92)); save(fig, f"{BLOG}/b_straight.png", dpi=170)

# ---------- 6. builders ----------
B = R["builders"][:10]
fig, ax = plt.subplots(figsize=(10, 5.6), facecolor=BG); ax.set_facecolor(BG)
yy = np.arange(len(B))[::-1]
ax.barh(yy, [b["km"] for b in B], color=HOT, height=.62, zorder=3)
for yi, b in zip(yy, B):
    ax.text(b["km"] + 60, yi, f"{b['km']:,.0f} km", va="center", fontsize=9.5)
ax.set_yticks(yy); ax.set_yticklabels([b["name"] for b in B]); ax.set_xlim(0, 7000); style(ax)
ax.set_xlabel("km of road with this name in the construction period field", color=MUT)
ax.set_title(f"Who built the roads? Only {R['dated']['share_km'] * 100:.0f}% of the network has a date", loc="left", fontproperties=DISPB, fontsize=16, color=FG, pad=12)
fig.tight_layout(); save(fig, f"{BLOG}/b_builders.png", dpi=170)

# ---------- 7. km by days band (paper only) ----------
Bd = R["foot_bands"]
fig, ax = plt.subplots(figsize=(10, 4.6), facecolor=BG); ax.set_facecolor(BG)
labs = [f"{b['a']} to {b['b']}" if b["b"] else f"{b['a']}+" for b in Bd]
ax.bar(range(len(Bd)), [b["km"] / 1000 for b in Bd], color=[ramp_rgb((b["a"] + (b["b"] or 160)) / 2) for b in Bd], zorder=3)
ax.set_xticks(range(len(Bd))); ax.set_xticklabels(labs, fontsize=9); style(ax, axis="y")
ax.set_ylabel("thousand km of road", color=MUT); ax.set_xlabel("days on foot from Rome", color=MUT)
fig.tight_layout(); save(fig, f"{BLOG}/b_bands.png", dpi=170)

# ---------- header card 1200 x 630 ----------
fig = plt.figure(figsize=(12, 6.3), facecolor=BG)
ax = fig.add_axes([0.38, 0.0, 0.62, 1.0])
ext2 = (proj(-10.5, 44)[0], proj(41, 44)[0], proj(16, 25)[1], proj(16, 56.5)[1])
base(ax, ext2)
ax.imshow(iso_rgba(D, .35), extent=ext, origin="upper", zorder=2, interpolation="bilinear")
roads(ax, road_col, .45, .25)
x, y = CITYXY["rome"]; ax.plot(x, y, "o", ms=7, mfc=PAPER, mec=FG, mew=1.6, zorder=8)
fx = fig.add_axes([0, 0, .38, 1]); fx.axis("off"); fx.set_xlim(0, 1); fx.set_ylim(0, 1)
fx.text(.08, .86, "DATA STUDY · HISTORY", fontsize=10, color=HOT, fontweight="medium")
fx.text(.08, .80, "Roads of the\nRoman Empire", fontproperties=DISP, fontsize=40, va="top", color=FG, linespacing=.95)
fx.text(.08, .47, f"{R['km_total']:,.0f} km of road, and\nhow many days from Rome", fontsize=13, va="top", color=FG, family=SER, linespacing=1.3)
fx.text(.08, .30, f"London {R['city']['london']['foot']:.0f} days on foot\nConstantinople {R['city']['constantinople']['foot']:.0f}\nAlexandria {R['city']['alexandria']['foot']:.0f}", fontsize=11.5, va="top", color=FG, linespacing=1.45)
fx.text(.08, .05, "maps.tristanhotham.com/roman-roads", fontsize=9, color=MUT)
fig.savefig(os.path.join(ROOT, "header.png"), dpi=100, facecolor=BG); plt.close(fig)

# paper copies
for fn in os.listdir(BLOG):
    if fn.startswith("b_") and fn.endswith(".png"):
        shutil.copyfile(f"{BLOG}/{fn}", f"{PAP}/fig_{fn[2:]}")
print("figures done")
