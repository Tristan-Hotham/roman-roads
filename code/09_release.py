"""Step 9. Blog post and meta (release/blog), Zenodo files and metadata (release/zenodo), Reddit post (reddit/post.md).
Numbers written out in the blog's alt text are checked against results.json here.
Run: python3 code/09_release.py
"""
import os, re, sys, zipfile, json as _json
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import *

R = jload(f"{DATA}/results.json"); C = R["city"]
REL = os.path.join(ROOT, "release"); NAME = "Hotham_Roads_of_the_Roman_Empire"

# ---------- facts written as numbers in alt text ----------
alt = {"mediolanum": 28, "aquileia": 32, "lugdunum": 50, "lutetia": 67, "athenae": 67, "constantinople": 75, "london": 81, "eboracum": 94,
       "gades": 116, "antiochia": 128, "hierosolyma": 157, "alexandria": 180, "carthago": 210, "lepcis": 231}
for k, v in alt.items():
    assert round(C[k]["foot"]) == v, (k, C[k]["foot"])
assert [round(r["km"], 1) for r in R["runs"][:6]] == [56.1, 49.4, 42.0, 40.5, 33.7, 32.5]
assert R["runs"][5]["from"] == "Nemetacum" and R["runs"][5]["to"] == "Camaracum"
assert all(0.45 < C[k]["cart"] / C[k]["foot"] < 0.56 and 0.25 < C[k]["courier"] / C[k]["foot"] < 0.32 for k in alt)
assert round(R["runs"][0]["km"]) == 56

# ---------- blog ----------
post = fill(open(os.path.join(ROOT, "code", "blog_template.html"), encoding="utf-8").read(), R)
used = re.findall(r"\{\{IMG\|([^|]+)\|", post)
assert 5 <= len(used) <= 8, used
for img in used:
    assert os.path.exists(f"{REL}/blog/{img}"), img
for fn in os.listdir(f"{REL}/blog"):
    if fn.startswith("b_") and fn not in used:
        os.remove(f"{REL}/blog/{fn}")
for ln in post.splitlines():
    if "{{IMG|" in ln:
        assert ln.startswith("{{IMG|") and ln.endswith("}}"), ln
assert not re.search(r"\{\{(?!IMG\||DOI_URL\}\}|BLOG_URL\}\}|DOI\}\})", post)
vis = re.sub(r"<!--.*?-->", "", post, flags=re.S)
visible_text_ok(vis, "blog")
open(f"{REL}/blog/post.html", "w", encoding="utf-8").write(post)
words = len(re.sub(r"<[^>]+>|\{\{IMG\|[^}]*\}\}", " ", vis).split())
meta = {"title": "Roads of the Roman Empire: how many days from Rome to anywhere?",
        "slug": "roman-roads",
        "excerpt": f"Itiner-e, the new open map of Roman roads, holds {R['km_total']:,.0f} km of road. Only {R['cert']['Certain']['share_km'] * 100:.1f}% is certain. Walked in a model, London is {C['london']['foot']:.0f} days from Rome, Alexandria {C['alexandria']['foot']:.0f}, and by road alone Carthage is further than either.",
        "seo_description": "A map of every Roman road in Itiner-e, and a travel model of how many days it took to walk, ride or send a letter from Rome to anywhere.",
        "tags": ["Roman roads", "Roman Empire", "history", "maps", "data visualisation", "travel time", "Itiner-e", "archaeology"],
        "header_alt": f"Title card reading 'Roads of the Roman Empire' in black on cream, beside a map of the Mediterranean with every Roman road coloured by days on foot from Rome, from deep red in Italy through gold, green and teal to violet in North Africa. Text: {R['km_total']:,.0f} km of road; London {C['london']['foot']:.0f} days on foot, Constantinople {C['constantinople']['foot']:.0f}, Alexandria {C['alexandria']['foot']:.0f}."}
assert len(meta["seo_description"]) < 160, len(meta["seo_description"])
jsave(meta, f"{REL}/blog/meta.json", indent=2)

# ---------- Zenodo ----------
Zd = f"{REL}/zenodo"; os.makedirs(Zd, exist_ok=True)
for fn in os.listdir(Zd):
    os.remove(os.path.join(Zd, fn))
os.link(f"{REL}/paper/{NAME}.pdf", f"{Zd}/{NAME}.pdf")
zp = f"{Zd}/roman-roads_code_and_data.zip"
with zipfile.ZipFile(zp, "w", zipfile.ZIP_DEFLATED) as z:
    for d in ("code", "data"):
        for fn in sorted(os.listdir(os.path.join(ROOT, d))):
            if fn.endswith(".pyc") or fn == "__pycache__":
                continue
            z.write(os.path.join(ROOT, d, fn), f"roman-roads/{d}/{fn}")
    for fn in ("README.md", "LICENSE", "reddit/collage.py"):
        z.write(os.path.join(ROOT, fn), f"roman-roads/{fn}")
