"""Petrophysics page — parameter inputs, calculate, view results, save curves."""

import dash
from dash import html, dcc, callback, Input, Output, State, no_update, ctx
import dash_bootstrap_components as dbc
import numpy as np

from database.repositories import (
    ProjectRepository, WellRepository, CurveRepository, PetroParamsRepository,
    TopsRepository, OOIPRepository,
)
from services.petrophysics import PetrophysicsEngine
from services.volumetrics import VolumetricsEngine, VolumetricsInput, MonteCarloParam
from components.log_plot import LogPlotBuilder
from utils.constants import get_curve_style

dash.register_page(__name__, path="/petrophysics", name="Petrophysics")

project_repo = ProjectRepository()
well_repo = WellRepository()
curve_repo = CurveRepository()
petro_repo = PetroParamsRepository()
tops_repo = TopsRepository()
ooip_repo = OOIPRepository()

layout = dbc.Container([
    dbc.Row([
        # Sidebar controls
        dbc.Col([
            html.H5("Petrophysics", className="mt-3"),

            dbc.Label("Project"),
            dbc.Select(id="pp-project-select", placeholder="Select project..."),

            dbc.Label("Well", className="mt-2"),
            dbc.Select(id="pp-well-select", placeholder="Select well..."),

            html.Hr(),

            # Accordion for parameter groups
            dbc.Accordion([
                dbc.AccordionItem([
                    dbc.Label("GR Curve"),
                    dbc.Select(id="pp-gr-curve", placeholder="Select GR..."),
                    dbc.Label("GR Clean", className="mt-2"),
                    dbc.Input(id="pp-gr-clean", type="number", value=20, step=1),
                    dbc.Label("GR Shale", className="mt-2"),
                    dbc.Input(id="pp-gr-shale", type="number", value=120, step=1),
                    dbc.Label("Method", className="mt-2"),
                    dbc.Select(
                        id="pp-vsh-method",
                        options=[
                            {"label": "Linear", "value": "linear"},
                            {"label": "Larionov (Tertiary)", "value": "larionov_tertiary"},
                            {"label": "Larionov (Older Rocks)", "value": "larionov_old"},
                            {"label": "Clavier", "value": "clavier"},
                        ],
                        value="linear",
                    ),
                ], title="Vshale Parameters"),

                dbc.AccordionItem([
                    dbc.Label("Density Curve (RHOB)"),
                    dbc.Select(id="pp-rhob-curve", placeholder="Select RHOB..."),
                    dbc.Label("Neutron Curve (NPHI)", className="mt-2"),
                    dbc.Select(id="pp-nphi-curve", placeholder="Select NPHI..."),
                    dbc.Label("Matrix Density", className="mt-2"),
                    dbc.Input(id="pp-rho-matrix", type="number", value=2.65, step=0.01),
                    dbc.Label("Fluid Density", className="mt-2"),
                    dbc.Input(id="pp-rho-fluid", type="number", value=1.0, step=0.01),
                    dbc.Label("NPhi Matrix", className="mt-2"),
                    dbc.Input(id="pp-nphi-matrix", type="number", value=0.0, step=0.01),
                ], title="Porosity Parameters"),

                dbc.AccordionItem([
                    dbc.Label("Deep Resistivity Curve"),
                    dbc.Select(id="pp-rt-curve", placeholder="Select RT/ILD/LLD..."),
                    dbc.Label("Rw (ohm-m)", className="mt-2"),
                    dbc.Input(id="pp-rw", type="number", value=0.05, step=0.001),
                    dbc.Label("a (tortuosity)", className="mt-2"),
                    dbc.Input(id="pp-archie-a", type="number", value=1.0, step=0.1),
                    dbc.Label("m (cementation)", className="mt-2"),
                    dbc.Input(id="pp-archie-m", type="number", value=2.0, step=0.1),
                    dbc.Label("n (saturation exp.)", className="mt-2"),
                    dbc.Input(id="pp-archie-n", type="number", value=2.0, step=0.1),
                ], title="Archie Parameters"),

                dbc.AccordionItem([
                    dbc.Label("Porosity Cutoff"),
                    dbc.Input(id="pp-phi-cutoff", type="number", value=0.08, step=0.01),
                    dbc.Label("Sw Cutoff", className="mt-2"),
                    dbc.Input(id="pp-sw-cutoff", type="number", value=0.5, step=0.05),
                    dbc.Label("Vshale Cutoff", className="mt-2"),
                    dbc.Input(id="pp-vsh-cutoff", type="number", value=0.5, step=0.05),
                ], title="Net Pay Cutoffs"),
            ], always_open=True, className="mb-3"),

            dbc.Button("Calculate", id="pp-calculate-btn", color="success",
                        className="w-100 mb-2", size="lg"),
            dbc.Button("Save Curves to DB", id="pp-save-btn", color="primary",
                        className="w-100 mb-2"),
            dbc.Button("Load Saved Params", id="pp-load-btn", color="secondary",
                        className="w-100", size="sm"),

            dbc.Alert(id="pp-alert", is_open=False, duration=4000, className="mt-2"),

        ], md=3, className="border-end bg-light",
           style={"maxHeight": "calc(100vh - 56px)", "overflowY": "auto"}),

        # Main area: plot + summary
        dbc.Col([
            dcc.Loading(
                dcc.Graph(id="pp-result-plot", style={"height": "calc(100vh - 200px)"}),
                type="circle",
            ),

            # Net pay summary card
            dbc.Card([
                dbc.CardHeader("Net Pay Summary"),
                dbc.CardBody(id="pp-summary-body", children="Run calculation to see results"),
            ], className="mt-2"),

            # OOIP/OGIP Volumetrics section
            dbc.Card([
                dbc.CardHeader("OOIP / OGIP Volumetrics"),
                dbc.CardBody([
                    dbc.Row([
                        dbc.Col([
                            dbc.Label("Fluid Type"),
                            dbc.RadioItems(
                                id="pp-vol-fluid",
                                options=[
                                    {"label": "Oil", "value": "oil"},
                                    {"label": "Gas", "value": "gas"},
                                ],
                                value="oil",
                                inline=True,
                            ),
                        ], md=3),
                        dbc.Col([
                            dbc.Label("Method"),
                            dbc.RadioItems(
                                id="pp-vol-method",
                                options=[
                                    {"label": "Deterministic", "value": "deterministic"},
                                    {"label": "Monte Carlo", "value": "monte_carlo"},
                                ],
                                value="deterministic",
                                inline=True,
                            ),
                        ], md=3),
                        dbc.Col([
                            dbc.Label("Formation Zone"),
                            dbc.Select(id="pp-vol-formation",
                                       placeholder="Select zone..."),
                        ], md=3),
                        dbc.Col([
                            dbc.Label("Area (acres)"),
                            dbc.Input(id="pp-vol-area", type="number",
                                      value=40, step=1),
                        ], md=3),
                    ]),
                    dbc.Row([
                        dbc.Col([
                            dbc.Label("Bo (rb/stb)" if True else "Bg"),
                            dbc.Input(id="pp-vol-bo", type="number",
                                      value=1.2, step=0.01),
                        ], md=2),
                        dbc.Col([
                            dbc.Label("Bg (rcf/scf)"),
                            dbc.Input(id="pp-vol-bg", type="number",
                                      value=0.005, step=0.001),
                        ], md=2),
                        dbc.Col([
                            dbc.Label("Recovery Factor"),
                            dbc.Input(id="pp-vol-rf", type="number",
                                      value=0.3, step=0.05, min=0, max=1),
                        ], md=2),
                        dbc.Col([
                            dbc.Label("MC Iterations"),
                            dbc.Input(id="pp-vol-mc-n", type="number",
                                      value=10000, step=1000),
                        ], md=2),
                        dbc.Col([
                            dbc.Button("Calculate OOIP/OGIP",
                                       id="pp-vol-calc-btn", color="info",
                                       className="mt-4 w-100"),
                        ], md=4),
                    ], className="mt-2"),

                    # MC distribution controls
                    html.Div(id="pp-vol-mc-div", children=[
                        html.Hr(),
                        html.P("Monte Carlo Distribution Parameters",
                               className="fw-bold mt-2"),
                        dbc.Row([
                            dbc.Col([
                                dbc.Label("Area: Min / Mode / Max"),
                                dbc.InputGroup([
                                    dbc.Input(id="pp-mc-area-min", type="number", value=20),
                                    dbc.Input(id="pp-mc-area-mode", type="number", value=40),
                                    dbc.Input(id="pp-mc-area-max", type="number", value=80),
                                ]),
                            ], md=4),
                            dbc.Col([
                                dbc.Label("h (ft): Min / Mode / Max"),
                                dbc.InputGroup([
                                    dbc.Input(id="pp-mc-h-min", type="number", value=10),
                                    dbc.Input(id="pp-mc-h-mode", type="number", value=30),
                                    dbc.Input(id="pp-mc-h-max", type="number", value=60),
                                ]),
                            ], md=4),
                            dbc.Col([
                                dbc.Label("Phi: Min / Mode / Max"),
                                dbc.InputGroup([
                                    dbc.Input(id="pp-mc-phi-min", type="number", value=0.05, step=0.01),
                                    dbc.Input(id="pp-mc-phi-mode", type="number", value=0.12, step=0.01),
                                    dbc.Input(id="pp-mc-phi-max", type="number", value=0.25, step=0.01),
                                ]),
                            ], md=4),
                        ]),
                        dbc.Row([
                            dbc.Col([
                                dbc.Label("Sw: Min / Mode / Max"),
                                dbc.InputGroup([
                                    dbc.Input(id="pp-mc-sw-min", type="number", value=0.15, step=0.01),
                                    dbc.Input(id="pp-mc-sw-mode", type="number", value=0.35, step=0.01),
                                    dbc.Input(id="pp-mc-sw-max", type="number", value=0.60, step=0.01),
                                ]),
                            ], md=4),
                            dbc.Col([
                                dbc.Label("Bo/Bg: Min / Mode / Max"),
                                dbc.InputGroup([
                                    dbc.Input(id="pp-mc-bx-min", type="number", value=1.1, step=0.01),
                                    dbc.Input(id="pp-mc-bx-mode", type="number", value=1.2, step=0.01),
                                    dbc.Input(id="pp-mc-bx-max", type="number", value=1.4, step=0.01),
                                ]),
                            ], md=4),
                            dbc.Col([
                                dbc.Label("RF: Min / Mode / Max"),
                                dbc.InputGroup([
                                    dbc.Input(id="pp-mc-rf-min", type="number", value=0.1, step=0.05),
                                    dbc.Input(id="pp-mc-rf-mode", type="number", value=0.3, step=0.05),
                                    dbc.Input(id="pp-mc-rf-max", type="number", value=0.5, step=0.05),
                                ]),
                            ], md=4),
                        ], className="mt-2"),
                    ], style={"display": "none"}),

                    html.Hr(),
                    html.Div(id="pp-vol-results", children=""),
                    dcc.Graph(id="pp-vol-histogram",
                              style={"display": "none"}),
                ]),
            ], className="mt-2"),
        ], md=9),
    ]),

    # Store computed results
    dcc.Store(id="pp-results-store"),
], fluid=True, className="px-0")


