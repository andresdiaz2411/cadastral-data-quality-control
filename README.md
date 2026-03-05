# 🗺️ Cadastral Data Quality Control — LADM-COL / CTM12

> **Automated QA/QC system for multipurpose cadastral data validation under the LADM-COL standard (IGAC). Detects geometry errors, spatial overlaps, and hierarchical inconsistencies across urban cadastral layers, with severity classification and multi-format reporting.**

[![Python](https://img.shields.io/badge/Python-3.12-blue?logo=python)](https://python.org)
[![GeoPandas](https://img.shields.io/badge/GeoPandas-0.14-green)](https://geopandas.org)
[![LADM-COL](https://img.shields.io/badge/Standard-LADM--COL%20%7C%20CTM12-orange)](https://www.igac.gov.co)
[![Status](https://img.shields.io/badge/Status-Functional%20Prototype-yellow)]()
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

> ⚠️ **Work in progress** — Streamlit dashboard under development. Console pipeline fully functional.

---

## 📌 Overview

This system automates the quality control process for urban cadastral datasets structured under the **LADM-COL model** as implemented by IGAC in the **CTM12 (Catastro Multipropósito)** framework. It validates the four core urban layers across three dimensions:

- **Geometry validation** — invalid, null, and empty geometries
- **Overlap validation** — spatial intersections within each layer using adaptive thresholds
- **Hierarchy validation** — spatial containment and percentage-based tolerance checks across the cadastral hierarchy

Errors are classified by severity (`leve`, `moderado`, `grave`) and exported as a GeoPackage for direct inspection in QGIS or ArcGIS, alongside a CSV summary report.

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
| Invalid geometries | Detects self-intersections, malformed rings, and topologically invalid features |

### 2. Overlap Validation (`overlap_validator.py` / `unit_validator.py`)
| Check | Description |
|---|---|
| Intra-layer overlaps | Detects overlapping polygons within the same layer using spatial indexing (STRtree) |
| Unit overlaps by construction | Validates overlaps between `U_UNIDAD` features grouped by `CONSTRUCCION_CODIGO` and `PLANTA` — avoids false positives between units on different floors |
| Adaptive threshold | Overlap tolerance adjusts based on project stage (see configuration) |

### 3. Hierarchy Validation (`hierarchy_validator.py`)
| Check | Description |
|---|---|
| Hard containment check | Binary validation — feature must be fully `within()` its parent layer union |
| Percentage-based tolerance | Calculates the percentage of each feature's area falling outside its parent, with severity classification |

### Severity Classification
| Severity | Threshold | Action |
|---|---|---|
| `leve` | ≤ 1% outside parent | Review — may be digitization tolerance |
| `moderado` | 1% – 10% outside parent | Correction recommended |
| `grave` | > 10% outside parent | Mandatory correction before delivery |

---

## ⚙️ Project Stage Configuration

The system adapts overlap thresholds to the current stage of the cadastral project:

```python
# main.py
PROJECT_STAGE = "initial"  # options: initial | preliminary | final

thresholds = {
    "initial":     0.10,   # 0.10 m² — permissive, early review
    "preliminary": 0.02,   # 0.02 m² — intermediate cleanup
    "final":       0.0001  # 0.0001 m² — strict, pre-delivery
}
```

This reflects the real workflow of LADM-COL cadastral projects, where tolerance requirements tighten as the project approaches final delivery to IGAC.

---

## 📁 Repository Structure

```
cadastral-data-quality-control/
│
├── main.py                         # Main validation pipeline (console)
├── filter_layers.py                # Utility: list CTM12 layers from GeoPackage
├── inspect_layers.py               # Utility: inspect layer schema and geometry type
│
├── validation_engine/
│   ├── geometry_validator.py       # Invalid geometry detection
│   ├── overlap_validator.py        # Intra-layer overlap detection with spatial index
│   ├── unit_validator.py           # U_UNIDAD overlap validation by construction + floor
│   └── hierarchy_validator.py      # Spatial containment and percentage-based checks
│
├── input_data/                     # Input GeoPackage (not included — see Data section)
├── outputs/                        # Validation outputs
├── schema_reference/               # LADM-COL schema reference documents
│
├── output_errors.gpkg              # Generated: error geometries per layer
├── quality_report.csv              # Generated: summary error counts per layer
└── README.md
```

---

## 🚀 How to Run

### 1. Install dependencies

```bash
pip install geopandas fiona pandas
```

### 2. Add your input data

Place your GeoPackage in the `input_data/` folder:

```
input_data/
└── urban_ctm12_anonymized.gpkg
```

The GeoPackage must contain the following layers with CTM12-compliant schema:
- `U_TERRENO_CTM12`
- `U_CONSTRUCCION_CTM12`
- `U_UNIDAD_CTM12` (requires `CONSTRUCCION_CODIGO` and `PLANTA` fields)
- `U_MANZANA_CTM12`

### 3. Configure project stage

Edit `main.py`:

```python
PROJECT_STAGE = "initial"  # initial | preliminary | final
```

### 4. Run the pipeline

```bash
python main.py
```

### 5. Review outputs

| Output | Description |
|---|---|
| `output_errors.gpkg` | Error geometries — open in QGIS or ArcGIS for spatial review |
| `quality_report.csv` | Summary table: error counts per layer and validation type |

---

## 📊 Output Example

```
Loading U_TERRENO_CTM12...
Loading U_CONSTRUCCION_CTM12...
Loading U_UNIDAD_CTM12...
Loading U_MANZANA_CTM12...

Validating U_TERRENO_CTM12
U_TERRENO_CTM12 → Invalid geometries: 3
U_TERRENO_CTM12 → Overlaps > 0.1 m²: 7

Validating U_UNIDAD_CTM12
U_UNIDAD_CTM12 → Invalid geometries: 0
U_UNIDAD_CTM12 → Overlaps > 0.1 m²: 12

Hierarchy Validation
unidad_fuera_pct: 5 cases
construccion_fuera_pct: 2 cases
terreno_fuera_pct: 0 cases

Quality report exported as quality_report.csv
Validation process completed successfully.
```

---

## 🗂️ Data

Input data is not included in this repository to protect cadastral information. The system was developed and tested using **anonymized urban cadastral datasets** following the CTM12 schema from IGAC's multipurpose cadastral program.

To run the system with your own data, your GeoPackage must follow the LADM-COL field naming conventions as specified in the [IGAC CTM12 technical guide](https://www.igac.gov.co).

> 📌 Sample synthetic data for testing purposes is planned for a future release.

---

## 🔧 Tech Stack

| Category | Tools |
|---|---|
| Spatial processing | GeoPandas, Fiona, Shapely |
| Cadastral standard | LADM-COL / CTM12 (IGAC) |
| Input format | GeoPackage (.gpkg) |
| Output formats | GeoPackage (.gpkg), CSV |
| Interface | Console (current) · Streamlit (in development) |

---

## 🗺️ Roadmap

- [x] Geometry validation
- [x] Intra-layer overlap detection with spatial indexing
- [x] Hierarchical containment validation (hard + percentage-based)
- [x] Severity classification (leve / moderado / grave)
- [x] GeoPackage + CSV export
- [ ] Attribute validation (field format, null checks, code consistency)
- [ ] Synthetic sample dataset for reproducibility
- [ ] Streamlit dashboard with interactive error map
- [ ] HTML report generation

---

## 👤 Author

**German Andrés Diaz Gelves**
GIS & Spatial Data Analyst | Cadastral QA/QC | LADM-COL

5+ years of experience in cadastral projects with IGAC, Catastro Distrital, and multipurpose cadastral programs across Colombia.

[![LinkedIn](https://img.shields.io/badge/LinkedIn-Connect-blue?logo=linkedin)](https://linkedin.com/in/adiaz96/)
[![Email](https://img.shields.io/badge/Email-Contact-red?logo=gmail)](mailto:andresdgel96@gmail.com)

*Open to remote opportunities in GIS analysis, cadastral data management, and geospatial quality control.*