tex = open(f"{REL}/paper/{NAME}.tex", encoding="utf-8").read()
ab = re.search(r"\\begin\{center\}\\textbf\{Abstract\}\\end\{center\}\n(.*?)\n\n\\textbf\{Keywords", tex, re.S).group(1)
ab = ab.replace("\\%", "%").replace("\\&", "&").replace("\\emph{", "").replace("\\textsuperscript{2}", "²").replace("}", "")
zmeta = {"title": "Roads of the Roman Empire: Certainty, Density, Straight Runs and Days from Rome in the Itiner-e Network",
         "upload_type": "publication", "publication_type": "workingpaper",
         "description": f"<p>{ab}</p><p>Interactive version: <a href=\"{PAGE_URL}\">{PAGE_URL}</a>. Data and code: <a href=\"{REPO}\">{REPO}</a>. Blog post: {{https://blog.tristanhotham.com/2026/10/31/roman-roads/}}.</p>"
                        f"<p>Data: Itiner-e static version 2024 (de Soto, Pažout, Brughmans et al. 2025, https://doi.org/{ITINERE_DOI}), CC BY 4.0. Province outlines: Digital Atlas of the Roman Empire (DARE, Johan Åhlfeldt), CC BY. Travel speeds: English Wikipedia, 'Roman roads'. Land: Natural Earth (public domain). Derived data, figures and text: CC BY 4.0. Code: MIT.</p>",
         "creators": [{"name": "Hotham, Tristan", "affiliation": "Independent researcher", "orcid": "0000-0003-4931-9349"}],
         "keywords": ["Roman roads", "Roman Empire", "Itiner-e", "transport networks", "travel time", "network analysis", "historical GIS", "archaeology"],
         "license": "cc-by-4.0", "language": "eng",
         "related_identifiers": [{"identifier": REPO, "relation": "isSupplementedBy", "resource_type": "software"},
                                 {"identifier": PAGE_URL, "relation": "isSupplementedBy", "resource_type": "other"},
                                 {"identifier": f"https://doi.org/{ITINERE_DOI}", "relation": "isDerivedFrom", "resource_type": "dataset"},
                                 {"identifier": f"https://doi.org/{ITINERE_PAPER_DOI}", "relation": "references", "resource_type": "publication-article"},
                                 {"identifier": "https://www.naturalearthdata.com/", "relation": "isDerivedFrom", "resource_type": "dataset"}],
         "notes": AI}
s = _json.dumps(zmeta, ensure_ascii=False) + _json.dumps(meta, ensure_ascii=False)
visible_text_ok(s, "meta")
jsave(zmeta, f"{Zd}/metadata.json", indent=2)

# ---------- Reddit post ----------
pm = f"""## Title

[OC] How many days on foot from Rome? Every road in the new open map of the Roman Empire ({R['km_total']:,.0f} km), coloured by modelled walking time. London {C['london']['foot']:.0f} days, Alexandria {C['alexandria']['foot']:.0f}, and by road alone Carthage {C['carthago']['foot']:.0f}

## Body

Itiner-e (2025) is the most detailed open dataset of Roman roads yet: {R['n_sections']:,} sections, {R['km_total']:,.0f} km. I turned it into a network of {R['n_nodes']:,} junctions and ran a shortest-path search from the Forum, at {MODES['foot']['kmd']} km a day on foot (Wikipedia gives 20 to 25), {MODES['cart']['kmd']:.0f} by cart and {MODES['courier']['kmd']:.0f} by courier, slowed on steep sections using the dataset's own passability field, with one day for each short sea crossing (Channel, Messina, Otranto, Gibraltar). London: {C['london']['foot']:.0f} days on foot, {C['london']['courier']:.0f} by courier. Constantinople: {C['constantinople']['foot']:.0f}. Alexandria: {C['alexandria']['foot']:.0f}, because by road you go round the whole eastern Mediterranean. Carthage, {C['carthago']['straight_km']:,.0f} km from Rome, is {C['carthago']['foot']:.0f} days by road via Spain and Gibraltar, which is why everyone took a ship. Caveats: these are modelled times (no rests, seasons, rivers or sea routes), and only {R['cert']['Certain']['share_km'] * 100:.1f}% of the network is mapped as certain; {R['cert']['Conjectured']['share_km'] * 100:.0f}% is conjectured. Interactive map where you can start from any city and click anywhere: {PAGE_URL}

## Source comment

Source: Itiner-e static version 2024, de Soto, Pažout, Brughmans et al. (2025), Zenodo doi:10.5281/zenodo.17122148, described in Scientific Data doi:10.1038/s41597-025-06140-z, CC BY 4.0 (roads, certainty, dates, slope, passability). Speeds: English Wikipedia, 'Roman roads' (middle of each range). Land: Natural Earth (public domain).

Tools: Python (geopandas, scipy, shapely, pyproj, matplotlib); Leaflet for the interactive map. Derived data and figures: CC BY 4.0.

Interactive version: {PAGE_URL}
Paper: {{https://doi.org/10.5281/zenodo.23857866}}
Blog post: {{https://blog.tristanhotham.com/2026/10/31/roman-roads/}}
"""
visible_text_ok(pm, "post")
open(os.path.join(ROOT, "reddit", "post.md"), "w", encoding="utf-8").write(pm)
print("blog words", words, "; figures", len(used), "; zenodo", sorted(os.listdir(Zd)), os.path.getsize(zp) // 1024, "KB zip")