@callback(
    Output("pp-project-select", "options"),
    Output("pp-project-select", "value"),
    Input("pp-project-select", "id"),
    State("session-project-id", "data"),
)
def load_projects(_, session_pid):
    projects = project_repo.get_all()
    options = [{"label": p["name"], "value": str(p["id"])} for p in projects]
    value = str(session_pid) if session_pid else (options[0]["value"] if options else None)
    return options, value


@callback(
    Output("pp-well-select", "options"),
    Output("pp-well-select", "value"),
    Input("pp-project-select", "value"),
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
    Output("pp-gr-curve", "options"),
    Output("pp-gr-curve", "value"),
    Output("pp-rhob-curve", "options"),
    Output("pp-rhob-curve", "value"),
    Output("pp-nphi-curve", "options"),
    Output("pp-nphi-curve", "value"),
    Output("pp-rt-curve", "options"),
    Output("pp-rt-curve", "value"),
    Input("pp-well-select", "value"),
)
def populate_curves(well_id):
    empty = ([], None)
    if not well_id:
        return *empty, *empty, *empty, *empty

    curves = curve_repo.get_curves_for_well(int(well_id))
    all_opts = [{"label": f"{c['mnemonic']} ({c['unit']})", "value": c["mnemonic"]}
                for c in curves]

    def find_default(mnemonics):
        for m in mnemonics:
            for c in curves:
                if c["mnemonic"] == m:
                    return m
        return None

    gr_val = find_default(["GR"])
    rhob_val = find_default(["RHOB"])
    nphi_val = find_default(["NPHI", "DPHI"])
    rt_val = find_default(["RT", "ILD", "LLD"])

    return (all_opts, gr_val, all_opts, rhob_val,
            all_opts, nphi_val, all_opts, rt_val)


