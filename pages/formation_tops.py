"""Formation Tops page — click-to-pick tops on logs, CRUD table, CSV export."""

import dash
from dash import html, dcc, callback, Input, Output, State, dash_table, no_update, ctx
import dash_bootstrap_components as dbc
import numpy as np

from database.repositories import (
    ProjectRepository, WellRepository, CurveRepository, TopsRepository,
)
from components.log_plot import LogPlotBuilder
from services.export_service import ExportService
from utils.constants import get_curve_style

dash.register_page(__name__, path="/formation-tops", name="Formation Tops")

well_repo = WellRepository()
curve_repo = CurveRepository()
tops_repo = TopsRepository()
project_repo = ProjectRepository()

layout = dbc.Container([
    dbc.Row([
        # Sidebar
        dbc.Col([
            html.H5("Formation Tops", className="mt-3"),

            dbc.Label("Project"),
            dbc.Select(id="ft-project-select", placeholder="Select project..."),

            dbc.Label("Well", className="mt-2"),
            dbc.Select(id="ft-well-select", placeholder="Select well..."),

            html.Hr(),

            # Pick mode controls
            dbc.Card([
                dbc.CardHeader("Pick Mode"),
                dbc.CardBody([
                    dbc.Switch(id="ft-pick-mode", label="Enable Picking", value=False),
                    dbc.Label("Formation Name", className="mt-2"),
                    dbc.Input(id="ft-formation-name", placeholder="e.g., Top Cretaceous"),
                    dbc.Label("Confidence", className="mt-2"),
                    dbc.Select(
                        id="ft-confidence",
                        options=[
                            {"label": "High", "value": "high"},
                            {"label": "Medium", "value": "medium"},
                            {"label": "Low", "value": "low"},
                        ],
                        value="medium",
                    ),
                ]),
            ], className="mb-3"),

            # Manual entry
            dbc.Card([
                dbc.CardHeader("Manual Entry"),
                dbc.CardBody([
                    dbc.Label("MD Top"),
                    dbc.Input(id="ft-md-top-input", type="number", placeholder="Depth"),
                    dbc.Label("MD Base (optional)", className="mt-2"),
                    dbc.Input(id="ft-md-base-input", type="number", placeholder="Depth"),
                    dbc.Button("Add Top", id="ft-add-manual-btn", color="primary",
                                className="mt-2 w-100"),
                ]),
            ], className="mb-3"),

            dbc.Button("Export CSV", id="ft-export-btn", color="secondary",
                        className="w-100"),
            dcc.Download(id="ft-csv-download"),

        ], md=3, className="border-end bg-light",
           style={"maxHeight": "calc(100vh - 56px)", "overflowY": "auto"}),

        # Main area
        dbc.Col([
            dbc.Row([
                dbc.Col([
                    dcc.Loading(
                        dcc.Graph(id="ft-log-plot",
                                  style={"height": "calc(100vh - 250px)"}),
                        type="circle",
                    ),
                ], md=12),
            ]),
            dbc.Row([
                dbc.Col([
                    html.H6("Formation Tops Table", className="mt-2"),
                    dash_table.DataTable(
                        id="ft-tops-table",
                        columns=[
                            {"name": "ID", "id": "id"},
                            {"name": "Formation", "id": "formation", "editable": True},
                            {"name": "MD Top", "id": "md_top", "type": "numeric", "editable": True},
                            {"name": "MD Base", "id": "md_base", "type": "numeric", "editable": True},
                            {"name": "Confidence", "id": "confidence", "editable": True,
                             "presentation": "dropdown"},
                            {"name": "Source", "id": "source"},
                        ],
                        data=[],
                        editable=True,
                        row_deletable=True,
                        dropdown={
                            "confidence": {
                                "options": [
                                    {"label": "High", "value": "high"},
                                    {"label": "Medium", "value": "medium"},
                                    {"label": "Low", "value": "low"},
                                ]
                            }
                        },
                        page_size=10,
                        style_table={"overflowX": "auto"},
                        style_cell={"textAlign": "left", "padding": "6px", "fontSize": "12px"},
                        style_header={"fontWeight": "bold", "backgroundColor": "#f8f9fa"},
                    ),
                ], md=12),
            ]),
        ], md=9),
    ]),

    dcc.Store(id="ft-refresh-trigger", data=0),
], fluid=True, className="px-0")


@callback(
    Output("ft-project-select", "options"),
    Output("ft-project-select", "value"),
    Input("ft-project-select", "id"),
    State("session-project-id", "data"),
)
def load_projects(_, session_pid):
    projects = project_repo.get_all()
    options = [{"label": p["name"], "value": str(p["id"])} for p in projects]
    value = str(session_pid) if session_pid else (options[0]["value"] if options else None)
    return options, value


@callback(
    Output("ft-well-select", "options"),
    Output("ft-well-select", "value"),
    Input("ft-project-select", "value"),
    Input("session-well-id", "data"),
)
def load_wells(project_id, session_wid):
    if not project_id:
        return [], None
    wells = well_repo.get_by_project(int(project_id))
    options = [{"label": w["name"], "value": str(w["id"])} for w in wells]
    value = str(session_wid) if session_wid else (options[0]["value"] if options else None)
    return options, value


