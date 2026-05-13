"""
OSM Road Quality Analyzer
=========================
Portfolio Project by Tahira Ullah · Geoinformatikerin

Analysiert die Attributvollständigkeit des OpenStreetMap-Straßennetzes
für eine beliebige Stadt und berechnet einen Qualitätsscore pro Segment.

Verwendete Technologien:
    - osmnx      → OSM-Datenabfrage & Graphverarbeitung
    - geopandas  → Geodatenverarbeitung
    - pandas     → Tabellarische Analyse
    - folium     → Interaktive Karte
    - PostGIS    → (optional) Persistenz & räumliche Abfragen

Referenz: Ullah et al. (2023) – Assessing Completeness of OSM Building
Footprints Using MapSwipe. ISPRS Int. J. Geo-Information, 12(4), 143.
https://doi.org/10.3390/ijgi12040143

Usage:
    python osm_road_quality_analyzer.py --city "Frankfurt am Main, Germany"
    python osm_road_quality_analyzer.py --city "Berlin, Germany" --output berlin_quality.html
"""

import argparse
import json
from pathlib import Path

import folium
import geopandas as gpd
import osmnx as ox
import pandas as pd


# ---------------------------------------------------------------------------
# Konfiguration
# ---------------------------------------------------------------------------

QUALITY_ATTRIBUTES = [
    "name",        # Straßenname vorhanden?
    "maxspeed",    # Geschwindigkeitsbeschränkung vorhanden?
    "surface",     # Oberflächentyp vorhanden?
    "lit",         # Beleuchtungsinfo vorhanden?
    "lanes",       # Anzahl Fahrspuren vorhanden?
]

COLOR_MAP = {
    "good":     "#2ecc71",  # ≥ 80 %  — green
    "medium":   "#f1c40f",  # 60–79 % — yellow
    "weak":     "#e67e22",  # 40–59 % — orange
    "critical": "#e74c3c",  # < 40 %  — red
}


# ---------------------------------------------------------------------------
# Daten laden
# ---------------------------------------------------------------------------

def load_street_network(city: str) -> gpd.GeoDataFrame:
    """Lädt das Fahrstraßennetz via OSM Overpass API."""
    print(f"[1/4] Lade Straßennetz für: {city}")
    G = ox.graph_from_place(city, network_type="drive")
    edges = ox.graph_to_gdfs(G, nodes=False)
    print(f"      → {len(edges):,} Straßensegmente geladen")
    return edges


# ---------------------------------------------------------------------------
# Qualitätsanalyse
# ---------------------------------------------------------------------------