@callback(
    Output("pp-result-plot", "figure"),
    Output("pp-summary-body", "children"),
    Output("pp-results-store", "data"),
    Output("pp-alert", "children"),
    Output("pp-alert", "color"),
    Output("pp-alert", "is_open"),
    Input("pp-calculate-btn", "n_clicks"),
    State("pp-well-select", "value"),
    State("pp-gr-curve", "value"),
    State("pp-rhob-curve", "value"),
    State("pp-nphi-curve", "value"),
    State("pp-rt-curve", "value"),
    State("pp-gr-clean", "value"),
    State("pp-gr-shale", "value"),
    State("pp-vsh-method", "value"),
    State("pp-rho-matrix", "value"),
    State("pp-rho-fluid", "value"),
    State("pp-nphi-matrix", "value"),
    State("pp-rw", "value"),
    State("pp-archie-a", "value"),
    State("pp-archie-m", "value"),
    State("pp-archie-n", "value"),
    State("pp-phi-cutoff", "value"),
    State("pp-sw-cutoff", "value"),
    State("pp-vsh-cutoff", "value"),
    prevent_initial_call=True,
)
def run_calculation(n_clicks, well_id, gr_mnem, rhob_mnem, nphi_mnem, rt_mnem,
                    gr_clean, gr_shale, vsh_method, rho_matrix, rho_fluid,
                    nphi_matrix, rw, archie_a, archie_m, archie_n,
                    phi_cutoff, sw_cutoff, vsh_cutoff):
    empty_fig = LogPlotBuilder.build([], title="No results")

    if not well_id:
        return empty_fig, "Select a well first", None, "", "info", False

    wid = int(well_id)
    well = well_repo.get_by_id(wid)
    well_name = well["name"] if well else ""

    # Load curve data
    def load_curve(mnemonic):
        if not mnemonic:
            return None, None
        return curve_repo.get_curve_data_by_mnemonic(wid, mnemonic)

    gr_depth, gr_data = load_curve(gr_mnem)
    rhob_depth, rhob_data = load_curve(rhob_mnem)
    nphi_depth, nphi_data = load_curve(nphi_mnem)
    rt_depth, rt_data = load_curve(rt_mnem)

    if gr_data is None:
        return empty_fig, "No GR curve available", None, "GR curve required", "warning", True

    depth = gr_depth  # Use GR depth as reference

    # Interpolate other curves to same depth basis
    def interp_to_depth(d, v, ref_depth):
        if d is None or v is None:
            return None
        return np.interp(ref_depth, d, v, left=np.nan, right=np.nan)

    rhob_interp = interp_to_depth(rhob_depth, rhob_data, depth)
    nphi_interp = interp_to_depth(nphi_depth, nphi_data, depth)
    rt_interp = interp_to_depth(rt_depth, rt_data, depth)

    params = {
        "gr_clean": float(gr_clean or 20),
        "gr_shale": float(gr_shale or 120),
        "vshale_method": vsh_method or "linear",
        "rho_matrix": float(rho_matrix or 2.65),
        "rho_fluid": float(rho_fluid or 1.0),
        "nphi_matrix": float(nphi_matrix or 0.0),
        "rw": float(rw or 0.05),
        "archie_a": float(archie_a or 1.0),
        "archie_m": float(archie_m or 2.0),
        "archie_n": float(archie_n or 2.0),
        "phi_cutoff": float(phi_cutoff or 0.08),
        "sw_cutoff": float(sw_cutoff or 0.5),
        "vshale_cutoff": float(vsh_cutoff or 0.5),
    }

    results = PetrophysicsEngine.run_full_analysis(
        depth, gr_data, rhob_interp, nphi_interp, rt_interp, params
    )

    # Build 5-track display
    tracks = [
        # Track 1: GR + Vshale
        {
            "label": "GR + Vsh",
            "curves": [
                {"mnemonic": "GR", "depth": depth, "data": gr_data,
                 **get_curve_style("GR")},
                {"mnemonic": "VSHALE", "depth": depth, "data": results["VSHALE"],
                 "color": "olive", "width": 1.5, "scale": "linear", "min": 0, "max": 1},
            ],
            "fill": [{"mnemonic": "GR", "color": "rgba(0,128,0,0.2)", "direction": "tozerox"}],
        },
        # Track 2: Resistivity
        {
            "label": "Resistivity",
            "curves": ([{
                "mnemonic": rt_mnem or "RT", "depth": depth, "data": rt_interp,
                **get_curve_style("RT"),
            }] if rt_interp is not None else []),
            "fill": [],
        },
        # Track 3: Porosity
        {
            "label": "Porosity",
            "curves": [
                {"mnemonic": "PHIE", "depth": depth, "data": results["PHIE"],
                 "color": "blue", "width": 1.5, "scale": "linear", "min": 0.45, "max": -0.15},
            ],
            "fill": [],
        },
        # Track 4: Sw
        {
            "label": "Sw",
            "curves": [
                {"mnemonic": "SW", "depth": depth, "data": results["SW"],
                 "color": "blue", "width": 1.5, "scale": "linear", "min": 0, "max": 1},
            ],
            "fill": [{"mnemonic": "SW", "color": "rgba(0,0,255,0.15)", "direction": "tozerox"}],
        },
        # Track 5: Pay flag
        {
            "label": "Pay Flag",
            "curves": [
                {"mnemonic": "PAY_FLAG", "depth": depth, "data": results["PAY_FLAG"],
                 "color": "gold", "width": 3.0, "scale": "linear", "min": 0, "max": 1},
            ],
            "fill": [{"mnemonic": "PAY_FLAG", "color": "rgba(255,215,0,0.4)", "direction": "tozerox"}],
        },
    ]

    # Remove empty tracks
    tracks = [t for t in tracks if t["curves"]]

    fig = LogPlotBuilder.build(tracks, title=f"{well_name} — Petrophysics Results")

    # Summary
    summary = results["summary"]
    summary_content = dbc.Row([
        dbc.Col([
            html.P([html.Strong("Gross: "), f"{summary['gross']} ft"]),
            html.P([html.Strong("Net Pay: "), f"{summary['net']} ft"]),
        ], md=4),
        dbc.Col([
            html.P([html.Strong("N/G Ratio: "), f"{summary['ng_ratio']:.3f}"]),
            html.P([html.Strong("Avg Porosity: "), f"{summary['avg_phi']:.4f}"]),
        ], md=4),
        dbc.Col([
            html.P([html.Strong("Avg Sw: "), f"{summary['avg_sw']:.4f}"]),
        ], md=4),
    ])

    # Store results for saving
    store_data = {"well_id": wid, "params": params, "has_results": True}

    return fig, summary_content, store_data, "Calculation complete!", "success", True


