"""
report_builder.py
-----------------
Consolidates all validation results into structured summaries
ready for CSV export and Streamlit dashboard consumption.

Produces:
  - Per-layer summary with error counts by type and severity
  - Global summary across all layers
  - Severity breakdown for hierarchy errors
  - Dashboard-ready data structures
"""

import pandas as pd
import geopandas as gpd
from datetime import datetime


# ---------------------------------------------------------------------------
# REPORT BUILDER
# ---------------------------------------------------------------------------

class ReportBuilder:
    """
    Collects validation results and builds structured reports.

    Usage
    -----
    builder = ReportBuilder(project_stage="initial", overlap_threshold=0.10)
    builder.add_geometry(layer, geometry_summary)
    builder.add_overlaps(layer, overlap_gdf)
    builder.add_hierarchy(name, hierarchy_gdf)
    builder.add_attributes(layer, attribute_results)
    builder.add_duplicates(layer, duplicate_gdf)
    builder.add_referential(name, ref_gdf)
    df_summary, df_detail = builder.build()
    """

    def __init__(self, project_stage: str, overlap_threshold: float):
        self.project_stage = project_stage
        self.overlap_threshold = overlap_threshold
        self.timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self._rows = []

    # ------------------------------------------------------------------
    # Add methods
    # ------------------------------------------------------------------

    def add_geometry(self, layer: str, summary: dict) -> None:
        """
        Add geometry validation results.

        Parameters
        ----------
        layer : str
            CTM12 layer name.
        summary : dict
            Output from geometry_validator.summarize_geometry_errors().
        """
        for error_type, count in summary.items():
            if error_type == "total":
                continue
            self._rows.append({
                "layer": layer,
                "validation_category": "geometry",
                "validation_type": error_type,
                "error_count": count,
                "severity": "critical" if count > 0 else "none",
            })

    def add_overlaps(self, layer: str, gdf: gpd.GeoDataFrame) -> None:
        """
        Add overlap validation results.

        Parameters
        ----------
        layer : str
            CTM12 layer name.
        gdf : GeoDataFrame
            Output from overlap_validator or unit_validator.
        """
        self._rows.append({
            "layer": layer,
            "validation_category": "overlap",
            "validation_type": "intra_layer_overlap",
            "error_count": len(gdf),
            "severity": self._overlap_severity(len(gdf)),
        })

    def add_hierarchy(self, name: str, gdf: gpd.GeoDataFrame) -> None:
        """
        Add hierarchy validation results with severity breakdown.

        Parameters
        ----------
        name : str
            Descriptive name (e.g. 'unidad_fuera_construccion_pct').
        gdf : GeoDataFrame
            Output from hierarchy_validator.validate_within_percentage().
        """
        if gdf.empty or "severity" not in gdf.columns:
            self._rows.append({
                "layer": name,
                "validation_category": "hierarchy",
                "validation_type": name,
                "error_count": 0,
                "severity": "none",
            })
            return

        for severity in ["low", "moderate", "critical"]:
            count = len(gdf[gdf["severity"] == severity])
            self._rows.append({
                "layer": name,
                "validation_category": "hierarchy",
                "validation_type": f"{name}_{severity}",
                "error_count": count,
                "severity": severity,
            })

    def add_attributes(self, layer: str, results: dict) -> None:
        """
        Add attribute validation results.

        Parameters
        ----------
        layer : str
            CTM12 layer name.
        results : dict
            Output from attribute_validator.validate_attributes().
        """
        type_map = {
            "null_fields":             ("null_mandatory_field",   "critical"),
            "field_lengths":           ("field_length_exceeded",  "moderate"),
            "domain_values":           ("invalid_domain_value",   "critical"),
            "numeric_ranges":          ("numeric_out_of_range",   "moderate"),
            "tipo_construccion_nulls": ("null_tipo_construccion", "critical"),
            "planta_nulls":            ("null_planta",            "critical"),
            "planta_invalid_format":   ("invalid_planta_format",  "moderate"),
        }

        for key, (validation_type, severity) in type_map.items():
            gdf = results.get(key)
            if not isinstance(gdf, gpd.GeoDataFrame):
                continue
            self._rows.append({
                "layer": layer,
                "validation_category": "attribute",
                "validation_type": validation_type,
                "error_count": len(gdf),
                "severity": severity if len(gdf) > 0 else "none",
            })

    def add_duplicates(self, layer: str, gdf: gpd.GeoDataFrame) -> None:
        """
        Add duplicate CODIGO validation results.

        Parameters
        ----------
        layer : str
            CTM12 layer name.
        gdf : GeoDataFrame
            Output from duplicate_validator.validate_duplicates().
        """
        self._rows.append({
            "layer": layer,
            "validation_category": "duplicate",
            "validation_type": "duplicate_codigo",
            "error_count": len(gdf),
            "severity": "critical" if len(gdf) > 0 else "none",
        })

    def add_referential(self, name: str, gdf: gpd.GeoDataFrame) -> None:
        """
        Add referential integrity validation results.

        Parameters
        ----------
        name : str
            Descriptive name (e.g. 'ref_construccion_sin_terreno').
        gdf : GeoDataFrame
            Output from attribute_validator.validate_referential_integrity().
        """
        self._rows.append({
            "layer": name,
            "validation_category": "referential_integrity",
            "validation_type": name,
            "error_count": len(gdf),
            "severity": "critical" if len(gdf) > 0 else "none",
        })

    # ------------------------------------------------------------------
    # Build reports
    # ------------------------------------------------------------------

    def build(self) -> tuple[pd.DataFrame, pd.DataFrame]:
        """
        Build the final report DataFrames.

        Returns
        -------
        df_detail : pd.DataFrame
            One row per (layer, validation_type) with error count and severity.
            Ready for CSV export.

        df_summary : pd.DataFrame
            One row per layer with total error count and worst severity.
            Ready for Streamlit dashboard KPI cards.
        """
        df_detail = pd.DataFrame(self._rows)

        if df_detail.empty:
            return pd.DataFrame(), pd.DataFrame()

        df_detail["project_stage"] = self.project_stage
        df_detail["timestamp"] = self.timestamp

        # Summary — aggregate by layer
        severity_order = {"critical": 3, "moderate": 2, "low": 1, "none": 0}

        summary_rows = []
        for layer, group in df_detail.groupby("layer"):
            total_errors = group["error_count"].sum()
            worst_severity = group["severity"].map(severity_order).max()
            worst_label = {v: k for k, v in severity_order.items()}.get(worst_severity, "none")

            summary_rows.append({
                "layer": layer,
                "total_errors": total_errors,
                "worst_severity": worst_label,
                "geometry_errors": group[group["validation_category"] == "geometry"]["error_count"].sum(),
                "overlap_errors": group[group["validation_category"] == "overlap"]["error_count"].sum(),
                "hierarchy_errors": group[group["validation_category"] == "hierarchy"]["error_count"].sum(),
                "attribute_errors": group[group["validation_category"] == "attribute"]["error_count"].sum(),
                "duplicate_errors": group[group["validation_category"] == "duplicate"]["error_count"].sum(),
                "referential_errors": group[group["validation_category"] == "referential_integrity"]["error_count"].sum(),
            })

        df_summary = pd.DataFrame(summary_rows)

        return df_detail, df_summary

    def global_summary(self) -> dict:
        """
        Compute global KPIs across all layers.

        Returns
        -------
        dict with keys:
            total_errors        : int
            total_grave         : int
            total_moderado      : int
            total_leve          : int
            layers_with_errors  : int
            project_stage       : str
            timestamp           : str
        """
        df, _ = self.build()
        if df.empty:
            return {}

        return {
            "total_errors":       int(df["error_count"].sum()),
            "total_critical":        int(df[df["severity"] == "critical"]["error_count"].sum()),
            "total_moderate":     int(df[df["severity"] == "moderate"]["error_count"].sum()),
            "total_low":         int(df[df["severity"] == "low"]["error_count"].sum()),
            "layers_with_errors": int((df.groupby("layer")["error_count"].sum() > 0).sum()),
            "project_stage":      self.project_stage,
            "timestamp":          self.timestamp,
        }

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _overlap_severity(count: int) -> str:
        if count == 0:
            return "none"
        elif count <= 10:
            return "low"
        elif count <= 100:
            return "moderate"
        else:
            return "critical"