@callback(
    Output("ft-tops-table", "data"),
    Output("ft-refresh-trigger", "data"),
    Input("ft-well-select", "value"),
    Input("ft-log-plot", "clickData"),
    Input("ft-add-manual-btn", "n_clicks"),
    Input("ft-tops-table", "data_timestamp"),
    Input("ft-tops-table", "data_previous"),
    Input("ft-refresh-trigger", "data"),
    State("ft-pick-mode", "value"),
    State("ft-formation-name", "value"),
    State("ft-confidence", "value"),
    State("ft-md-top-input", "value"),
    State("ft-md-base-input", "value"),
    State("ft-tops-table", "data"),
    prevent_initial_call=False,
)
def manage_tops(well_id, click_data, add_clicks, data_ts, data_prev,
                trigger, pick_mode, formation_name, confidence,
                md_top_input, md_base_input, table_data):
    triggered = ctx.triggered_id

    if not well_id:
        return [], trigger or 0

    wid = int(well_id)

    # Handle click-to-pick
    if triggered == "ft-log-plot" and click_data and pick_mode:
        point = click_data["points"][0]
        picked_depth = point.get("y")
        if picked_depth is not None and formation_name and formation_name.strip():
            tops_repo.create(
                well_id=wid,
                formation=formation_name.strip(),
                md_top=float(picked_depth),
                confidence=confidence or "medium",
                source="picked",
            )

    # Handle manual add
    if triggered == "ft-add-manual-btn" and formation_name and md_top_input is not None:
        tops_repo.create(
            well_id=wid,
            formation=formation_name.strip(),
            md_top=float(md_top_input),
            md_base=float(md_base_input) if md_base_input is not None else None,
            confidence=confidence or "medium",
            source="manual",
        )

    # Handle row deletion (data_previous has more rows than current data)
    if triggered == "ft-tops-table" and data_prev is not None and table_data is not None:
        if len(data_prev) > len(table_data):
            current_ids = {r["id"] for r in table_data}
            for r in data_prev:
                if r["id"] not in current_ids:
                    tops_repo.delete(r["id"])

    # Handle inline edits
    if triggered == "ft-tops-table" and data_ts and table_data:
        for row in table_data:
            tops_repo.update(
                row["id"],
                formation=row.get("formation", ""),
                md_top=float(row["md_top"]) if row.get("md_top") is not None else 0,
                md_base=float(row["md_base"]) if row.get("md_base") else None,
                confidence=row.get("confidence", "medium"),
            )

    tops = tops_repo.get_by_well(wid)
    return tops, (trigger or 0) + 1


@callback(
    Output("ft-log-plot", "figure"),
    Input("ft-well-select", "value"),
    Input("ft-refresh-trigger", "data"),
    State("ft-pick-mode", "value"),
)
def update_log_plot(well_id, trigger, pick_mode):
    if not well_id:
        return LogPlotBuilder.build([], title="Select a well")

    wid = int(well_id)
    well = well_repo.get_by_id(wid)
    well_name = well["name"] if well else ""

    # Build a default GR + Resistivity + Porosity display
    tracks = []
    for mnemonics, label in [
        (["GR"], "GR"),
        (["ILD", "LLD", "RT"], "Resistivity"),
        (["RHOB", "NPHI"], "Porosity"),
    ]:
        curves = []
        for m in mnemonics:
            depth, data = curve_repo.get_curve_data_by_mnemonic(wid, m)
            if depth is not None:
                style = get_curve_style(m)
                curves.append({
                    "mnemonic": m, "depth": depth, "data": data,
                    "color": style["color"], "width": style["width"],
                    "scale": style.get("scale", "linear"),
                    "min": style.get("min"), "max": style.get("max"),
                })
        if curves:
            fill = [{"mnemonic": "GR", "color": "rgba(0,128,0,0.2)", "direction": "tozerox"}] if label == "GR" else []
            tracks.append({"curves": curves, "label": label, "fill": fill})

    if not tracks:
        return LogPlotBuilder.build([], title=f"{well_name} — No curves available")

    # Load tops
    raw_tops = tops_repo.get_by_well(wid)
    tops = [{"formation": t["formation"], "md_top": t["md_top"], "md_base": t.get("md_base")} for t in raw_tops]

    title = f"{well_name} — {'PICK MODE' if pick_mode else 'View Mode'}"
    fig = LogPlotBuilder.build(tracks, tops=tops, title=title)

    if pick_mode:
        fig.update_layout(clickmode="event+select")

    return fig


@callback(
    Output("ft-csv-download", "data"),
    Input("ft-export-btn", "n_clicks"),
    State("ft-project-select", "value"),
    prevent_initial_call=True,
)
def export_csv(n_clicks, project_id):
    if not project_id:
        return no_update
    tops = tops_repo.get_by_project(int(project_id))
    csv_str = ExportService.tops_to_csv(tops)
    return dict(content=csv_str, filename="formation_tops.csv")