@callback(
    Output("pp-save-btn", "n_clicks"),
    Input("pp-save-btn", "n_clicks"),
    State("pp-results-store", "data"),
    State("pp-well-select", "value"),
    State("pp-gr-curve", "value"),
    State("pp-rhob-curve", "value"),
    State("pp-nphi-curve", "value"),
    State("pp-rt-curve", "value"),
    State("pp-gr-clean", "value"),
    State("pp-gr-shale", "value"),
    State("pp-vsh-method", "value"),
    State("pp-rho-matrix", "value"),
    State("pp-rho-fluid", "value"),
    State("pp-nphi-matrix", "value"),
    State("pp-rw", "value"),
    State("pp-archie-a", "value"),
    State("pp-archie-m", "value"),
    State("pp-archie-n", "value"),
    State("pp-phi-cutoff", "value"),
    State("pp-sw-cutoff", "value"),
    State("pp-vsh-cutoff", "value"),
    prevent_initial_call=True,
)
def save_results(n_clicks, store_data, well_id, gr_mnem, rhob_mnem, nphi_mnem,
                 rt_mnem, gr_clean, gr_shale, vsh_method, rho_matrix, rho_fluid,
                 nphi_matrix, rw, archie_a, archie_m, archie_n,
                 phi_cutoff, sw_cutoff, vsh_cutoff):
    if not store_data or not store_data.get("has_results") or not well_id:
        return no_update

    wid = int(well_id)

    # Re-run calculation to get arrays
    def load_curve(mnemonic):
        if not mnemonic:
            return None, None
        return curve_repo.get_curve_data_by_mnemonic(wid, mnemonic)

    gr_depth, gr_data = load_curve(gr_mnem)
    if gr_data is None:
        return no_update

    depth = gr_depth
    rhob_depth, rhob_data = load_curve(rhob_mnem)
    nphi_depth, nphi_data = load_curve(nphi_mnem)
    rt_depth, rt_data = load_curve(rt_mnem)

    def interp_to_depth(d, v, ref_depth):
        if d is None or v is None:
            return None
        return np.interp(ref_depth, d, v, left=np.nan, right=np.nan)

    params = {
        "gr_clean": float(gr_clean or 20),
        "gr_shale": float(gr_shale or 120),
        "vshale_method": vsh_method or "linear",
        "rho_matrix": float(rho_matrix or 2.65),
        "rho_fluid": float(rho_fluid or 1.0),
        "nphi_matrix": float(nphi_matrix or 0.0),
        "rw": float(rw or 0.05),
        "archie_a": float(archie_a or 1.0),
        "archie_m": float(archie_m or 2.0),
        "archie_n": float(archie_n or 2.0),
        "phi_cutoff": float(phi_cutoff or 0.08),
        "sw_cutoff": float(sw_cutoff or 0.5),
        "vshale_cutoff": float(vsh_cutoff or 0.5),
    }

    results = PetrophysicsEngine.run_full_analysis(
        depth, gr_data,
        interp_to_depth(rhob_depth, rhob_data, depth),
        interp_to_depth(nphi_depth, nphi_data, depth),
        interp_to_depth(rt_depth, rt_data, depth),
        params,
    )

    # Delete existing computed curves and save new ones
    curve_repo.delete_computed_curves(wid)

    for mnemonic, unit in [("VSHALE", "v/v"), ("PHIE", "v/v"),
                           ("SW", "v/v"), ("PAY_FLAG", "flag")]:
        if mnemonic in results:
            curve_repo.save_curve(
                well_id=wid,
                mnemonic=mnemonic,
                original_mnemonic=mnemonic,
                unit=unit,
                depth_data=depth,
                curve_data=results[mnemonic],
                is_computed=1,
            )

    # Save params
    petro_repo.save(wid, "default", **params)

    return no_update


