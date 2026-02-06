"""Cross Section page — multi-well structural/stratigraphic cross sections."""

import dash
from dash import html, dcc, callback, Input, Output, State, no_update
import dash_bootstrap_components as dbc
import numpy as np

from database.repositories import (
    ProjectRepository, WellRepository, CurveRepository, TopsRepository,
)
from components.cross_section import CrossSectionBuilder

dash.register_page(__name__, path="/cross-section", name="Cross Section")

project_repo = ProjectRepository()
well_repo = WellRepository()
curve_repo = CurveRepository()
tops_repo = TopsRepository()

layout = dbc.Container([
    dbc.Row([
        # Sidebar
        dbc.Col([
            html.H5("Cross Section", className="mt-3"),

            dbc.Label("Project"),
            dbc.Select(id="xs-project-select", placeholder="Select project..."),

            dbc.Label("Wells (select in order)", className="mt-2"),
            dcc.Dropdown(id="xs-well-select", multi=True,
                         placeholder="Select wells..."),

            html.Hr(),

            dbc.Label("Mode"),
            dbc.RadioItems(
                id="xs-mode",
                options=[
                    {"label": "Structural", "value": "structural"},
                    {"label": "Stratigraphic", "value": "stratigraphic"},
                ],
                value="structural",
                className="mb-2",
            ),

            html.Div(id="xs-datum-div", children=[
                dbc.Label("Datum Formation"),
                dbc.Select(id="xs-datum-formation",
                           placeholder="Select datum..."),
            ], style={"display": "none"}),

            html.Hr(),

            dbc.Label("Curves to Display"),
            dcc.Checklist(
                id="xs-curves-checklist",
                options=[
                    {"label": "GR", "value": "GR"},
                    {"label": "ILD/RT", "value": "ILD"},
                    {"label": "RHOB", "value": "RHOB"},
                    {"label": "NPHI", "value": "NPHI"},
                    {"label": "VSHALE", "value": "VSHALE"},
                    {"label": "PHIE", "value": "PHIE"},
                    {"label": "SW", "value": "SW"},
                ],
                value=["GR"],
                className="mb-2",
            ),

            dbc.Label("Formations to Correlate"),
            dcc.Dropdown(id="xs-formations-checklist", multi=True,
                         placeholder="Select formations..."),

            dbc.Label("Spacing", className="mt-2"),
            dbc.RadioItems(
                id="xs-spacing",
                options=[
                    {"label": "Uniform", "value": "uniform"},
                    {"label": "Proportional", "value": "proportional"},
                ],
                value="uniform",
                className="mb-2",
            ),

            dbc.Button("Generate", id="xs-generate-btn", color="primary",
                        className="mt-3 w-100", size="lg"),

            dbc.Alert(id="xs-alert", is_open=False, duration=4000,
                      className="mt-2"),

        ], md=3, className="border-end bg-light",
           style={"maxHeight": "calc(100vh - 56px)", "overflowY": "auto"}),

        # Main area
        dbc.Col([
            dcc.Loading(
                dcc.Graph(id="xs-plot",
                          style={"height": "calc(100vh - 70px)"}),
                type="circle",
            ),
        ], md=9),
    ]),
], fluid=True, className="px-0")


@callback(
    Output("xs-project-select", "options"),
    Output("xs-project-select", "value"),
    Input("xs-project-select", "id"),
    State("session-project-id", "data"),
)
def load_projects(_, session_pid):
    projects = project_repo.get_all()
    options = [{"label": p["name"], "value": str(p["id"])} for p in projects]
    value = str(session_pid) if session_pid else (
        options[0]["value"] if options else None)
    return options, value


@callback(
    Output("xs-well-select", "options"),
    Output("xs-formations-checklist", "options"),
    Output("xs-datum-formation", "options"),
    Input("xs-project-select", "value"),
)
def load_wells_and_formations(project_id):
    if not project_id:
        return [], [], []
    pid = int(project_id)
    wells = well_repo.get_by_project(pid)
    w_opts = [{"label": w["name"], "value": str(w["id"])} for w in wells]

    formations = tops_repo.get_formations_in_project(pid)
    f_opts = [{"label": f, "value": f} for f in formations]

    return w_opts, f_opts, f_opts


@callback(
    Output("xs-datum-div", "style"),
    Input("xs-mode", "value"),
)
def toggle_datum(mode):
    if mode == "stratigraphic":
        return {"display": "block"}
    return {"display": "none"}


@callback(
    Output("xs-plot", "figure"),
    Output("xs-alert", "children"),
    Output("xs-alert", "color"),
    Output("xs-alert", "is_open"),
    Input("xs-generate-btn", "n_clicks"),
    State("xs-project-select", "value"),
    State("xs-well-select", "value"),
    State("xs-mode", "value"),
    State("xs-datum-formation", "value"),
    State("xs-curves-checklist", "value"),
    State("xs-formations-checklist", "value"),
    State("xs-spacing", "value"),
    prevent_initial_call=True,
)
def generate_cross_section(n_clicks, project_id, well_ids, mode,
                           datum_formation, curves_display,
                           formations_correlate, spacing):
    import plotly.graph_objects as go

    if not project_id or not well_ids or len(well_ids) < 2:
        return (go.Figure().update_layout(title="Select at least 2 wells"),
                "Select at least 2 wells", "warning", True)

    wells = []
    for wid_str in well_ids:
        wid = int(wid_str)
        well_info = well_repo.get_by_id(wid)
        if not well_info:
            continue

        # Load curves
        well_curves = {}
        all_curves = curve_repo.get_curves_for_well(wid)
        for c in all_curves:
            mnem = c["mnemonic"]
            if curves_display and mnem in curves_display:
                depth_arr, data_arr = curve_repo.get_curve_data(c["id"])
                if depth_arr is not None:
                    well_curves[mnem] = {"depth": depth_arr, "data": data_arr}

        # Load tops
        well_tops = tops_repo.get_by_well(wid)
        tops_list = [{"formation": t["formation"], "md_top": t["md_top"]}
                     for t in well_tops]

        wells.append({
            "name": well_info["name"],
            "kb": well_info.get("kb", 0),
            "x_coord": well_info.get("x_coord"),
            "y_coord": well_info.get("y_coord"),
            "curves": well_curves,
            "tops": tops_list,
        })

    if len(wells) < 2:
        return (go.Figure().update_layout(title="Insufficient well data"),
                "Need at least 2 wells with data", "warning", True)

    fig = CrossSectionBuilder.build(
        wells=wells,
        mode=mode,
        datum_formation=datum_formation,
        curves_to_display=curves_display or ["GR"],
        formations_to_correlate=formations_correlate or [],
        spacing=spacing,
    )

    return fig, "", "info", False
