"""Stateless LogPlotBuilder — takes arrays + config, returns go.Figure.

Reused by well_log_viewer, formation_tops, and petrophysics pages.
"""

import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from utils.constants import get_curve_style, TOP_COLORS


class LogPlotBuilder:
    @staticmethod
    def build(tracks: list, depth: np.ndarray = None,
              tops: list = None, height: int = 900,
              title: str = "") -> go.Figure:
        """Build a multi-track well log figure.

        Args:
            tracks: list of track dicts, each with:
                - curves: list of curve dicts {mnemonic, depth, data, color?, width?, scale?}
                - label: track header label (optional)
                - fill: list of fill dicts {mnemonic, color, direction} (optional)
            depth: shared depth array (optional, curves can carry their own)
            tops: list of top dicts {formation, md_top, color} for horizontal lines
            height: figure height in pixels
            title: plot title

        Returns:
            go.Figure with subplots arranged as tracks sharing depth (y-axis).
        """
        n_tracks = len(tracks)
        if n_tracks == 0:
            return go.Figure().update_layout(title="No tracks configured")

        # Create subplots sharing Y axis
        fig = make_subplots(
            rows=1, cols=n_tracks,
            shared_yaxes=True,
            horizontal_spacing=0.02,
        )

        for t_idx, track in enumerate(tracks):
            col = t_idx + 1
            curves = track.get("curves", [])
            label = track.get("label", f"Track {col}")
            fills = track.get("fill", [])

            for curve in curves:
                mnemonic = curve.get("mnemonic", "")
                style = get_curve_style(mnemonic)

                c_depth = curve.get("depth", depth)
                c_data = curve.get("data")
                if c_depth is None or c_data is None:
                    continue

                color = curve.get("color", style["color"])
                width = curve.get("width", style["width"])
                scale = curve.get("scale", style.get("scale", "linear"))
                c_min = curve.get("min", style.get("min"))
                c_max = curve.get("max", style.get("max"))

                fig.add_trace(
                    go.Scatter(
                        x=c_data, y=c_depth,
                        mode="lines",
                        name=mnemonic,
                        line=dict(color=color, width=width),
                        hovertemplate=f"{mnemonic}: %{{x:.3f}}<br>Depth: %{{y:.2f}}<extra></extra>",
                    ),
                    row=1, col=col,
                )

                # Configure x-axis for this track
                xaxis_key = f"xaxis{col}" if col > 1 else "xaxis"
                axis_update = {"title_text": label}
                if scale == "log":
                    axis_update["type"] = "log"
                if c_min is not None and c_max is not None:
                    axis_update["range"] = (
                        [np.log10(max(c_min, 1e-6)), np.log10(max(c_max, 1e-6))]
                        if scale == "log"
                        else [c_min, c_max]
                    )
                axis_update["side"] = "top"
                axis_update["showgrid"] = True
                axis_update["gridcolor"] = "lightgray"
                fig.update_layout(**{xaxis_key: axis_update})

            # GR fill (shade between curve and clean line)
            for fill_spec in fills:
                fill_mnemonic = fill_spec.get("mnemonic", "")
                # Find matching curve data
                for curve in curves:
                    if curve.get("mnemonic") == fill_mnemonic:
                        c_depth = curve.get("depth", depth)
                        c_data = curve.get("data")
                        if c_depth is None or c_data is None:
                            break
                        fill_color = fill_spec.get("color", "rgba(0,128,0,0.3)")
                        fill_dir = fill_spec.get("direction", "tozerox")
                        fig.add_trace(
                            go.Scatter(
                                x=c_data, y=c_depth,
                                fill=fill_dir,
                                fillcolor=fill_color,
                                line=dict(width=0),
                                showlegend=False,
                                hoverinfo="skip",
                            ),
                            row=1, col=col,
                        )
                        break

        # Formation top lines
        if tops:
            for i, top in enumerate(tops):
                color = top.get("color", TOP_COLORS[i % len(TOP_COLORS)])
                for col in range(1, n_tracks + 1):
                    fig.add_hline(
                        y=top["md_top"],
                        line_dash="dash",
                        line_color=color,
                        line_width=1.5,
                        annotation_text=top["formation"] if col == 1 else None,
                        annotation_position="top left" if col == 1 else None,
                        annotation_font_size=9,
                        annotation_font_color=color,
                        row=1, col=col,
                    )

        # Global layout
        fig.update_layout(
            height=height,
            title_text=title,
            yaxis=dict(
                autorange="reversed",
                title_text="Depth (ft)",
                showgrid=True,
                gridcolor="lightgray",
            ),
            margin=dict(l=60, r=20, t=80, b=40),
            showlegend=True,
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="left", x=0),
            plot_bgcolor="white",
            hovermode="closest",
        )

        return fig
