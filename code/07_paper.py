"""Step 7. Paper PDF: fill code/paper_template.tex from data/results.json (with three tables built here), write
release/paper/Hotham_Roads_of_the_Roman_Empire.tex and compile it with xelatex (figures from step 6). The DOI line keeps the
publisher's 10.5281/zenodo.23857866 placeholder unless ROMAN_DOI is set.
Run: python3 code/07_paper.py
"""
import os, re, subprocess, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import *

R = jload(f"{DATA}/results.json")
OUT = os.path.join(ROOT, "release", "paper"); NAME = "Hotham_Roads_of_the_Roman_Empire"
DOI = os.environ.get("ROMAN_DOI", "10.5281/zenodo.23857866")
tex = lambda s: str(s).replace("&", "\\&").replace("%", "\\%").replace("_", "\\_").replace("#", "\\#")


def ffmt(v, f):
    if f == "pct": return f"{round(v * 100)}\\%"
    if f == "pct1": return f"{v * 100:.1f}\\%"
    if f in (None, "raw"): return tex(v)
    return fmt(v, f)


rows = []
for k in R["city_order"]:
    c = R["city"][k]
    rows.append(f"{tex(c['name'])} & {tex(c['latin'])} & {c['road_km']:,.0f} & {c['foot']:.0f} & {c['foot_lo']:.0f} to {c['foot_hi']:.0f} & {c['cart']:.0f} & {c['courier']:.0f}\\\\")
T_CITIES = ("\\begin{table}[tbp]\\centering\\small\\caption{Modelled days from Rome. Road km: length of the quickest route on foot, excluding sea crossings. Range: on foot at 25 and 20 km a day.}\\label{tab:cities}"
            "\\begin{tabular}{llrrrrr}\\toprule City & Ancient name & Road km & On foot & Range & Cart & Courier\\\\\\midrule\n" + "\n".join(rows) + "\n\\bottomrule\\end{tabular}\\end{table}")
rows = []
for i, r in enumerate(R["runs"][:10]):
    rows.append(f"{i + 1} & {tex(r['label'])} & {r['km']:.1f} & {r['maxdev_m']:.0f} & {round(r['share_certain'] * 100)}\\%\\\\")
T_RUNS = ("\\begin{table}[tbp]\\centering\\small\\caption{The longest straight runs: stretches within 200 m of a straight line. Off line: largest deviation of the digitised road.}\\label{tab:runs}"
          "\\begin{tabular}{rp{8.2cm}rrr}\\toprule & Stretch & km & Off line (m) & Certain\\\\\\midrule\n" + "\n".join(rows) + "\n\\bottomrule\\end{tabular}\\end{table}")
rows = []
P = R["provinces"]
for p in P[:12] + [None] + P[-5:]:
    if p is None:
        rows.append("\\multicolumn{5}{c}{\\dots}\\\\"); continue
    rows.append(f"{tex(p['name'])} & {p['km']:,.0f} & {p['area_km2']:,.0f} & {p['density']:.1f} & {round(p['share_certain'] * 100)}\\%\\\\")
T_PROV = ("\\begin{table}[tbp]\\centering\\small\\caption{Road density by province, about AD 117: the twelve densest and the five least dense.}\\label{tab:prov}"
          "\\begin{tabular}{lrrrr}\\toprule Province & Road km & Land km\\textsuperscript{2} & km per 1,000 km\\textsuperscript{2} & Certain\\\\\\midrule\n" + "\n".join(rows) + "\n\\bottomrule\\end{tabular}\\end{table}")


def sub(m):
    k = m.group(1)
    if k.startswith("TABLE_"):
        return {"TABLE_CITIES": T_CITIES, "TABLE_RUNS": T_RUNS, "TABLE_PROV": T_PROV}[k]
    return ffmt(get(R, k), m.group(3))


src = open(os.path.join(ROOT, "code", "paper_template.tex"), encoding="utf-8").read()
out = re.sub(r"\{\{([^{}|]+)(\|(\w+))?\}\}", sub, src).replace("DOIVALUE", DOI)
assert "{{" not in out.replace("10.5281/zenodo.23857866", "")
body = re.sub(r"(?m)^%.*$", "", out)
for bad in ("—", "–", "DSIT", "DCMS", "--"):
    assert bad not in body, bad
os.makedirs(OUT, exist_ok=True)
open(f"{OUT}/{NAME}.tex", "w", encoding="utf-8").write(out)
for _ in range(2):
    r = subprocess.run(["xelatex", "-interaction=nonstopmode", f"{NAME}.tex"], cwd=OUT, capture_output=True, text=True)
pdf = f"{OUT}/{NAME}.pdf"
assert os.path.exists(pdf), r.stdout[-3000:]
n = int(re.search(r"Pages:\s+(\d+)", subprocess.run(["pdfinfo", pdf], capture_output=True, text=True).stdout).group(1))
txt = subprocess.run(["pdftotext", pdf, "-"], capture_output=True, text=True).stdout
for bad in ("—", "–", "??"):
    assert bad not in txt, ("pdf", bad)
print(NAME, n, "pages")
assert 8 <= n <= 15, n
for ext in ("aux", "log", "out"):
    if os.path.exists(f"{OUT}/{NAME}.{ext}"):
        os.remove(f"{OUT}/{NAME}.{ext}")
