"""Well Log Viewer page — multi-track log display with configurable tracks."""

import dash
from dash import html, dcc, callback, Input, Output, State, no_update
import dash_bootstrap_components as dbc
import numpy as np

from database.repositories import WellRepository, CurveRepository, TopsRepository
from components.log_plot import LogPlotBuilder
from utils.constants import get_curve_style, DEFAULT_TRACK_LABELS

dash.register_page(__name__, path="/well-log-viewer", name="Log Viewer")

well_repo = WellRepository()
curve_repo = CurveRepository()
tops_repo = TopsRepository()

layout = dbc.Container([
    dbc.Row([
        # Sidebar controls
        dbc.Col([
            html.H5("Well Log Viewer", className="mt-3"),

            dbc.Label("Project"),
            dbc.Select(id="lv-project-select", placeholder="Select project..."),

            dbc.Label("Well", className="mt-2"),
            dbc.Select(id="lv-well-select", placeholder="Select well..."),

            html.Hr(),
            html.H6("Track Configuration"),
            html.P("Select curves for each track:", className="text-muted small"),

            # Track 1
            dbc.Card([
                dbc.CardHeader("Track 1: GR / Caliper"),
                dbc.CardBody([
                    dbc.Checklist(id="lv-track1-curves", options=[], value=[], inline=True),
                ]),
            ], className="mb-2"),

            # Track 2
            dbc.Card([
                dbc.CardHeader("Track 2: Resistivity"),
                dbc.CardBody([
                    dbc.Checklist(id="lv-track2-curves", options=[], value=[], inline=True),
                ]),
            ], className="mb-2"),

            # Track 3
            dbc.Card([
                dbc.CardHeader("Track 3: Porosity / Density"),
                dbc.CardBody([
                    dbc.Checklist(id="lv-track3-curves", options=[], value=[], inline=True),
                ]),
            ], className="mb-2"),

            dbc.Checklist(
                id="lv-show-tops",
                options=[{"label": " Show Formation Tops", "value": "show"}],
                value=["show"],
                className="mt-2",
            ),

            dbc.Button("Refresh Plot", id="lv-refresh-btn", color="primary",
                        className="mt-3 w-100"),
        ], md=3, className="border-end bg-light",
           style={"maxHeight": "calc(100vh - 56px)", "overflowY": "auto"}),

        # Main plot area
        dbc.Col([
            dcc.Loading(
                dcc.Graph(id="lv-log-plot", style={"height": "calc(100vh - 70px)"}),
                type="circle",
            ),
        ], md=9),
    ]),
], fluid=True, className="px-0")


@callback(
    Output("lv-project-select", "options"),
    Output("lv-project-select", "value"),
    Input("lv-project-select", "id"),  # fires on load
    State("session-project-id", "data"),
)
def load_projects(_, session_pid):
    from database.repositories import ProjectRepository
    projects = ProjectRepository().get_all()
    options = [{"label": p["name"], "value": str(p["id"])} for p in projects]
    value = str(session_pid) if session_pid else (options[0]["value"] if options else None)
    return options, value


@callback(
    Output("lv-well-select", "options"),
    Output("lv-well-select", "value"),
    Input("lv-project-select", "value"),
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
    Output("lv-track1-curves", "options"),
    Output("lv-track1-curves", "value"),
    Output("lv-track2-curves", "options"),
    Output("lv-track2-curves", "value"),
    Output("lv-track3-curves", "options"),
    Output("lv-track3-curves", "value"),
    Input("lv-well-select", "value"),
)
def populate_curve_checklists(well_id):
    if not well_id:
        return [], [], [], [], [], []

    curves = curve_repo.get_curves_for_well(int(well_id))
    all_mnemonics = [c["mnemonic"] for c in curves]

    track1_mnemonics = ["GR", "CALI", "SP", "BS", "VSHALE"]
    track2_mnemonics = ["ILD", "ILM", "LLD", "LLS", "MSFL", "RT", "RXOZ"]
    track3_mnemonics = ["RHOB", "NPHI", "DPHI", "DT", "PE", "PHIE", "SW", "PAY_FLAG"]

    def make_opts(track_list):
        available = [m for m in all_mnemonics if m in track_list]
        # Also include any curves not in any default track
        opts = [{"label": m, "value": m} for m in available]
        return opts

    def default_vals(track_list):
        available = [m for m in all_mnemonics if m in track_list]
        # Auto-select first 2 curves
        return available[:2]

    # Also show unassigned curves in track 1
    assigned = set(track1_mnemonics + track2_mnemonics + track3_mnemonics)
    unassigned = [m for m in all_mnemonics if m not in assigned]
    extra_opts = [{"label": m, "value": m} for m in unassigned]

    t1_opts = make_opts(track1_mnemonics) + extra_opts
    t2_opts = make_opts(track2_mnemonics)
    t3_opts = make_opts(track3_mnemonics)

    return (t1_opts, default_vals(track1_mnemonics),
            t2_opts, default_vals(track2_mnemonics),
            t3_opts, default_vals(track3_mnemonics))


@callback(
    Output("lv-log-plot", "figure"),
    Input("lv-refresh-btn", "n_clicks"),
    Input("lv-well-select", "value"),
    State("lv-track1-curves", "value"),
    State("lv-track2-curves", "value"),
    State("lv-track3-curves", "value"),
    State("lv-show-tops", "value"),
    prevent_initial_call=False,
)
def update_log_plot(n_clicks, well_id, t1_curves, t2_curves, t3_curves, show_tops):
    if not well_id:
        return LogPlotBuilder.build([], title="Select a well to view logs")

    wid = int(well_id)
    well = well_repo.get_by_id(wid)
    well_name = well["name"] if well else ""

    def build_track(mnemonics, label):
        curves = []
        for m in (mnemonics or []):
            depth, data = curve_repo.get_curve_data_by_mnemonic(wid, m)
            if depth is not None:
                style = get_curve_style(m)
                curves.append({
                    "mnemonic": m, "depth": depth, "data": data,
                    "color": style["color"], "width": style["width"],
                    "scale": style.get("scale", "linear"),
                    "min": style.get("min"), "max": style.get("max"),
                })
        fill = []
        if "GR" in (mnemonics or []):
            fill.append({"mnemonic": "GR", "color": "rgba(0,128,0,0.2)", "direction": "tozerox"})
        return {"curves": curves, "label": label, "fill": fill}

    tracks = []
    if t1_curves:
        tracks.append(build_track(t1_curves, "GR / Caliper"))
    if t2_curves:
        tracks.append(build_track(t2_curves, "Resistivity"))
    if t3_curves:
        tracks.append(build_track(t3_curves, "Porosity / Density"))

    if not tracks:
        tracks.append(build_track(["GR"], "GR"))

    # Formation tops
    tops = []
    if show_tops and "show" in (show_tops or []):
        raw_tops = tops_repo.get_by_well(wid)
        for t in raw_tops:
            tops.append({"formation": t["formation"], "md_top": t["md_top"], "md_base": t.get("md_base")})

    return LogPlotBuilder.build(tracks, tops=tops, title=well_name,
                                height=max(800, 900))
