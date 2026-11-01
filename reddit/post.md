## Title

[OC] How many days on foot from Rome? Every road in the new open map of the Roman Empire (299,171 km), coloured by modelled walking time. London 81 days, Alexandria 180, and by road alone Carthage 210

## Body

Itiner-e (2025) is the most detailed open dataset of Roman roads yet: 14,769 sections, 299,171 km. I turned it into a network of 10,315 junctions and ran a shortest-path search from the Forum, at 22.5 km a day on foot (Wikipedia gives 20 to 25), 45 by cart and 80 by courier, slowed on steep sections using the dataset's own passability field, with one day for each short sea crossing (Channel, Messina, Otranto, Gibraltar). London: 81 days on foot, 23 by courier. Constantinople: 75. Alexandria: 180, because by road you go round the whole eastern Mediterranean. Carthage, 590 km from Rome, is 210 days by road via Spain and Gibraltar, which is why everyone took a ship. Caveats: these are modelled times (no rests, seasons, rivers or sea routes), and only 2.7% of the network is mapped as certain; 90% is conjectured. Interactive map where you can start from any city and click anywhere: https://maps.tristanhotham.com/roman-roads/

## Source comment

Source: Itiner-e static version 2024, de Soto, Pažout, Brughmans et al. (2025), Zenodo doi:10.5281/zenodo.17122148, described in Scientific Data doi:10.1038/s41597-025-06140-z, CC BY 4.0 (roads, certainty, dates, slope, passability). Speeds: English Wikipedia, 'Roman roads' (middle of each range). Land: Natural Earth (public domain).

Tools: Python (geopandas, scipy, shapely, pyproj, matplotlib); Leaflet for the interactive map. Derived data and figures: CC BY 4.0.

Interactive version: https://maps.tristanhotham.com/roman-roads/
Paper: {https://doi.org/10.5281/zenodo.23857866}
Blog post: {https://blog.tristanhotham.com/2026/10/31/roman-roads/}
