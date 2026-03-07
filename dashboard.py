"""
dashboard.py
------------
Streamlit dashboard for the Cadastral Data Quality Control system.
Supports two modes:
  1. Load results from existing CSV reports
  2. Run full validation pipeline in real time
"""

import streamlit as st
import pandas as pd
import geopandas as gpd
import plotly.graph_objects as go
import plotly.express as px
import os
import sys

sys.path.append(os.path.dirname(__file__))

# ---------------------------------------------------
# PAGE CONFIG
# ---------------------------------------------------

st.set_page_config(
    page_title="Cadastral QA/QC Dashboard",
    page_icon="🗺️",
    layout="wide",
)

# ---------------------------------------------------
# STYLES
# ---------------------------------------------------

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@400;600&family=IBM+Plex+Sans:wght@300;400;600&display=swap');

html, body, [class*="css"] {
    font-family: 'IBM Plex Sans', sans-serif;
    background-color: #0d0f14;
    color: #e2e8f0;
}

.main { background-color: #0d0f14; }
.block-container { padding: 2rem 2.5rem; }

/* Header */
.dash-header {
    border-left: 4px solid #f59e0b;
    padding: 0.5rem 0 0.5rem 1.2rem;
    margin-bottom: 2rem;
}
.dash-header h1 {
    font-family: 'IBM Plex Mono', monospace;
    font-size: 1.6rem;
    font-weight: 600;
    color: #f8fafc;
    margin: 0;
    letter-spacing: -0.5px;
}
.dash-header p {
    font-size: 0.85rem;
    color: #94a3b8;
    margin: 0.2rem 0 0 0;
    font-family: 'IBM Plex Mono', monospace;
}

/* KPI cards */
.kpi-grid { display: grid; grid-template-columns: repeat(4, 1fr); gap: 1rem; margin-bottom: 2rem; }
.kpi-card {
    background: #151820;
    border: 1px solid #1e2433;
    border-radius: 8px;
    padding: 1.2rem 1.4rem;
    position: relative;
    overflow: hidden;
}
.kpi-card::before {
    content: '';
    position: absolute;
    top: 0; left: 0; right: 0;
    height: 3px;
}
.kpi-card.grave::before  { background: #ef4444; }
.kpi-card.moderado::before { background: #f59e0b; }
.kpi-card.leve::before   { background: #22c55e; }
.kpi-card.total::before  { background: #3b82f6; }

.kpi-label {
    font-family: 'IBM Plex Mono', monospace;
    font-size: 0.7rem;
    color: #64748b;
    text-transform: uppercase;
    letter-spacing: 1px;
    margin-bottom: 0.5rem;
}
.kpi-value {
    font-family: 'IBM Plex Mono', monospace;
    font-size: 2rem;
    font-weight: 600;
    color: #f8fafc;
    line-height: 1;
}
.kpi-card.grave .kpi-value  { color: #ef4444; }
.kpi-card.moderado .kpi-value { color: #f59e0b; }
.kpi-card.leve .kpi-value   { color: #22c55e; }
.kpi-card.total .kpi-value  { color: #3b82f6; }

/* Section headers */
.section-title {
    font-family: 'IBM Plex Mono', monospace;
    font-size: 0.75rem;
    color: #f59e0b;
    text-transform: uppercase;
    letter-spacing: 2px;
    margin: 2rem 0 1rem 0;
    padding-bottom: 0.5rem;
    border-bottom: 1px solid #1e2433;
}

/* Severity badges */
.badge {
    display: inline-block;
    padding: 2px 8px;
    border-radius: 4px;
    font-size: 0.72rem;
    font-family: 'IBM Plex Mono', monospace;
    font-weight: 600;
}
.badge-grave    { background: #3f0f0f; color: #ef4444; border: 1px solid #7f1d1d; }
.badge-moderado { background: #3f2a0f; color: #f59e0b; border: 1px solid #78350f; }
.badge-leve     { background: #0f2f1a; color: #22c55e; border: 1px solid #14532d; }
.badge-none     { background: #1e2433; color: #64748b; border: 1px solid #334155; }

/* Sidebar */
section[data-testid="stSidebar"] {
    background-color: #0a0c10 !important;
    border-right: 1px solid #1e2433;
}
section[data-testid="stSidebar"] * { color: #cbd5e1 !important; }

/* Table */
.stDataFrame { border: 1px solid #1e2433; border-radius: 8px; overflow: hidden; }

/* Info box */
.info-box {
    background: #151820;
    border: 1px solid #1e2433;
    border-left: 3px solid #3b82f6;
    border-radius: 6px;
    padding: 0.8rem 1rem;
    font-size: 0.83rem;
    color: #94a3b8;
    margin: 0.5rem 0 1.5rem 0;
}

/* Warning box */
.warn-box {
    background: #1a1400;
    border: 1px solid #78350f;
    border-left: 3px solid #f59e0b;
    border-radius: 6px;
    padding: 0.8rem 1rem;
    font-size: 0.83rem;
    color: #fcd34d;
    margin: 0.5rem 0 1.5rem 0;
}
</style>
""", unsafe_allow_html=True)

# ---------------------------------------------------
# CHART THEME
# ---------------------------------------------------

CHART_THEME = dict(
    template="plotly_dark",
    paper_bgcolor="#151820",
    plot_bgcolor="#151820",
    font_family="IBM Plex Mono",
    font_color="#94a3b8",
)

SEVERITY_COLORS = {
    "critical":    "#ef4444",
    "moderate": "#f59e0b",
    "low":     "#22c55e",
    "none":     "#334155",
}

CATEGORY_COLORS = {
    "geometry":             "#3b82f6",
    "duplicate":            "#8b5cf6",
    "overlap":              "#f59e0b",
    "hierarchy":            "#ec4899",
    "attribute":            "#06b6d4",
    "referential_integrity":"#ef4444",
}

# ---------------------------------------------------
# HELPERS
# ---------------------------------------------------

@st.cache_data
def load_csv_reports(detail_path: str, summary_path: str):
    df_detail  = pd.read_csv(detail_path)
    df_summary = pd.read_csv(summary_path)
    return df_detail, df_summary


def run_validation_pipeline():
    """Run full validation and return detail + summary DataFrames."""
    from validation_engine.geometry_validator import validate_geometry, summarize_geometry_errors
    from validation_engine.overlap_validator import validate_overlaps
    from validation_engine.hierarchy_validator import validate_within_percentage
    from validation_engine.unit_validator import validate_unit_overlaps_by_construction
    from validation_engine.attribute_validator import validate_attributes, validate_referential_integrity
    from validation_engine.duplicate_validator import validate_duplicates
    from validation_engine.report_builder import ReportBuilder

    GPKG_PATH = "input_data/urban_ctm12_anonymized.gpkg"
    PROJECT_STAGE = st.session_state.get("project_stage", "initial")
    THRESHOLDS = {"initial": 0.10, "preliminary": 0.02, "final": 0.0001}
    OVERLAP_THRESHOLD = THRESHOLDS.get(PROJECT_STAGE, 0.10)
    LAYERS = ["U_TERRENO_CTM12", "U_CONSTRUCCION_CTM12", "U_UNIDAD_CTM12", "U_MANZANA_CTM12"]

    builder = ReportBuilder(project_stage=PROJECT_STAGE, overlap_threshold=OVERLAP_THRESHOLD)
    progress = st.progress(0, text="Loading layers...")
    data = {}
    for i, layer in enumerate(LAYERS):
        data[layer] = gpd.read_file(GPKG_PATH, layer=layer)
        progress.progress((i + 1) / (len(LAYERS) * 6), text=f"Loaded {layer}")

    step = len(LAYERS)
    total_steps = len(LAYERS) * 6

    # Geometry
    for i, layer in enumerate(LAYERS):
        progress.progress((step + i) / total_steps, text=f"Geometry: {layer}")
        result = validate_geometry(data[layer], layer)
        builder.add_geometry(layer, summarize_geometry_errors(result))
    step += len(LAYERS)

    # Duplicates
    for i, layer in enumerate(LAYERS):
        progress.progress((step + i) / total_steps, text=f"Duplicates: {layer}")
        result = validate_duplicates(data[layer], layer)
        builder.add_duplicates(layer, result)
    step += len(LAYERS)

    # Overlaps
    for i, layer in enumerate(LAYERS):
        progress.progress((step + i) / total_steps, text=f"Overlaps: {layer}")
        if layer == "U_UNIDAD_CTM12":
            result = validate_unit_overlaps_by_construction(data[layer], min_area=OVERLAP_THRESHOLD)
        else:
            result = validate_overlaps(data[layer], layer, min_area=OVERLAP_THRESHOLD)
        builder.add_overlaps(layer, result)
    step += len(LAYERS)

    # Hierarchy
    hierarchy_checks = [
        (data["U_UNIDAD_CTM12"], data["U_CONSTRUCCION_CTM12"],
         "CONSTRUCCION_CODIGO", "CODIGO", "U_UNIDAD_CTM12", "U_CONSTRUCCION_CTM12",
         "unidad_fuera_construccion_pct"),
        (data["U_CONSTRUCCION_CTM12"], data["U_TERRENO_CTM12"],
         "TERRENO_CODIGO", "CODIGO", "U_CONSTRUCCION_CTM12", "U_TERRENO_CTM12",
         "construccion_fuera_terreno_pct"),
        (data["U_TERRENO_CTM12"], data["U_MANZANA_CTM12"],
         "MANZANA_CODIGO", "CODIGO", "U_TERRENO_CTM12", "U_MANZANA_CTM12",
         "terreno_fuera_manzana_pct"),
    ]
    for i, (child, parent, cf, pf, cn, pn, name) in enumerate(hierarchy_checks):
        progress.progress((step + i) / total_steps, text=f"Hierarchy: {name}")
        result = validate_within_percentage(child, parent, cf, pf, cn, pn)
        builder.add_hierarchy(name, result)
    step += 3

    # Attributes
    for i, layer in enumerate(LAYERS):
        progress.progress((step + i) / total_steps, text=f"Attributes: {layer}")
        results = validate_attributes(data[layer], layer)
        builder.add_attributes(layer, results)
    step += len(LAYERS)

    # Referential integrity
    ref_checks = [
        (data["U_CONSTRUCCION_CTM12"], data["U_TERRENO_CTM12"],
         "TERRENO_CODIGO", "CODIGO", "U_CONSTRUCCION_CTM12", "U_TERRENO_CTM12",
         "ref_construccion_sin_terreno"),
        (data["U_UNIDAD_CTM12"], data["U_CONSTRUCCION_CTM12"],
         "CONSTRUCCION_CODIGO", "CODIGO", "U_UNIDAD_CTM12", "U_CONSTRUCCION_CTM12",
         "ref_unidad_sin_construccion"),
        (data["U_UNIDAD_CTM12"], data["U_TERRENO_CTM12"],
         "TERRENO_CODIGO", "CODIGO", "U_UNIDAD_CTM12", "U_TERRENO_CTM12",
         "ref_unidad_sin_terreno"),
        (data["U_TERRENO_CTM12"], data["U_MANZANA_CTM12"],
         "MANZANA_CODIGO", "CODIGO", "U_TERRENO_CTM12", "U_MANZANA_CTM12",
         "ref_terreno_sin_manzana"),
    ]
    for i, (child, parent, cf, pf, cn, pn, name) in enumerate(ref_checks):
        progress.progress((step + i) / total_steps, text=f"Referential: {name}")
        result = validate_referential_integrity(child, parent, cf, pf, cn, pn)
        builder.add_referential(name, result)

    progress.progress(1.0, text="Validation complete.")
    return builder.build()


def severity_badge(sev: str) -> str:
    return f'<span class="badge badge-{sev}">{sev.upper()}</span>'


# ---------------------------------------------------
# SIDEBAR
# ---------------------------------------------------

with st.sidebar:
    st.markdown("### ⚙️ Configuration")

    data_source = st.radio(
        "Data Source",
        ["Load existing reports", "Run validation now"],
        index=0,
    )

    st.markdown("---")
    project_stage = st.selectbox(
        "Project Stage",
        ["initial", "preliminary", "final"],
        index=0,
    )
    st.session_state["project_stage"] = project_stage

    st.markdown("---")
    st.markdown("### 🔍 Filters")
    selected_categories = st.multiselect(
        "Validation Categories",
        ["geometry", "duplicate", "overlap", "hierarchy", "attribute", "referential_integrity"],
        default=["geometry", "duplicate", "overlap", "hierarchy", "attribute", "referential_integrity"],
    )
    show_zero = st.checkbox("Show checks with 0 errors", value=False)

    st.markdown("---")
    st.markdown(
        "<div style='font-size:0.72rem; color:#475569; font-family:IBM Plex Mono'>"
        "LADM-COL / CTM12<br>IGAC Multipurpose Cadastre<br>CRS: EPSG:3116"
        "</div>",
        unsafe_allow_html=True,
    )

# ---------------------------------------------------
# HEADER
# ---------------------------------------------------

st.markdown("""
<div class="dash-header">
    <h1>🗺️ Cadastral QA/QC Dashboard</h1>
    <p>LADM-COL / CTM12 — Automated spatial data quality control</p>
</div>
""", unsafe_allow_html=True)

# ---------------------------------------------------
# LOAD DATA
# ---------------------------------------------------

df_detail  = None
df_summary = None

if data_source == "Load existing reports":
    detail_path  = "outputs/quality_report.csv"
    summary_path = "outputs/quality_summary.csv"

    if os.path.exists(detail_path) and os.path.exists(summary_path):
        df_detail, df_summary = load_csv_reports(detail_path, summary_path)
        st.markdown(
            f'<div class="info-box">📂 Loaded from <code>{detail_path}</code> — '
            f'run <code>main.py</code> to refresh results.</div>',
            unsafe_allow_html=True,
        )
    else:
        st.markdown(
            '<div class="warn-box">⚠️ No report files found. '
            'Run <code>main.py</code> first, or switch to <b>Run validation now</b>.</div>',
            unsafe_allow_html=True,
        )
        st.stop()

else:
    if st.button("▶ Run Validation Pipeline", type="primary"):
        with st.spinner("Running validation..."):
            df_detail, df_summary = run_validation_pipeline()
        st.success("Validation complete.")
    else:
        st.markdown(
            '<div class="info-box">Click <b>Run Validation Pipeline</b> to start.</div>',
            unsafe_allow_html=True,
        )
        st.stop()

# ---------------------------------------------------
# APPLY FILTERS
# ---------------------------------------------------

df_filtered = df_detail[df_detail["validation_category"].isin(selected_categories)].copy()
if not show_zero:
    df_filtered = df_filtered[df_filtered["error_count"] > 0]

# ---------------------------------------------------
# KPI CARDS
# ---------------------------------------------------

total   = int(df_detail["error_count"].sum())
grave   = int(df_detail[df_detail["severity"] == "critical"]["error_count"].sum())
moderado= int(df_detail[df_detail["severity"] == "moderate"]["error_count"].sum())
leve    = int(df_detail[df_detail["severity"] == "low"]["error_count"].sum())

st.markdown(f"""
<div class="kpi-grid">
    <div class="kpi-card total">
        <div class="kpi-label">Total Errors</div>
        <div class="kpi-value">{total:,}</div>
    </div>
    <div class="kpi-card grave">
        <div class="kpi-label">Critical</div>
        <div class="kpi-value">{grave:,}</div>
    </div>
    <div class="kpi-card moderado">
        <div class="kpi-label">Moderate</div>
        <div class="kpi-value">{moderado:,}</div>
    </div>
    <div class="kpi-card leve">
        <div class="kpi-label">Low</div>
        <div class="kpi-value">{leve:,}</div>
    </div>
</div>
""", unsafe_allow_html=True)

# ---------------------------------------------------
# CHARTS — ROW 1
# ---------------------------------------------------

st.markdown('<div class="section-title">Error Distribution</div>', unsafe_allow_html=True)

col1, col2 = st.columns([3, 2])

with col1:
    # Errors by layer and category — stacked bar
    layer_cat = (
        df_filtered
        .groupby(["layer", "validation_category"])["error_count"]
        .sum()
        .reset_index()
    )

    fig_bar = go.Figure()
    for cat in layer_cat["validation_category"].unique():
        cat_data = layer_cat[layer_cat["validation_category"] == cat]
        fig_bar.add_trace(go.Bar(
            name=cat,
            x=cat_data["layer"],
            y=cat_data["error_count"],
            marker_color=CATEGORY_COLORS.get(cat, "#64748b"),
        ))

    fig_bar.update_layout(
        barmode="stack",
        height=380,
        xaxis_tickangle=-30,
        showlegend=True,
        legend=dict(orientation="h", y=-0.25, font_size=11),
        margin=dict(t=20, b=80, l=10, r=10),
        **CHART_THEME,
    )
    fig_bar.update_xaxes(tickfont_size=10)
    st.plotly_chart(fig_bar, use_container_width=True)

with col2:
    # Errors by category — donut
    cat_totals = (
        df_filtered
        .groupby("validation_category")["error_count"]
        .sum()
        .reset_index()
        .sort_values("error_count", ascending=False)
    )

    fig_donut = go.Figure(go.Pie(
        labels=cat_totals["validation_category"],
        values=cat_totals["error_count"],
        hole=0.55,
        marker_colors=[CATEGORY_COLORS.get(c, "#64748b") for c in cat_totals["validation_category"]],
        textfont_size=11,
        textinfo="percent+label",
    ))
    fig_donut.update_layout(
        height=380,
        showlegend=False,
        margin=dict(t=20, b=20, l=10, r=10),
        **CHART_THEME,
    )
    st.plotly_chart(fig_donut, use_container_width=True)

# ---------------------------------------------------
# CHARTS — ROW 2: Severity breakdown
# ---------------------------------------------------

st.markdown('<div class="section-title">Severity Breakdown by Layer</div>', unsafe_allow_html=True)

sev_data = (
    df_filtered[df_filtered["severity"].isin(["critical", "moderate", "low"])]
    .groupby(["layer", "severity"])["error_count"]
    .sum()
    .reset_index()
)

fig_sev = go.Figure()
for sev in ["critical", "moderate", "low"]:
    s = sev_data[sev_data["severity"] == sev]
    fig_sev.add_trace(go.Bar(
        name=sev.capitalize(),
        x=s["layer"],
        y=s["error_count"],
        marker_color=SEVERITY_COLORS[sev],
    ))

fig_sev.update_layout(
    barmode="group",
    height=320,
    xaxis_tickangle=-30,
    legend=dict(orientation="h", y=-0.3, font_size=11),
    margin=dict(t=10, b=90, l=10, r=10),
    **CHART_THEME,
)
st.plotly_chart(fig_sev, use_container_width=True)

# ---------------------------------------------------
# DETAIL TABLE
# ---------------------------------------------------

st.markdown('<div class="section-title">Validation Detail</div>', unsafe_allow_html=True)

selected_layer = st.selectbox(
    "Filter by layer",
    ["All layers"] + sorted(df_detail["layer"].unique().tolist()),
)

display_df = df_filtered.copy()
if selected_layer != "All layers":
    display_df = display_df[display_df["layer"] == selected_layer]

display_df = display_df.sort_values(["layer", "error_count"], ascending=[True, False])

def color_severity(val):
    colors = {
        "critical":    "color: #ef4444; font-weight: 600",
        "moderate": "color: #f59e0b; font-weight: 600",
        "low":     "color: #22c55e; font-weight: 600",
        "none":     "color: #475569",
    }
    return colors.get(val, "")

styled = (
    display_df[["layer", "validation_category", "validation_type", "error_count", "severity"]]
    .rename(columns={
        "layer": "Layer",
        "validation_category": "Category",
        "validation_type": "Validation",
        "error_count": "Errors",
        "severity": "Severity",
    })
    .style
    .applymap(color_severity, subset=["Severity"])
    .format({"Errors": "{:,}"})
    .set_properties(**{"font-family": "IBM Plex Mono", "font-size": "13px"})
)

st.dataframe(styled, use_container_width=True, height=420)

# ---------------------------------------------------
# MAP
# ---------------------------------------------------

st.markdown('<div class="section-title">Spatial Error Map</div>', unsafe_allow_html=True)

OUTPUT_GPKG = "outputs/output_errors.gpkg"

if not os.path.exists(OUTPUT_GPKG):
    st.markdown(
        '<div class="warn-box">⚠️ No GeoPackage found at <code>outputs/output_errors.gpkg</code>. '
        'Run <code>main.py</code> to generate error geometries.</div>',
        unsafe_allow_html=True,
    )
else:
    import fiona
    available_layers = fiona.listlayers(OUTPUT_GPKG)

    map_layer = st.selectbox("Select error layer to display", available_layers)

    try:
        gdf_map = gpd.read_file(OUTPUT_GPKG, layer=map_layer)

        if gdf_map.crs and gdf_map.crs.to_epsg() != 4326:
            gdf_map = gdf_map.to_crs(epsg=4326)

        centroid = gdf_map.geometry.centroid
        center_lat = centroid.y.mean()
        center_lon = centroid.x.mean()

        # Determine color by layer name prefix
        color = "#ef4444"
        if "overlap" in map_layer:   color = "#f59e0b"
        elif "geom" in map_layer:    color = "#3b82f6"
        elif "attr" in map_layer:    color = "#06b6d4"
        elif "dup" in map_layer:     color = "#8b5cf6"
        elif "ref" in map_layer:     color = "#ec4899"

        fig_map = go.Figure()

        for _, row in gdf_map.iterrows():
            geom = row.geometry
            if geom is None or geom.is_empty:
                continue

            if geom.geom_type == "Polygon":
                x, y = geom.exterior.xy
                fig_map.add_trace(go.Scattermapbox(
                    lon=list(x), lat=list(y),
                    mode="lines",
                    line=dict(color=color, width=1.5),
                    showlegend=False,
                    hoverinfo="skip",
                ))
            elif geom.geom_type == "MultiPolygon":
                for poly in geom.geoms:
                    x, y = poly.exterior.xy
                    fig_map.add_trace(go.Scattermapbox(
                        lon=list(x), lat=list(y),
                        mode="lines",
                        line=dict(color=color, width=1.5),
                        showlegend=False,
                        hoverinfo="skip",
                    ))
            elif "Point" in geom.geom_type:
                fig_map.add_trace(go.Scattermapbox(
                    lon=[geom.x], lat=[geom.y],
                    mode="markers",
                    marker=dict(size=6, color=color),
                    showlegend=False,
                    hoverinfo="skip",
                ))

        fig_map.update_layout(
            mapbox=dict(
                style="carto-darkmatter",
                center=dict(lat=center_lat, lon=center_lon),
                zoom=12,
            ),
            height=550,
            margin=dict(t=0, b=0, l=0, r=0),
            paper_bgcolor="#151820",
        )

        st.plotly_chart(fig_map, use_container_width=True)
        st.markdown(
            f'<div class="info-box">Displaying <b>{len(gdf_map):,}</b> features '
            f'from layer <code>{map_layer}</code></div>',
            unsafe_allow_html=True,
        )

    except Exception as e:
        st.error(f"Error loading map layer: {e}")

# ---------------------------------------------------
# FOOTER
# ---------------------------------------------------

st.markdown("---")
st.markdown(
    "<div style='font-size:0.72rem; color:#334155; font-family:IBM Plex Mono; text-align:center'>"
    "Cadastral Data Quality Control · LADM-COL / CTM12 · "
    "Developed by <a href='https://linkedin.com/in/adiaz96/' style='color:#475569'>Andres Diaz</a>"
    "</div>",
    unsafe_allow_html=True,
)