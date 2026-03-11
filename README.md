# 🗺️ Cadastral Data Quality Control — LADM-COL / CTM12

> **Automated QA/QC system for multipurpose cadastral data validation under the LADM-COL standard (IGAC). Detects geometry errors, spatial overlaps, attribute inconsistencies, and hierarchical violations across urban cadastral layers, with severity classification and an interactive Streamlit dashboard.**

[![Python](https://img.shields.io/badge/Python-3.12-blue?logo=python)](https://python.org)
[![GeoPandas](https://img.shields.io/badge/GeoPandas-1.0+-green)](https://geopandas.org)
[![Streamlit](https://img.shields.io/badge/Streamlit-Dashboard-red?logo=streamlit)](https://cadastral-data-quality-control.streamlit.app/)
[![LADM-COL](https://img.shields.io/badge/Standard-LADM--COL%20%7C%20CTM12-orange)](https://www.igac.gov.co)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

🌐 **[Live Dashboard →](https://cadastral-data-quality-control.streamlit.app/)**

---

## 📌 Overview

This system automates the quality control process for urban cadastral datasets structured under the **LADM-COL model** as implemented by IGAC in the **CTM12 (Catastro Multipropósito)** framework. It validates the four core urban layers across five dimensions:

- **Geometry validation** — invalid, null, and empty geometries
- **Overlap validation** — spatial intersections within each layer using adaptive thresholds
- **Hierarchy validation** — spatial containment and percentage-based tolerance checks
- **Attribute validation** — mandatory field nulls, format checks, and code consistency
- **Duplicate validation** — duplicate feature detection per layer

Errors are classified by severity (`critical`, `moderate`, `low`) and visualized in an interactive Streamlit dashboard with spatial map, KPI cards, and filterable detail tables.

---

## 🏛️ LADM-COL Cadastral Hierarchy

The system validates the following containment hierarchy, following IGAC's multipurpose cadastral model:

```
U_MANZANA_CTM12
    └── U_TERRENO_CTM12
            └── U_CONSTRUCCION_CTM12
                    └── U_UNIDAD_CTM12  (grouped by CONSTRUCCION_CODIGO + PLANTA)
```

Each level must be spatially contained within its parent. Violations are reported with the percentage of area falling outside the parent polygon and classified by severity.

---

## ✅ Validations Implemented

### 1. Geometry Validation (`geometry_validator.py`)
| Check | Description |
|---|---|
| Invalid geometries | Self-intersections, malformed rings, topologically invalid features |
| Empty geometries | Null or zero-area features |

### 2. Overlap Validation (`overlap_validator.py` / `unit_validator.py`)
| Check | Description |
|---|---|
| Intra-layer overlaps | Overlapping polygons within the same layer using STRtree spatial indexing |
| Unit overlaps by floor | `U_UNIDAD` overlaps grouped by `CONSTRUCCION_CODIGO` + `PLANTA` — avoids false positives between floors |
| Adaptive threshold | Overlap tolerance adjusts by project stage |

### 3. Hierarchy Validation (`hierarchy_validator.py`)
| Check | Description |
|---|---|
| Spatial containment | Each feature must fall within its parent layer union |
| Percentage-based tolerance | Area outside parent calculated and classified by severity |
| Referential integrity | Orphan detection across all hierarchy levels |

### 4. Attribute Validation (`attribute_validator.py`)
| Check | Description |
|---|---|
| Mandatory null fields | Required fields with null values |
| PLANTA format | Floor identifier format validation |
| Code consistency | CONSTRUCCION_CODIGO referential checks |

### 5. Duplicate Validation (`duplicate_validator.py`)
| Check | Description |
|---|---|
| Duplicate geometries | Exact geometry duplicates per layer (excludes UNIDAD and CONSTRUCCION by design) |

### Severity Classification
| Severity | Threshold | Action |
|---|---|---|
| `low` | ≤ 1% outside parent | Review — may be digitization tolerance |
| `moderate` | 1% – 10% outside parent | Correction recommended |
| `critical` | > 10% outside parent | Mandatory correction before delivery |

---

## ⚙️ Project Stage Configuration

```python
# main.py
PROJECT_STAGE = "initial"  # options: initial | preliminary | final

thresholds = {
    "initial":     0.10,   # 0.10 m² — permissive, early review
    "preliminary": 0.02,   # 0.02 m² — intermediate cleanup
    "final":       0.0001  # 0.0001 m² — strict, pre-delivery
}
```

---

## 📁 Repository Structure

```
cadastral-data-quality-control/
│
├── main.py                     # Main validation pipeline (console)
├── dashboard.py                # Streamlit interactive dashboard
├── inspect_schema.py           # Utility: inspect layer schema
├── generate_sample_gpkg.py     # Utility: generate synthetic sample data
│
├── geometry_validator.py       # Invalid geometry detection
├── overlap_validator.py        # Intra-layer overlap detection
├── unit_validator.py           # U_UNIDAD floor-level overlap validation
├── hierarchy_validator.py      # Spatial containment + referential integrity
├── attribute_validator.py      # Mandatory field and format validation
├── duplicate_validator.py      # Duplicate geometry detection
├── report_builder.py           # CSV + GeoPackage report generation
│
├── outputs/
│   ├── quality_report.csv      # Full error detail (layer, type, severity, geometry)
│   ├── quality_summary.csv     # Aggregated counts per layer and category
│   └── sample_errors.gpkg      # Sample error geometries for dashboard demo
│
├── requirements.txt
└── README.md
```

---

## 🚀 How to Run

### 1. Install dependencies

```bash
pip install -r requirements.txt
```

### 2. Run the validation pipeline

```bash
python main.py
```

Outputs written to `outputs/`:
- `quality_report.csv` — full error detail
- `quality_summary.csv` — aggregated counts
- `output_errors.gpkg` — error geometries for QGIS/ArcGIS

### 3. Launch the dashboard

```bash
streamlit run dashboard.py
```

🔗 Or visit the **[live demo](https://cadastral-data-quality-control.streamlit.app/)**

---

## 📊 Validation Results — Test Dataset

Dataset: `urban_ctm12_anonymized.gpkg` | CRS: EPSG:3116 | Provisional migration data

| Layer | Features |
|---|---|
| U_MANZANA_CTM12 | 2,861 |
| U_TERRENO_CTM12 | 48,289 |
| U_CONSTRUCCION_CTM12 | 63,344 |
| U_UNIDAD_CTM12 | 159,420 |

| Category | Critical | Moderate | Low | Total |
|---|---|---|---|---|
| Geometry | 53 | 0 | 0 | 53 |
| Duplicates | 0 | 85 | 0 | 85 |
| Overlaps | 0 | 76,001 | 30,971 | 107,972 |
| Hierarchy | 1,087,557 | 0 | 0 | 1,087,557 |
| Attributes | 53 | 0 | 0 | 53 |
| **Total** | **1,087,610** | **76,086** | **30,971** | **1,194,667** |

> Note: high hierarchy error counts reflect null `MANZANA_CODIGO` values typical of provisional migration datasets — not indicative of production data quality.

---

## 🔧 Tech Stack

| Category | Tools |
|---|---|
| Spatial processing | GeoPandas, Shapely, Fiona |
| Cadastral standard | LADM-COL / CTM12 (IGAC) |
| Coordinate system | MAGNA-SIRGAS / Colombia Bogotá (EPSG:3116) |
| Input format | GeoPackage (.gpkg) |
| Output formats | GeoPackage (.gpkg), CSV |
| Dashboard | Streamlit, Plotly |
| Deployment | Streamlit Cloud |

---

## 🗺️ Roadmap

- [x] Geometry validation
- [x] Intra-layer overlap detection with spatial indexing
- [x] Floor-level U_UNIDAD overlap validation
- [x] Hierarchical containment validation (hard + percentage-based)
- [x] Referential integrity checks
- [x] Attribute and format validation
- [x] Duplicate detection
- [x] Severity classification (critical / moderate / low)
- [x] GeoPackage + CSV export
- [x] Streamlit dashboard with KPI cards, charts, spatial map
- [ ] HTML report generation
- [ ] Synthetic sample dataset for full reproducibility

---

## 👤 Author

**German Andrés Diaz Gelves**
GIS & Spatial Data Analyst | Cadastral QA/QC | LADM-COL

5+ years of experience in cadastral projects with IGAC, Catastro Distrital, and multipurpose cadastral programs across Colombia.

[![LinkedIn](https://img.shields.io/badge/LinkedIn-Connect-blue?logo=linkedin)](https://linkedin.com/in/adiaz96/)
[![Email](https://img.shields.io/badge/Email-Contact-red?logo=gmail)](mailto:andresdgel96@gmail.com)

*Open to remote opportunities in GIS analysis, cadastral data management, and geospatial quality control.*