@callback(
    Output("pp-gr-clean", "value"),
    Output("pp-gr-shale", "value"),
    Output("pp-vsh-method", "value"),
    Output("pp-rho-matrix", "value"),
    Output("pp-rho-fluid", "value"),
    Output("pp-nphi-matrix", "value"),
    Output("pp-rw", "value"),
    Output("pp-archie-a", "value"),
    Output("pp-archie-m", "value"),
    Output("pp-archie-n", "value"),
    Output("pp-phi-cutoff", "value"),
    Output("pp-sw-cutoff", "value"),
    Output("pp-vsh-cutoff", "value"),
    Input("pp-load-btn", "n_clicks"),
    State("pp-well-select", "value"),
    prevent_initial_call=True,
)
def load_params(n_clicks, well_id):
    if not well_id:
        return (no_update,) * 13
    p = petro_repo.get(int(well_id))
    if not p:
        return (no_update,) * 13
    return (
        p["gr_clean"], p["gr_shale"], p["vshale_method"],
        p["rho_matrix"], p["rho_fluid"], p["nphi_matrix"],
        p["rw"], p["archie_a"], p["archie_m"], p["archie_n"],
        p["phi_cutoff"], p["sw_cutoff"], p["vshale_cutoff"],
    )


# --- Volumetrics callbacks ---

