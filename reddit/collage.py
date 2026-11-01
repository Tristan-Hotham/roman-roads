"""Reddit collage (r/dataisbeautiful style): every Roman road in Itiner-e coloured by modelled days on foot from Rome, with
the days shading off the roads and isochrone lines every 30 days, on a light paper map. Labels sit on open sea or on the
paper, with a halo; a check at the end asserts that no label box touches land or a road, that labels do not overlap,
and that no leader line crosses another label.
Run: python3 reddit/collage.py   (after code/01 to 04)
"""
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "code"))
from figlib import *
import matplotlib.patheffects as pe
from matplotlib.patches import Rectangle, FancyBboxPatch
from matplotlib.lines import Line2D
from scipy.ndimage import gaussian_filter
from shapely.geometry import Polygon, box as sbox, LineString as LS
from shapely.ops import unary_union as uu

N, TR, AN, R = load()
S = AN["S"]; T = TR["T"]
OUT = os.path.join(ROOT, "reddit", "roman_roads_days_from_rome.png")
XY = road_xy(S, simplify=0.002)
EXT = empire_extent()
W_IN, DPI = 15, 200                     # 3000 px wide
MAPW = W_IN * .976; MAPH = MAPW * (EXT[3] - EXT[2]) / (EXT[1] - EXT[0])
TOP_IN, BOT_IN = 1.55, 1.75              # paper bands for the title, and for the legend and credits
H_IN = MAPH + TOP_IN + BOT_IN
fig = plt.figure(figsize=(W_IN, H_IN), facecolor=BG)
TOP, BOT = 1 - TOP_IN / H_IN, BOT_IN / H_IN
ax = fig.add_axes([0.012, BOT, 0.976, TOP - BOT])
ax.set_facecolor(SEA); draw_land(ax, lw=.45)
ax.set_xlim(EXT[0], EXT[1]); ax.set_ylim(EXT[2], EXT[3]); ax.set_aspect("equal"); ax.set_xticks([]); ax.set_yticks([])
for s in ax.spines.values(): s.set_color(RULE)

# shading off the roads and isochrone lines
D, dist, ext = days_raster(TR, S, EXT, res_m=4000)
fin = np.isfinite(D)
rgb = ramp_rgb(np.where(fin, D, 0)); rgb[~fin & ~np.isnan(D)] = (.62, .6, .56)
alpha = np.where(np.isnan(D), 0, np.clip(1 - (dist - 30) / 25, .35, 1) * .36)
ax.imshow(np.dstack([rgb, alpha]), extent=ext, origin="upper", zorder=2, interpolation="bilinear")
Dc = np.where(fin, D, np.nan)
sm = gaussian_filter(np.nan_to_num(Dc, nan=0), 3.0) / np.maximum(gaussian_filter(fin.astype(float), 3.0), 1e-6)
sm = np.where(fin, sm, np.nan)
xs = np.linspace(ext[0], ext[1], D.shape[1]); ys = np.linspace(ext[3], ext[2], D.shape[0])
ax.contour(xs, ys, sm, levels=[30, 60, 90, 120, 150], colors=[FG], linewidths=.9, alpha=.6, zorder=3, linestyles="solid")

# roads coloured by days to their middle
w = S.km.values / (MODES["foot"]["kmd"] * S.pas.values)
mid = np.minimum(T["foot"][S.u.values] + w / 2, T["foot"][S.v.values] + w / 2)
col = [tuple(ramp_rgb(d)) if np.isfinite(d) else (.55, .53, .5) for d in mid]
main = (S.type == "Main Road").values
for sel, lw in ((~main, .42), (main, .8)):
    idx = np.where(sel)[0]
    ax.add_collection(LineCollection([XY[i] for i in idx], colors=[col[i] for i in idx], linewidths=lw, zorder=4, capstyle="round"))
# sea crossings
nd = N["nodes"]
for x in N["X"]:
    if x["bridge"]:
        continue
    px, py = proj(nd.lon.values[[x["u"], x["v"]]], nd.lat.values[[x["u"], x["v"]]])
    ax.plot(px, py, color="#2E6FA8", lw=1.6, ls=(0, (1.2, 2.2)), zorder=5)

halo = [pe.withStroke(linewidth=4, foreground=PAPER)]
C = R["city"]
d0 = lambda k: f"{C[k]['foot']:.0f}"
LABELS = [
    ("london", f"LONDINIUM\n{d0('london')} days on foot\ncart {C['london']['cart']:.0f} · courier {C['london']['courier']:.0f}"),
    ("constantinople", f"BYZANTIUM\n{d0('constantinople')} days on foot\ncart {C['constantinople']['cart']:.0f} · courier {C['constantinople']['courier']:.0f}"),
    ("hierosolyma", f"HIEROSOLYMA\n{d0('hierosolyma')} days"),
    ("alexandria", f"ALEXANDRIA\n{d0('alexandria')} days on foot\ncart {C['alexandria']['cart']:.0f} · courier {C['alexandria']['courier']:.0f}"),
    ("rome", "ROMA\nday 0"),
    ("carthago", f"CARTHAGO\n{d0('carthago')} days"),
    ("gades", f"GADES\n{d0('gades')} days"),
    ("athenae", f"ATHENAE\n{d0('athenae')} days"),
    ("lepcis", f"LEPCIS MAGNA\n{d0('lepcis')} days"),
    ("eboracum", f"EBURACUM\n{d0('eboracum')} days"),
    ("lutetia", f"LUTETIA\n{d0('lutetia')} days"),
]
callout = (f"By road alone, Carthage was {C['carthago']['foot']:.0f} days' walk from Rome:\n"
           f"{C['carthago']['road_km']:,.0f} km by Spain and North Africa, for a city\n{C['carthago']['straight_km']:,.0f} km away. Everyone took a ship.")
