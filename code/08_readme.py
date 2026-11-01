"""Step 8. README.md and LICENSE, numbers from data/results.json.
Run: python3 code/08_readme.py
"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import *

R = jload(f"{DATA}/results.json"); C = R["city"]
kb = lambda f: f"{os.path.getsize(os.path.join(DATA, f)) // 1024:,} KB"
p0 = R["provinces"][0]
readme = f"""# Roads of the Roman Empire

Every road in Itiner-e, the new open map of the roads of the Roman Empire ({R['km_total']:,.0f} km in {R['n_sections']:,} sections): how much of it is certain, when it was built, where it runs straightest and densest, and a travel-time model of how many days it took to reach anywhere from Rome on foot, by cart or by courier.

Interactive page: https://maps.tristanhotham.com/roman-roads/
Paper: https://doi.org/{{10.5281/zenodo.23857866}}
Blog post: {{https://blog.tristanhotham.com/2026/10/31/roman-roads/}}

## Headline results

- Size: {R['km_total']:,.0f} km of road, {R['km_main']:,.0f} km main ({R['share_main'] * 100:.0f}%) and {R['km_secondary']:,.0f} km secondary; {R['n_nodes']:,} junctions.
- Certainty: only {R['cert']['Certain']['km']:,.0f} km ({R['cert']['Certain']['share_km'] * 100:.1f}%) is graded certain; {R['cert']['Conjectured']['share_km'] * 100:.0f}% is conjectured and {R['cert']['Hypothetical']['share_km'] * 100:.1f}% hypothetical. {R['dated']['share_km'] * 100:.0f}% of the length has a date or builder; Claudius is named for the most ({R['builders'][0]['km']:,.0f} km).
- Days from Rome (modelled): London {C['london']['foot']:.0f} days on foot ({C['london']['foot_lo']:.0f} to {C['london']['foot_hi']:.0f}), {C['london']['cart']:.0f} by cart, {C['london']['courier']:.0f} by courier; Constantinople {C['constantinople']['foot']:.0f} on foot; Alexandria {C['alexandria']['foot']:.0f}, round the eastern Mediterranean ({C['alexandria']['road_km']:,.0f} km of road). By road alone Carthage ({C['carthago']['straight_km']:,.0f} km away) is {C['carthago']['foot']:.0f} days, via Spain and Gibraltar.
- Straight runs: the longest stretch within 200 m of a straight line is {R['runs'][0]['km']:.1f} km between Saint-Quentin and Amiens; the longest on certain sections is the Via Appia across the Pontine plain ({R['runs'][2]['km']:.1f} km).
- Density: highest in {p0['name']} ({p0['density']:.0f} km per 1,000 km²) and outside Italy in Cyprus, Judaea and Lycia et Pamphylia; the average over all provinces is {R['empire_density']:.0f}.

## Files

| File | What it is |
|---|---|
| `index.html` | The interactive page (built by `code/05_build_site.py`); loads `data/network.json`, `data/roads_site.json`, `data/places.json`, `data/grid_edge.png`, `data/grid_dist.png` and, on demand, `data/provinces.geojson`. |
| `header.png` | Social card, 1200 x 630. |
| `data/roads.csv` | {R['n_sections']:,} road sections: name, type, certainty, dates and the date used, construction period, itinerary, description, digitiser, bibliography, km, slope, passability, end junctions, province (about AD 117) and modelled days from Rome on foot, by cart and by courier ({kb('roads.csv')}). |
| `data/roads.geojson.gz` | The same sections as lines, simplified to about 50 m (gzipped GeoJSON; uncompressed in the Zenodo zip). |
| `data/nodes.csv` | {R['n_nodes']:,} junctions with inferred names. |
| `data/travel_from_rome.csv` | Modelled days from Rome to every junction, three ways to travel. |
| `data/provinces.csv`, `data/provinces.geojson` | Road length, land area, density and share certain by province (outlines from DARE, simplified). |
| `data/straight_runs.csv` | Every straight run of 15 km or more, with its end points, length, largest deviation and share certain. |
| `data/named_roads.csv` | Road length by named road (Via Egnatia, Via Appia, Fosse Way...). |
| `data/network.json`, `data/roads_site.json`, `data/places.json`, `data/grid_*.png` | Page data: the graph, compact road lines, modern place names and a lookup grid for the days shading. |
| `data/results.json` | Every number used in the page, paper, blog and collage. |
| `code/` | Scripts, run in order (below), and the page, paper and blog templates. |
| `release/` | Paper PDF and LaTeX source, blog figures and post, Zenodo files. |
| `reddit/` | Collage (`collage.py`, PNG) and post text. |

## Method in brief

- Network: section ends within 1 m are one junction. Junctions are named by the place shared by the sections meeting there, else the nearest DARE place.
- Travel time on a section = km / (speed x passability). Speeds: middle of Wikipedia's ranges, {MODES['foot']['kmd']} km a day on foot, {MODES['cart']['kmd']:.0f} by cart, {MODES['courier']['kmd']:.0f} by courier. Passability is Itiner-e's own field; it matches Tobler's hiking function exp(-3.5 tan slope) for average slopes above about {R['pass']['slope_threshold']:.1f} degrees (median difference {R['pass']['median_absdiff_r']}). Sea crossings (Channel, Messina, Otranto, Gibraltar): one day each; Euripus bridge as road; Bosporus and Hellespont ferries are in the data. Off the network: the last stretch at half speed, up to {OFFROAD_MAX_KM} km. Dijkstra from the Forum.
- Straight runs: sections joined through junctions where the road continues within 20 degrees, Douglas-Peucker at 200 m in a local equidistant projection; hypothetical and straight-line-conjecture sections excluded, and sparsely drawn conjectured stretches dropped.
- Density: road per 1,000 km² of land in DARE's provinces of about AD 117 (Italy as its eleven regions).
- Caveats: most roads are conjectured and few are dated, so this is a composite network of about 300 BCE to 300 CE; coverage reflects research effort; travel times are modelled (no rests, seasons, rivers or sea routes).

## How to rerun

Needs Python 3 with numpy, pandas, geopandas, shapely, pyproj, scipy, rasterio, matplotlib, fontTools and Pillow; xelatex, pdfinfo and pdftotext; Playwright with Chromium for the QA step. Raw inputs are read in place (paths in `code/common.py`): `itinere_roads.gpkg`, the field description and Zenodo record of Itiner-e static version 2024 (https://doi.org/{ITINERE_DOI}), the Wikipedia page 'Roman roads', Natural Earth land, countries and populated places, and a clone of https://github.com/klokantech/roman-empire (DARE provinces and places). Intermediate files go to `/home/claude/work/roman-roads` (set `ROMAN_WORK` to change).

```
python3 code/01_network.py      # sections, junctions, crossings
python3 code/02_travel.py       # travel times, page graph and lookup grid
python3 code/03_analysis.py     # certainty, dates, straight runs, provinces
python3 code/04_results.py      # results.json and page data
python3 code/05_build_site.py   # index.html
python3 code/06_figures.py      # header, blog and paper figures
python3 code/07_paper.py        # paper PDF
python3 code/08_readme.py       # README and LICENSE
python3 code/09_release.py      # blog post, Zenodo files, Reddit post
python3 reddit/collage.py       # collage
python3 code/10_qa.py           # screenshots and checks
```

## Sources and licences

- de Soto, P., Pažout, A., Brughmans, T. et al. (2025) A high-resolution dataset of roads of the Roman Empire: Itiner-e static version 2024. Zenodo, https://doi.org/{ITINERE_DOI}. Described in Scientific Data, https://doi.org/{ITINERE_PAPER_DOI}. CC BY 4.0.
- Digital Atlas of the Roman Empire (DARE), Johan Åhlfeldt, CC BY: province outlines of about AD 117 and ancient place names, via https://github.com/klokantech/roman-empire.
- English Wikipedia, 'Roman roads' (revision {R['wiki']['revid']}): travel speeds and the 400,000 km estimate. CC BY-SA 4.0.
- Natural Earth (public domain): land, countries, modern place names.
- Base map tiles on the page: © Esri.
- ORBIS (Scheidel and Meeks, orbis.stanford.edu) is mentioned for comparison only; none of its data is used.

## Citation

Hotham, T. (2026) Roads of the Roman Empire: certainty, density, straight runs and days from Rome in the Itiner-e network. Zenodo. https://doi.org/{{10.5281/zenodo.23857866}}

Dr Tristan Hotham, Independent researcher. ORCID 0000-0003-4931-9349.

{AI}
"""
visible_text_ok(readme.replace("|---|---|", ""), "readme")
open(os.path.join(ROOT, "README.md"), "w", encoding="utf-8").write(readme)
lic = open("/home/claude/studies/submarine-cables/LICENSE", encoding="utf-8").read().split("This MIT licence covers")[0]
lic += """This MIT licence covers the code in code/ and reddit/collage.py and the page
scripts only.

The data in data/, the figures (header.png, release/blog/, release/paper/,
reddit/), the collage and the text of the page, paper and blog post are shared
under Creative Commons Attribution 4.0 (CC BY 4.0,
https://creativecommons.org/licenses/by/4.0/). They are derived from Itiner-e
static version 2024 (de Soto, Pazout, Brughmans et al. 2025,
https://doi.org/10.5281/zenodo.17122148), itself CC BY 4.0: please credit both.
Province outlines are from the Digital Atlas of the Roman Empire (DARE, Johan
Ahlfeldt); land and place names from Natural Earth (public domain).
"""
open(os.path.join(ROOT, "LICENSE"), "w", encoding="utf-8").write(lic)
print("README and LICENSE written")