@callback(
    Output("pp-vol-formation", "options"),
    Input("pp-well-select", "value"),
)
def load_vol_formations(well_id):
    if not well_id:
        return []
    tops = tops_repo.get_by_well(int(well_id))
    seen = set()
    opts = []
    for t in tops:
        fm = t["formation"]
        if fm not in seen:
            seen.add(fm)
            label = fm
            if t.get("md_base"):
                label += f" ({t['md_top']:.0f}-{t['md_base']:.0f})"
            else:
                label += f" ({t['md_top']:.0f})"
            opts.append({"label": label, "value": fm})
    return opts


@callback(
    Output("pp-vol-mc-div", "style"),
    Input("pp-vol-method", "value"),
)
def toggle_mc_controls(method):
    if method == "monte_carlo":
        return {"display": "block"}
    return {"display": "none"}


@callback(
    Output("pp-vol-results", "children"),
    Output("pp-vol-histogram", "figure"),
    Output("pp-vol-histogram", "style"),
    Input("pp-vol-calc-btn", "n_clicks"),
    State("pp-well-select", "value"),
    State("pp-project-select", "value"),
    State("pp-vol-fluid", "value"),
    State("pp-vol-method", "value"),
    State("pp-vol-formation", "value"),
    State("pp-vol-area", "value"),
    State("pp-vol-bo", "value"),
    State("pp-vol-bg", "value"),
    State("pp-vol-rf", "value"),
    State("pp-vol-mc-n", "value"),
    State("pp-results-store", "data"),
    # MC distribution params
    State("pp-mc-area-min", "value"),
    State("pp-mc-area-mode", "value"),
    State("pp-mc-area-max", "value"),
    State("pp-mc-h-min", "value"),
    State("pp-mc-h-mode", "value"),
    State("pp-mc-h-max", "value"),
    State("pp-mc-phi-min", "value"),
    State("pp-mc-phi-mode", "value"),
    State("pp-mc-phi-max", "value"),
    State("pp-mc-sw-min", "value"),
    State("pp-mc-sw-mode", "value"),
    State("pp-mc-sw-max", "value"),
    State("pp-mc-bx-min", "value"),
    State("pp-mc-bx-mode", "value"),
    State("pp-mc-bx-max", "value"),
    State("pp-mc-rf-min", "value"),
    State("pp-mc-rf-mode", "value"),
    State("pp-mc-rf-max", "value"),
    prevent_initial_call=True,
)
def calculate_volumetrics(
    n_clicks, well_id, project_id, fluid_type, method, formation,
    area, bo, bg, rf, mc_n, store_data,
    mc_area_min, mc_area_mode, mc_area_max,
    mc_h_min, mc_h_mode, mc_h_max,
    mc_phi_min, mc_phi_mode, mc_phi_max,
    mc_sw_min, mc_sw_mode, mc_sw_max,
    mc_bx_min, mc_bx_mode, mc_bx_max,
    mc_rf_min, mc_rf_mode, mc_rf_max,
):
    import plotly.graph_objects as go
    empty_fig = go.Figure()
    hidden = {"display": "none"}

    if not well_id:
        return "Select a well first", empty_fig, hidden

    wid = int(well_id)
    area = float(area or 40)
    bo = float(bo or 1.2)
    bg = float(bg or 0.005)
    rf_val = float(rf or 0.3)

    # Try to extract zone properties from computed curves
    h_val = 30.0
    phi_val = 0.12
    sw_val = 0.35

    if formation and store_data and store_data.get("has_results"):
        # Load computed curves for zone extraction
        tops = tops_repo.get_by_well(wid)
        top_match = None
        for t in tops:
            if t["formation"] == formation:
                top_match = t
                break
        if top_match:
            md_top = top_match["md_top"]
            md_base = top_match.get("md_base") or md_top + 50
            try:
                d_depth, d_phi = curve_repo.get_curve_data_by_mnemonic(wid, "PHIE")
                _, d_sw = curve_repo.get_curve_data_by_mnemonic(wid, "SW")
                _, d_pay = curve_repo.get_curve_data_by_mnemonic(wid, "PAY_FLAG")
                if d_depth is not None and d_phi is not None:
                    zone = VolumetricsEngine.extract_zone_properties(
                        d_depth, d_phi, d_sw, d_pay, md_top, md_base)
                    if zone["net_pay"] > 0:
                        h_val = zone["net_pay"]
                    if zone["avg_phi"] > 0:
                        phi_val = zone["avg_phi"]
                    if zone["avg_sw"] > 0:
                        sw_val = zone["avg_sw"]
            except Exception:
                pass

    if method == "deterministic":
        inputs = VolumetricsInput(
            area=area, h=h_val, phi=phi_val, sw=sw_val,
            bo=bo, bg=bg, rf=rf_val, fluid_type=fluid_type,
        )
        result = VolumetricsEngine.deterministic(inputs)

        if fluid_type == "oil":
            val = result["ooip"]
            label = "OOIP"
            unit = "STB"
        else:
            val = result["ogip"]
            label = "OGIP"
            unit = "SCF"

        # Save to DB
        try:
            ooip_repo.save(
                well_id=wid,
                project_id=int(project_id) if project_id else None,
                formation=formation or "",
                method="deterministic",
                ooip=result.get("ooip"),
                ogip=result.get("ogip"),
                parameters=result.get("inputs", {}),
            )
        except Exception:
            pass

        content = dbc.Card([
            dbc.CardBody([
                html.H4(f"{label}: {val:,.0f} {unit}", className="text-primary"),
                html.P(f"Area: {area} acres | h: {h_val:.1f} ft | "
                       f"Phi: {phi_val:.4f} | Sw: {sw_val:.4f} | RF: {rf_val}"),
            ]),
        ], color="light")
        return content, empty_fig, hidden

    else:  # Monte Carlo
        mc_params = {
            "area": MonteCarloParam("area", "triangular",
                                    float(mc_area_min or 20),
                                    float(mc_area_mode or 40),
                                    float(mc_area_max or 80)),
            "h": MonteCarloParam("h", "triangular",
                                 float(mc_h_min or 10),
                                 float(mc_h_mode or h_val),
                                 float(mc_h_max or 60)),
            "phi": MonteCarloParam("phi", "triangular",
                                   float(mc_phi_min or 0.05),
                                   float(mc_phi_mode or phi_val),
                                   float(mc_phi_max or 0.25)),
            "sw": MonteCarloParam("sw", "triangular",
                                  float(mc_sw_min or 0.15),
                                  float(mc_sw_mode or sw_val),
                                  float(mc_sw_max or 0.60)),
            "rf": MonteCarloParam("rf", "triangular",
                                  float(mc_rf_min or 0.1),
                                  float(mc_rf_mode or rf_val),
                                  float(mc_rf_max or 0.5)),
        }

        if fluid_type == "oil":
            mc_params["bo"] = MonteCarloParam(
                "bo", "triangular",
                float(mc_bx_min or 1.1),
                float(mc_bx_mode or bo),
                float(mc_bx_max or 1.4))
        else:
            mc_params["bg"] = MonteCarloParam(
                "bg", "triangular",
                float(mc_bx_min or 0.003),
                float(mc_bx_mode or bg),
                float(mc_bx_max or 0.008))

        mc_result = VolumetricsEngine.monte_carlo(
            mc_params, int(mc_n or 10000), fluid_type)

        label = mc_result["label"]
        unit = "STB" if fluid_type == "oil" else "SCF"

        # Save to DB
        try:
            ooip_repo.save(
                well_id=wid,
                project_id=int(project_id) if project_id else None,
                formation=formation or "",
                method="monte_carlo",
                ooip=mc_result["p50"] if fluid_type == "oil" else None,
                ogip=mc_result["p50"] if fluid_type == "gas" else None,
                parameters={
                    "p10": mc_result["p10"],
                    "p50": mc_result["p50"],
                    "p90": mc_result["p90"],
                    "mean": mc_result["mean"],
                    "n_iterations": mc_result["n_iterations"],
                },
            )
        except Exception:
            pass

        content = dbc.Row([
            dbc.Col(dbc.Card(dbc.CardBody([
                html.H5("P10"), html.H4(f"{mc_result['p10']:,.0f} {unit}"),
            ]), color="light"), md=3),
            dbc.Col(dbc.Card(dbc.CardBody([
                html.H5("P50"), html.H4(f"{mc_result['p50']:,.0f} {unit}",
                                         className="text-primary"),
            ]), color="light"), md=3),
            dbc.Col(dbc.Card(dbc.CardBody([
                html.H5("P90"), html.H4(f"{mc_result['p90']:,.0f} {unit}"),
            ]), color="light"), md=3),
            dbc.Col(dbc.Card(dbc.CardBody([
                html.H5("Mean"), html.H4(f"{mc_result['mean']:,.0f} {unit}"),
            ]), color="light"), md=3),
        ])

        hist_fig = VolumetricsEngine.build_histogram_figure(mc_result)
        return content, hist_fig, {"display": "block"}