landpoly = uu([Polygon(r[0], r[1:]) for r in land_rings("50m")])
from shapely.strtree import STRtree
from shapely.geometry import Point
from shapely.ops import nearest_points
rl = [LS(xy) for xy in XY if len(xy) > 1]; rtree = STRtree(rl)
mapbox = sbox(EXT[0], EXT[2], EXT[1], EXT[3]).buffer(-40000)
fig.canvas.draw(); rend = fig.canvas.get_renderer(); inv = ax.transData.inverted()


def dbox(t, pad=5):
    bb = t.get_window_extent(rend); (x0, y0), (x1, y1) = inv.transform([[bb.x0 - pad, bb.y0 - pad], [bb.x1 + pad, bb.y1 + pad]])
    return sbox(min(x0, x1), min(y0, y1), max(x0, x1), max(y0, y1))


boxes, leaders, dots = {}, {}, {}
MISSING = []
for k, _, _, xy in CITIES:
    dots[k] = proj(*xy)


def ok_box(b, k):
    if os.environ.get("DBG") == k:
        print(k, mapbox.contains(b), b.intersects(landpoly), any(rl[i].intersects(b) for i in rtree.query(b)), [o for o, bb in boxes.items() if b.intersects(bb)], [o for o, L_ in leaders.items() if L_.intersects(b)], INV.transform(*b.centroid.coords[0]))
    if not mapbox.contains(b) or b.intersects(landpoly) or any(rl[i].intersects(b) for i in rtree.query(b)):
        return False
    if any(b.intersects(o) for o in boxes.values()) or any(L_.intersects(b) for L_ in leaders.values()):
        return False
    if any(Point(d).buffer(15000).intersects(b) for kk, d in dots.items() if kk != k and kk in [l[0] for l in LABELS]):
        return False
    return True


def place(k, txt, fs, anchor, family=SER, style_="normal", radii=range(50, 900, 15), weight="semibold"):
    t = ax.text(0, 0, txt, ha="center", va="center", fontsize=fs, color=FG, zorder=10, path_effects=halo, linespacing=1.12,
                fontweight=weight, family=family, style=style_)
    for rkm in radii:
        for ang in np.linspace(0, 2 * np.pi, 36, endpoint=False):
            x = anchor[0] + rkm * 1000 * np.cos(ang); y = anchor[1] + rkm * 1000 * np.sin(ang)
            t.set_position((x, y)); b = dbox(t)
            if not ok_box(b, k):
                continue
            if k in dots:
                p = nearest_points(b, Point(anchor))[0]; L_ = LS([anchor, (p.x, p.y)])
                if any(L_.intersects(o) for o in boxes.values()):
                    continue
                leaders[k] = L_
            boxes[k] = b
            return t
    b = dbox(t); print(f"no place for {k}: box {b.bounds[2]-b.bounds[0]:.0f} x {b.bounds[3]-b.bounds[1]:.0f} m"); t.remove(); MISSING.append(k)
    return None


def city(k, txt):
    x, y = dots[k]
    ax.plot(x, y, "o", ms=7 if k in HEADLINE + ["rome"] else 5.5, mfc=PAPER, mec=FG, mew=1.6, zorder=8)
    place(k, txt, {"constantinople": 9.2}.get(k, 11.5 if k in HEADLINE else 9.8), (x, y), radii=range(50, 650 if k in HEADLINE else 560, 12))


for k, txt in LABELS[:5]:
    city(k, txt)
for anc in ((18.0, 34.4), (5.0, 39.5), (-8.5, 46.0)):
    if place("callout", callout, 10.5, proj(*anc), family=SER, style_="italic", radii=range(0, 450, 15), weight="normal") is not None:
        MISSING[:] = [m for m in MISSING if m != "callout"]
        break
for k, txt in LABELS[5:]:
    city(k, txt)
for k, L_ in leaders.items():
    (x0, y0), (x1, y1) = L_.coords
    ax.plot([x0, x1], [y0, y1], color=FG, lw=.9, zorder=7)
BAD = []
for k, b in boxes.items():
    if b.intersects(landpoly): BAD.append(("label on land", k))
    if any(rl[i].intersects(b) for i in rtree.query(b)): BAD.append(("label over a road", k))
    for k2, b2 in boxes.items():
        if k2 != k and b.intersects(b2): BAD.append(("labels overlap", k, k2))
    for k2, L_ in leaders.items():
        if k2 != k and L_.intersects(b): BAD.append(("leader crosses label", k2, k))

