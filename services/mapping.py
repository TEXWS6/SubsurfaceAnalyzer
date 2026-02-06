"""Mapping service for contour/isopach map generation using scipy interpolation.

Supports: cubic/linear/nearest (scipy), Ordinary Kriging (pykrige), IDW.
Map types: structure, isopach, bubble, posted values, pie chart, grid property.
"""

import numpy as np
from scipy.interpolate import griddata
import plotly.graph_objects as go


class MappingService:
    @staticmethod
    def interpolate_grid(x: np.ndarray, y: np.ndarray, z: np.ndarray,
                         method: str = "cubic", resolution: int = 100) -> tuple:
        """Interpolate scattered data onto a regular grid.

        Returns (xi, yi, zi) where zi is the interpolated grid.
        """
        if len(x) < 3:
            method = "nearest"
        elif len(x) < 4 and method == "cubic":
            method = "linear"

        padding = 0.1
        x_range = x.max() - x.min() if x.max() != x.min() else 1.0
        y_range = y.max() - y.min() if y.max() != y.min() else 1.0
        x_pad = x_range * padding
        y_pad = y_range * padding

        xi = np.linspace(x.min() - x_pad, x.max() + x_pad, resolution)
        yi = np.linspace(y.min() - y_pad, y.max() + y_pad, resolution)
        xi_grid, yi_grid = np.meshgrid(xi, yi)

        zi = griddata(
            np.column_stack([x, y]),
            z,
            (xi_grid, yi_grid),
            method=method,
        )

        # Fill NaN edges with nearest neighbor
        if np.any(np.isnan(zi)):
            zi_nearest = griddata(
                np.column_stack([x, y]),
                z,
                (xi_grid, yi_grid),
                method="nearest",
            )
            zi = np.where(np.isnan(zi), zi_nearest, zi)

        return xi, yi, zi

    @staticmethod
    def build_contour_figure(xi, yi, zi, x_wells, y_wells, z_wells,
                             well_names, title: str = "Structure Map",
                             colorscale: str = "Viridis",
                             z_label: str = "Depth (ft)") -> go.Figure:
        """Build a Plotly contour figure with well spots."""
        fig = go.Figure()

        # Contour fill
        fig.add_trace(go.Contour(
            x=xi, y=yi, z=zi,
            colorscale=colorscale,
            contours=dict(showlabels=True, labelfont=dict(size=10, color="white")),
            colorbar=dict(title=z_label),
            name="Contours",
        ))

        # Well spots
        fig.add_trace(go.Scatter(
            x=x_wells, y=y_wells,
            mode="markers+text",
            marker=dict(size=10, color="black", symbol="circle"),
            text=well_names,
            textposition="top center",
            textfont=dict(size=9),
            customdata=z_wells,
            hovertemplate="%{text}<br>X: %{x:.1f}<br>Y: %{y:.1f}<br>Value: %{customdata:.1f}<extra></extra>",
            name="Wells",
        ))

        fig.update_layout(
            title=title,
            xaxis_title="X",
            yaxis_title="Y",
            xaxis=dict(scaleanchor="y", scaleratio=1),
            height=700,
            margin=dict(l=60, r=20, t=50, b=60),
        )

        return fig

    @classmethod
    def build_structure_map(cls, wells_data: list, formation: str,
                            method: str = "cubic", resolution: int = 100,
                            colorscale: str = "Viridis") -> go.Figure:
        """Build a structure contour map for a formation top.

        wells_data: list of dicts with x_coord, y_coord, kb, md_top, well_name
        """
        if not wells_data:
            return go.Figure().update_layout(title="No data available")

        x = np.array([w["x_coord"] for w in wells_data])
        y = np.array([w["y_coord"] for w in wells_data])
        # Structure = KB - MD (subsea elevation)
        z = np.array([
            (w.get("kb", 0) or 0) - w["md_top"] for w in wells_data
        ])
        names = [w.get("well_name", "") for w in wells_data]

        xi, yi, zi = cls.interpolate_grid(x, y, z, method, resolution)
        return cls.build_contour_figure(
            xi, yi, zi, x, y, z, names,
            title=f"Structure Map — {formation}",
            colorscale=colorscale,
            z_label="TVDSS (ft)",
        )

    @classmethod
    def build_isopach_map(cls, wells_data: list, formation_top: str,
                          formation_base: str, method: str = "cubic",
                          resolution: int = 100,
                          colorscale: str = "Viridis") -> go.Figure:
        """Build an isopach (thickness) map between two formation tops.

        wells_data: list of dicts with x_coord, y_coord, md_top, md_base, well_name
        """
        if not wells_data:
            return go.Figure().update_layout(title="No data available")

        x = np.array([w["x_coord"] for w in wells_data])
        y = np.array([w["y_coord"] for w in wells_data])
        z = np.array([w["md_base"] - w["md_top"] for w in wells_data])
        names = [w.get("well_name", "") for w in wells_data]

        xi, yi, zi = cls.interpolate_grid(x, y, z, method, resolution)
        return cls.build_contour_figure(
            xi, yi, zi, x, y, z, names,
            title=f"Isopach Map — {formation_top} to {formation_base}",
            colorscale=colorscale,
            z_label="Thickness (ft)",
        )

    # --- Kriging & IDW interpolation ---

    @staticmethod
    def interpolate_grid_kriging(x: np.ndarray, y: np.ndarray, z: np.ndarray,
                                 model: str = "spherical", sill: float = None,
                                 range_val: float = None, nugget: float = None,
                                 resolution: int = 100) -> tuple:
        """Interpolate using Ordinary Kriging (pykrige).

        model: 'spherical', 'exponential', 'gaussian'
        If sill/range/nugget are None, auto-fit is used.
        """
        from pykrige.ok import OrdinaryKriging

        variogram_params = {}
        if sill is not None and range_val is not None and nugget is not None:
            variogram_params = {
                "variogram_parameters": {
                    "sill": sill, "range": range_val, "nugget": nugget,
                }
            }

        padding = 0.1
        x_range = x.max() - x.min() if x.max() != x.min() else 1.0
        y_range = y.max() - y.min() if y.max() != y.min() else 1.0

        xi = np.linspace(x.min() - x_range * padding,
                         x.max() + x_range * padding, resolution)
        yi = np.linspace(y.min() - y_range * padding,
                         y.max() + y_range * padding, resolution)

        ok = OrdinaryKriging(
            x, y, z,
            variogram_model=model,
            verbose=False,
            enable_plotting=False,
            **variogram_params,
        )
        zi, ss = ok.execute("grid", xi, yi)
        return xi, yi, np.array(zi)

    @staticmethod
    def interpolate_grid_idw(x: np.ndarray, y: np.ndarray, z: np.ndarray,
                             power: float = 2.0,
                             resolution: int = 100) -> tuple:
        """Inverse Distance Weighting interpolation (pure numpy)."""
        padding = 0.1
        x_range = x.max() - x.min() if x.max() != x.min() else 1.0
        y_range = y.max() - y.min() if y.max() != y.min() else 1.0

        xi = np.linspace(x.min() - x_range * padding,
                         x.max() + x_range * padding, resolution)
        yi = np.linspace(y.min() - y_range * padding,
                         y.max() + y_range * padding, resolution)
        xi_grid, yi_grid = np.meshgrid(xi, yi)

        zi = np.zeros_like(xi_grid)
        for i in range(xi_grid.shape[0]):
            for j in range(xi_grid.shape[1]):
                dx = x - xi_grid[i, j]
                dy = y - yi_grid[i, j]
                dist = np.sqrt(dx ** 2 + dy ** 2)
                # Avoid division by zero at exact data points
                if np.any(dist == 0):
                    zi[i, j] = z[dist == 0][0]
                else:
                    weights = 1.0 / dist ** power
                    zi[i, j] = np.sum(weights * z) / np.sum(weights)

        return xi, yi, zi

    # --- New map type builders ---

    @staticmethod
    def build_bubble_map(wells_data: list, property_key: str,
                         title: str = "Bubble Map",
                         colorscale: str = "Viridis") -> go.Figure:
        """Build a bubble map — circles sized by a numeric property.

        wells_data: list of dicts with x_coord, y_coord, well_name, and property_key.
        """
        if not wells_data:
            return go.Figure().update_layout(title="No data available")

        x = [w["x_coord"] for w in wells_data]
        y = [w["y_coord"] for w in wells_data]
        names = [w.get("well_name", "") for w in wells_data]
        values = [w.get(property_key, 0) or 0 for w in wells_data]

        max_val = max(values) if values and max(values) > 0 else 1
        sizes = [max(5, (v / max_val) * 50) for v in values]

        fig = go.Figure()
        fig.add_trace(go.Scatter(
            x=x, y=y,
            mode="markers+text",
            marker=dict(
                size=sizes,
                color=values,
                colorscale=colorscale,
                showscale=True,
                colorbar=dict(title=property_key),
                line=dict(width=1, color="black"),
            ),
            text=names,
            textposition="top center",
            textfont=dict(size=9),
            customdata=values,
            hovertemplate="%{text}<br>X: %{x:.1f}<br>Y: %{y:.1f}<br>"
                          + f"{property_key}: " + "%{customdata:.1f}<extra></extra>",
            name="Wells",
        ))

        fig.update_layout(
            title=title,
            xaxis_title="X", yaxis_title="Y",
            xaxis=dict(scaleanchor="y", scaleratio=1),
            height=700,
            margin=dict(l=60, r=20, t=50, b=60),
        )
        return fig

    @staticmethod
    def build_posted_values_map(wells_data: list, property_key: str,
                                title: str = "Posted Values Map") -> go.Figure:
        """Build a posted values map — numeric values displayed at well locations."""
        if not wells_data:
            return go.Figure().update_layout(title="No data available")

        x = [w["x_coord"] for w in wells_data]
        y = [w["y_coord"] for w in wells_data]
        names = [w.get("well_name", "") for w in wells_data]
        values = [w.get(property_key, 0) or 0 for w in wells_data]

        fig = go.Figure()

        # Well spots
        fig.add_trace(go.Scatter(
            x=x, y=y,
            mode="markers",
            marker=dict(size=8, color="black", symbol="circle"),
            hovertemplate="%{customdata[0]}<br>X: %{x:.1f}<br>Y: %{y:.1f}<br>"
                          + f"{property_key}: " + "%{customdata[1]:.2f}<extra></extra>",
            customdata=list(zip(names, values)),
            name="Wells",
        ))

        # Posted values as annotations
        for xi, yi, name, val in zip(x, y, names, values):
            fig.add_annotation(
                x=xi, y=yi,
                text=f"<b>{name}</b><br>{val:.1f}",
                showarrow=False,
                yshift=20,
                font=dict(size=10),
            )

        fig.update_layout(
            title=title,
            xaxis_title="X", yaxis_title="Y",
            xaxis=dict(scaleanchor="y", scaleratio=1),
            height=700,
            margin=dict(l=60, r=20, t=50, b=60),
        )
        return fig

    @staticmethod
    def build_pie_chart_map(wells_data: list,
                            title: str = "Pie Chart Map") -> go.Figure:
        """Build a pie chart map — pie wedges at well locations showing oil/gas/water ratios.

        wells_data: list of dicts with x_coord, y_coord, well_name,
                    cum_oil, cum_gas, cum_water.
        """
        if not wells_data:
            return go.Figure().update_layout(title="No data available")

        fig = go.Figure()

        # Find plot range for sizing
        xs = [w["x_coord"] for w in wells_data]
        ys = [w["y_coord"] for w in wells_data]
        x_range = max(xs) - min(xs) if len(xs) > 1 else 100
        y_range = max(ys) - min(ys) if len(ys) > 1 else 100
        radius = min(x_range, y_range) * 0.04

        colors = {"oil": "green", "gas": "red", "water": "blue"}

        for w in wells_data:
            cx, cy = w["x_coord"], w["y_coord"]
            oil = w.get("cum_oil", 0) or 0
            gas = w.get("cum_gas", 0) or 0
            water = w.get("cum_water", 0) or 0
            total = oil + gas + water
            if total <= 0:
                # Just show a marker
                fig.add_trace(go.Scatter(
                    x=[cx], y=[cy], mode="markers",
                    marker=dict(size=8, color="gray"),
                    showlegend=False,
                    hovertemplate=f"{w.get('well_name','')}<br>No production<extra></extra>",
                ))
                continue

            # Draw pie wedges as filled shapes using arc approximation
            fractions = [
                ("oil", oil / total),
                ("gas", gas / total),
                ("water", water / total),
            ]
            start_angle = 0
            for fluid, frac in fractions:
                if frac <= 0:
                    continue
                end_angle = start_angle + frac * 2 * np.pi
                # Generate arc points
                n_pts = max(3, int(frac * 30))
                angles = np.linspace(start_angle, end_angle, n_pts)
                px = [cx] + [cx + radius * np.cos(a) for a in angles] + [cx]
                py = [cy] + [cy + radius * np.sin(a) for a in angles] + [cy]

                fig.add_trace(go.Scatter(
                    x=px, y=py,
                    fill="toself",
                    fillcolor=colors.get(fluid, "gray"),
                    line=dict(width=0.5, color="black"),
                    showlegend=False,
                    hovertemplate=(
                        f"{w.get('well_name','')}<br>"
                        f"{fluid}: {frac*100:.1f}%<br>"
                        f"Oil: {oil:,.0f} | Gas: {gas:,.0f} | Water: {water:,.0f}"
                        f"<extra></extra>"
                    ),
                ))
                start_angle = end_angle

            # Well name label
            fig.add_annotation(
                x=cx, y=cy + radius * 1.3,
                text=w.get("well_name", ""),
                showarrow=False,
                font=dict(size=9),
            )

        fig.update_layout(
            title=title,
            xaxis_title="X", yaxis_title="Y",
            xaxis=dict(scaleanchor="y", scaleratio=1),
            height=700,
            margin=dict(l=60, r=20, t=50, b=60),
        )
        return fig

    @staticmethod
    def build_grid_property_map(xi: np.ndarray, yi: np.ndarray, zi: np.ndarray,
                                x_wells: np.ndarray, y_wells: np.ndarray,
                                names: list, title: str = "Grid Property Map",
                                colorscale: str = "Viridis") -> go.Figure:
        """Build a heatmap from an interpolated grid with well overlay."""
        fig = go.Figure()

        fig.add_trace(go.Heatmap(
            x=xi, y=yi, z=zi,
            colorscale=colorscale,
            colorbar=dict(title="Value"),
        ))

        fig.add_trace(go.Scatter(
            x=x_wells, y=y_wells,
            mode="markers+text",
            marker=dict(size=8, color="black", symbol="circle"),
            text=names,
            textposition="top center",
            textfont=dict(size=9, color="white"),
            name="Wells",
        ))

        fig.update_layout(
            title=title,
            xaxis_title="X", yaxis_title="Y",
            xaxis=dict(scaleanchor="y", scaleratio=1),
            height=700,
            margin=dict(l=60, r=20, t=50, b=60),
        )
        return fig
