"""Cross Section Builder — stateless multi-well cross section figure.

Same pattern as LogPlotBuilder: takes data + config, returns go.Figure.
"""

import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from utils.constants import get_curve_style, TOP_COLORS


class CrossSectionBuilder:
    @staticmethod
    def build(wells: list, mode: str = "structural",
              datum_formation: str = None,
              curves_to_display: list = None,
              formations_to_correlate: list = None,
              spacing: str = "uniform",
              height: int = 800) -> go.Figure:
        """Build a cross section figure.

        Args:
            wells: ordered list of well dicts, each with:
                - name: well name
                - kb: Kelly Bushing elevation
                - curves: dict of mnemonic -> {depth, data}
                - tops: list of {formation, md_top} dicts
                - x_coord, y_coord: (optional, for proportional spacing)
            mode: "structural" or "stratigraphic"
            datum_formation: formation name for stratigraphic datum
            curves_to_display: list of curve mnemonics to plot
            formations_to_correlate: list of formation names to draw lines
            spacing: "uniform" or "proportional"
            height: figure height in pixels

        Returns:
            go.Figure with one subplot column per well.
        """
        n_wells = len(wells)
        if n_wells == 0:
            return go.Figure().update_layout(title="No wells selected")

        if curves_to_display is None:
            curves_to_display = ["GR"]
        if formations_to_correlate is None:
            formations_to_correlate = []

        # Determine datum offsets for stratigraphic mode
        datum_offsets = {}
        if mode == "stratigraphic" and datum_formation:
            for i, w in enumerate(wells):
                for top in w.get("tops", []):
                    if top["formation"] == datum_formation:
                        datum_offsets[i] = top["md_top"]
                        break
                if i not in datum_offsets:
                    datum_offsets[i] = 0  # No datum pick — use 0

        # Create subplots — one column per well
        fig = make_subplots(
            rows=1, cols=n_wells,
            shared_yaxes=True,
            horizontal_spacing=0.01,
            subplot_titles=[w.get("name", f"Well {i+1}") for i, w in enumerate(wells)],
        )

        # Global depth range tracking
        all_depths = []

        for i, w in enumerate(wells):
            col = i + 1
            kb = w.get("kb", 0) or 0
            tops = w.get("tops", [])
            curves = w.get("curves", {})

            for mnem in curves_to_display:
                if mnem not in curves:
                    continue
                c = curves[mnem]
                depth = np.array(c["depth"])
                data = np.array(c["data"])

                # Convert depth based on mode
                if mode == "structural":
                    display_depth = kb - depth  # TVDSS
                elif mode == "stratigraphic" and i in datum_offsets:
                    display_depth = depth - datum_offsets[i]
                else:
                    display_depth = depth

                all_depths.extend(display_depth.tolist())

                style = get_curve_style(mnem)
                fig.add_trace(
                    go.Scatter(
                        x=data, y=display_depth,
                        mode="lines",
                        name=f"{mnem}" if i == 0 else None,
                        showlegend=(i == 0),
                        line=dict(
                            color=style.get("color", "black"),
                            width=style.get("width", 1.5),
                        ),
                        hovertemplate=(
                            f"{w.get('name','')}<br>"
                            f"{mnem}: %{{x:.3f}}<br>"
                            f"Depth: %{{y:.2f}}<extra></extra>"
                        ),
                    ),
                    row=1, col=col,
                )

            # Formation top lines within each well column
            for t_idx, top in enumerate(tops):
                fm = top["formation"]
                md = top["md_top"]

                if mode == "structural":
                    y_pos = kb - md
                elif mode == "stratigraphic" and i in datum_offsets:
                    y_pos = md - datum_offsets[i]
                else:
                    y_pos = md

                color = TOP_COLORS[t_idx % len(TOP_COLORS)]

                fig.add_hline(
                    y=y_pos,
                    line_dash="dash",
                    line_color=color,
                    line_width=1,
                    row=1, col=col,
                )
                # Label on first well only
                if i == 0:
                    fig.add_annotation(
                        x=0, y=y_pos,
                        text=fm,
                        showarrow=False,
                        xanchor="right",
                        xshift=-5,
                        font=dict(size=8, color=color),
                        row=1, col=col,
                    )

        # Draw correlation lines across wells for selected formations
        if formations_to_correlate and n_wells > 1:
            for fm_idx, fm_name in enumerate(formations_to_correlate):
                color = TOP_COLORS[fm_idx % len(TOP_COLORS)]
                # Collect y-positions for this formation across all wells
                positions = []
                for i, w in enumerate(wells):
                    kb = w.get("kb", 0) or 0
                    for top in w.get("tops", []):
                        if top["formation"] == fm_name:
                            md = top["md_top"]
                            if mode == "structural":
                                y_pos = kb - md
                            elif mode == "stratigraphic" and i in datum_offsets:
                                y_pos = md - datum_offsets[i]
                            else:
                                y_pos = md
                            positions.append((i, y_pos))
                            break

                # Draw line segments between adjacent wells
                for k in range(len(positions) - 1):
                    i1, y1 = positions[k]
                    i2, y2 = positions[k + 1]
                    # Use paper coordinates for x spanning between subplot columns
                    x1_paper = (i1 + 0.5) / n_wells
                    x2_paper = (i2 + 0.5) / n_wells
                    fig.add_shape(
                        type="line",
                        xref="paper", yref="y",
                        x0=x1_paper, y0=y1,
                        x1=x2_paper, y1=y2,
                        line=dict(color=color, width=2, dash="dot"),
                    )

        # Configure axes
        if mode == "structural":
            y_title = "TVDSS (ft)"
            y_reversed = True
        elif mode == "stratigraphic":
            y_title = f"Offset from {datum_formation or 'datum'} (ft)"
            y_reversed = False
        else:
            y_title = "Depth (ft)"
            y_reversed = True

        fig.update_layout(
            height=height,
            title_text="Cross Section" + (f" — {mode.title()} Mode" if mode else ""),
            yaxis=dict(
                autorange="reversed" if y_reversed else True,
                title_text=y_title,
                showgrid=True,
                gridcolor="lightgray",
            ),
            margin=dict(l=70, r=20, t=80, b=40),
            showlegend=True,
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="left", x=0),
            plot_bgcolor="white",
            hovermode="closest",
        )

        # Set x-axis titles
        for i in range(n_wells):
            xaxis_key = f"xaxis{i+1}" if i > 0 else "xaxis"
            fig.update_layout(**{xaxis_key: {
                "title_text": wells[i].get("name", ""),
                "side": "top",
                "showgrid": True,
                "gridcolor": "lightgray",
            }})

        return fig