# ---------- title band ----------
yt = lambda inch: 1 - inch / H_IN
fig.text(.02, yt(.22), "ALL ROADS LEAD FROM ROME", fontsize=12, color=HOT, fontweight="medium", va="top")
fig.text(.02, yt(.45), f"How many days on foot from Rome? Every Roman road, {R['km_total']:,.0f} km of it",
         fontproperties=DISPB, fontsize=27, va="top", color=FG)
fig.text(.02, yt(1.0), f"Every road in Itiner-e, the new open map of the roads of the Roman Empire, coloured by modelled days on foot from the Forum. "
         f"{MODES['foot']['kmd']} km a day, slowed on slopes;\none day for each short sea crossing (Channel, Messina, Otranto, Gibraltar). "
         f"Only {R['cert']['Certain']['share_km'] * 100:.1f}% of the network is mapped as certain; the rest is conjectured ({R['cert']['Conjectured']['share_km'] * 100:.0f}%) or hypothetical ({R['cert']['Hypothetical']['share_km'] * 100:.1f}%).",
         fontsize=10.5, va="top", color=MUT, family=SER, linespacing=1.35)

# ---------- legend band (bottom 1.75 in) ----------
yb = lambda inch: inch / H_IN
lx = fig.add_axes([0.02, yb(.15), 0.40, yb(1.35)]); lx.axis("off"); lx.set_xlim(0, 1); lx.set_ylim(0, 1)
n = 300
for i in range(n):
    lx.add_patch(Rectangle((i / n * .95, .66), .95 / n * 1.05, .13, fc=ramp_rgb(RAMP[-1][0] * i / n), ec="none"))
for tk in (0, 30, 60, 90, 120, 150, 200):
    lx.text(tk / RAMP[-1][0] * .95, .62, f"{tk}{'+' if tk == 200 else ''}", ha="center", va="top", fontsize=10)
lx.text(0, .86, "Days on foot from Rome: road colour, and shading up to 50 km off the road", fontsize=10.5, va="bottom", color=FG, fontweight="medium")
lx.plot([0, .06], [.26, .26], color=FG, lw=.9, alpha=.6); lx.text(.075, .26, "line every 30 days", va="center", fontsize=9.5)
lx.plot([.36, .42], [.26, .26], color="#2E6FA8", lw=1.8, ls=(0, (1.2, 2.2))); lx.text(.435, .26, "sea crossing (1 day)", va="center", fontsize=9.5)
lx.add_patch(Rectangle((.72, .19), .045, .14, fc=(.62, .6, .56), alpha=.7, ec="none")); lx.text(.775, .26, "no road link", va="center", fontsize=9.5)
lx.plot([0, .06], [.04, .04], color=FG, lw=2.2); lx.text(.075, .04, "main road", va="center", fontsize=9.5)
lx.plot([.36, .42], [.04, .04], color=FG, lw=.8); lx.text(.435, .04, "secondary road", va="center", fontsize=9.5)

bx = fig.add_axes([0.555, yb(.38), 0.205, yb(1.05)]); bx.set_facecolor(BG)
ks = ["london", "constantinople", "alexandria"]; modes = ["foot", "cart", "courier"]; nm = {"foot": "on foot", "cart": "cart", "courier": "courier"}
for i, k in enumerate(ks):
    for j, m in enumerate(modes):
        v = C[k][m]; y = (2 - i) * 1.0 + (1 - j) * .3
        bx.barh(y, v, height=.24, color=ramp_rgb(v), zorder=3)
        bx.text(v + 3, y, f"{v:.0f} {nm[m]}", va="center", fontsize=7.6)
bx.set_yticks([2, 1, 0]); bx.set_yticklabels(["London", "Constantinople", "Alexandria"], fontsize=9.5)
bx.set_xlim(0, 250); bx.tick_params(axis="x", labelsize=8.5, colors=MUT)
for s_ in ("top", "right"): bx.spines[s_].set_visible(False)
for s_ in ("left", "bottom"): bx.spines[s_].set_color(MUT)
bx.set_title("Days from Rome, three ways to travel", fontsize=10, loc="left", color=FG, fontweight="medium")

fig.text(.79, yb(1.55), "Sources", fontsize=10, color=FG, fontweight="medium", va="top")
fig.text(.79, yb(1.35), "Roads: Itiner-e static version 2024,\nde Soto, Pažout, Brughmans et al.\n(2025), CC BY 4.0. Speeds: Wikipedia,\n'Roman roads'. Land: Natural Earth.\nTimes are modelled, not recorded.", fontsize=8.6, color=MUT, va="top", linespacing=1.3)
fig.text(.79, yb(.18), "maps.tristanhotham.com/roman-roads", fontsize=9.6, color=HOT, va="bottom", fontweight="medium")
fig.savefig(OUT, dpi=DPI, facecolor=BG)
print(OUT)
assert not BAD, BAD
assert not MISSING, MISSING
print("label checks passed")