def compute_quality_scores(gdf: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
    """
    Berechnet einen Qualitätsscore (0–100) pro Segment basierend auf der
    Attributvollständigkeit der konfigurierten QUALITY_ATTRIBUTES.

    Score-Formel:
        score = (Anzahl vorhandener Attribute / Gesamtanzahl Attribute) × 100
    """
    print("[2/4] Berechne Qualitätsscores …")

    for attr in QUALITY_ATTRIBUTES:
        col = f"has_{attr}"
        if attr in gdf.columns:
            gdf[col] = gdf[attr].notna().astype(int)
        else:
            gdf[col] = 0  # Attribut komplett fehlend → maximale Lücke

    score_cols = [f"has_{a}" for a in QUALITY_ATTRIBUTES]
    gdf["quality_score"] = (
        gdf[score_cols].sum(axis=1) / len(QUALITY_ATTRIBUTES) * 100
    ).round(1)

    gdf["quality_class"] = gdf["quality_score"].apply(_classify_score)
    gdf["color"] = gdf["quality_class"].map(COLOR_MAP)

    return gdf


def _classify_score(score: float) -> str:
    if score >= 80:
        return "good"
    elif score >= 60:
        return "medium"
    elif score >= 40:
        return "weak"
    return "critical"


# ---------------------------------------------------------------------------
# Statistiken
# ---------------------------------------------------------------------------

def print_summary(gdf: gpd.GeoDataFrame) -> dict:
    """Gibt eine Übersichtstabelle aus und gibt ein Dict zurück."""
    print("\n[3/4] Qualitätszusammenfassung")
    print("=" * 45)
    print(f"  Segmente gesamt : {len(gdf):,}")
    print(f"  Ø Qualitätsscore: {gdf['quality_score'].mean():.1f} %\n")

    print("  Attribut-Vollständigkeit:")
    completeness = {}
    for attr in QUALITY_ATTRIBUTES:
        col = f"has_{attr}"
        pct = gdf[col].mean() * 100
        completeness[attr] = round(pct, 1)
        bar = "█" * int(pct / 5) + "░" * (20 - int(pct / 5))
        print(f"    {attr:<12} {bar}  {pct:.1f}%")

    print("\n  Qualitätsklassen:")
    for cls, color in COLOR_MAP.items():
        n = (gdf["quality_class"] == cls).sum()
        pct = n / len(gdf) * 100
        print(f"    {cls:<10} {n:>5} Segmente  ({pct:.1f}%)")

    return {
        "total": len(gdf),
        "avg_score": round(gdf["quality_score"].mean(), 1),
        "completeness": completeness,
        "class_counts": gdf["quality_class"].value_counts().to_dict(),
    }


# ---------------------------------------------------------------------------
# Visualisierung
# ---------------------------------------------------------------------------

def create_map(gdf: gpd.GeoDataFrame, output_path: str = "road_quality.html") -> None:
    """Erstellt eine interaktive Folium-Karte mit farbkodiertem Straßennetz."""
    print("[4/4] Erstelle interaktive Karte …")

    gdf_proj = gdf.to_crs("EPSG:25832")
    centroids = gdf_proj.geometry.centroid.to_crs("EPSG:4326")
    center = [centroids.y.mean(), centroids.x.mean()]
    m = folium.Map(
        location=center,
        zoom_start=13,
        tiles="CartoDB dark_matter",
    )

    # Straßen als PolyLine zeichnen — Click-Highlight über GeoJson + onEachFeature
    features = []
    for _, row in gdf.iterrows():
        coords = [[x, y] for x, y in row.geometry.coords]  # GeoJSON: [lon, lat]
        features.append({
            "type": "Feature",
            "geometry": {"type": "LineString", "coordinates": coords},
            "properties": {
                "color":      row["color"],
                "tooltip":    _build_tooltip(row),
                "highway":    _safe_val(row, "highway"),
                "score":      float(row["quality_score"]),
            }
        })

    geojson_data = {"type": "FeatureCollection", "features": features}

    folium.GeoJson(
        geojson_data,
        style_function=lambda feature: {
            "color":   feature["properties"]["color"],
            "weight":  3,
            "opacity": 0.85,
        },
        highlight_function=lambda feature: {
            "color":  "#3498db",
            "weight": 6,
            "opacity": 1.0,
        },
        tooltip=folium.GeoJsonTooltip(
            fields=["tooltip"],
            aliases=[""],
            style="background:#111;color:#eee;font-family:monospace;font-size:12px;border:1px solid #333;",
            localize=True,
        ),
    ).add_to(m)

    # Legende
    legend_html = _build_legend()
    m.get_root().html.add_child(folium.Element(legend_html))

    m.save(output_path)
    print(f"      → Karte gespeichert: {output_path}")


def _safe_val(row, key: str) -> str:
    """Liest einen OSM-Attributwert sicher aus — OSM kann Listen zurückgeben."""
    val = row.get(key, None)
    if val is None:
        return "✗"
    if isinstance(val, (list, tuple)):
        val = val[0] if len(val) > 0 else None
    try:
        if pd.isna(val):
            return "✗"
    except (TypeError, ValueError):
        pass
    return str(val)


def _build_tooltip(row) -> str:
    """HTML-Tooltip für ein Straßensegment."""
    name = _safe_val(row, "name")
    if name == "✗":
        name = "—"
    lines = [
        f"<b style='color:{row.color}'>{name}</b>",
        f"<hr style='margin:4px 0;border-color:#333'>",
        f"Typ: {_safe_val(row, 'highway')}",
        f"Score: <b>{row.quality_score:.0f}%</b>",
        f"maxspeed: {_safe_val(row, 'maxspeed')}",
        f"surface: {_safe_val(row, 'surface')}",
        f"lit: {_safe_val(row, 'lit')}",
        f"lanes: {_safe_val(row, 'lanes')}",
    ]
    return "<br>".join(lines)


def _build_legend() -> str:
    return """
    <div style="
        position: fixed; bottom: 40px; right: 20px; z-index: 9999;
        background: rgba(15,17,23,0.92); border: 1px solid #1e2330;
        padding: 14px 18px; border-radius: 6px; font-family: monospace;
        font-size: 12px; color: #e8eaf0;
    ">
        <b style="color:#00e5a0;font-size:13px;">Quality Classes</b><br><br>
        <span style="color:#2ecc71">■</span>&nbsp; Good (≥ 80 %)<br>
        <span style="color:#f1c40f">■</span>&nbsp; Medium (60–79 %)<br>
        <span style="color:#e67e22">■</span>&nbsp; Weak (40–59 %)<br>
        <span style="color:#e74c3c">■</span>&nbsp; Critical (&lt; 40 %)<br>
        <br><span style="color:#6b7280;">© OpenStreetMap contributors</span>
    </div>
    """


# ---------------------------------------------------------------------------
# Optional: PostGIS Export
# ---------------------------------------------------------------------------

def export_to_postgis(gdf: gpd.GeoDataFrame, conn_string: str, table: str = "road_quality") -> None:
    """
    Exportiert die analysierten Daten in eine PostGIS-Datenbank.

    Beispiel conn_string:
        "postgresql://user:password@localhost:5432/osmdb"

    Nützliche Folgeabfragen in PostGIS:
        -- Straßen mit kritischer Qualität nahe Schulen
        SELECT r.name, r.quality_score
        FROM road_quality r, schools s
        WHERE ST_DWithin(r.geom::geography, s.geom::geography, 200)
          AND r.quality_class = 'critical'
        ORDER BY r.quality_score;

        -- Heatmap-Aggregation auf 500m-Raster
        SELECT ST_SnapToGrid(geom, 0.005) AS cell,
               AVG(quality_score) AS avg_score,
               COUNT(*) AS n_segments
        FROM road_quality
        GROUP BY cell;
    """
    from sqlalchemy import create_engine
    engine = create_engine(conn_string)
    export_cols = ["geometry", "osmid", "highway", "name",
                   "quality_score", "quality_class"] + QUALITY_ATTRIBUTES
    export_cols = [c for c in export_cols if c in gdf.columns]
    gdf[export_cols].to_postgis(table, engine, if_exists="replace", index=False)
    print(f"PostGIS: Tabelle '{table}' erfolgreich geschrieben.")


# ---------------------------------------------------------------------------
# Hauptprogramm
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description="OSM Road Quality Analyzer")
    parser.add_argument("--city", default="Frankfurt am Main-Innenstadt, Frankfurt, Germany",
                        help="Stadt / Ortsname für OSM-Abfrage")
    parser.add_argument("--output", default="road_quality.html",
                        help="Ausgabepfad für die HTML-Karte")
    parser.add_argument("--export-json", action="store_true",
                        help="Zusätzlich GeoJSON exportieren")
    args = parser.parse_args()

    # Pipeline
    gdf = load_street_network(args.city)
    gdf = compute_quality_scores(gdf)
    summary = print_summary(gdf)
    create_map(gdf, args.output)

    if args.export_json:
        json_path = Path(args.output).stem + "_summary.json"
        with open(json_path, "w") as f:
            json.dump(summary, f, indent=2)
        print(f"JSON-Zusammenfassung: {json_path}")

    print("\n✓ Analyse abgeschlossen.")


if __name__ == "__main__":
    main()
