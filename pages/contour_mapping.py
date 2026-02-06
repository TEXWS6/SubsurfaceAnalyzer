"""Contour Mapping page — structure/isopach maps with configurable gridding."""

import dash
from dash import html, dcc, callback, Input, Output, State, no_update, ctx, dash_table
import dash_bootstrap_components as dbc

from database.repositories import (
    ProjectRepository, WellRepository, TopsRepository, MapConfigRepository,
    ProductionRepository,
)
from services.mapping import MappingService
from services.volumetrics import VolumetricsEngine

dash.register_page(__name__, path="/contour-mapping", name="Contour Maps")

project_repo = ProjectRepository()
well_repo = WellRepository()
tops_repo = TopsRepository()
map_repo = MapConfigRepository()
prod_repo = ProductionRepository()

layout = dbc.Container([
    dbc.Row([
        # Sidebar
        dbc.Col([
            html.H5("Contour Mapping", className="mt-3"),

            dbc.Label("Project"),
            dbc.Select(id="cm-project-select", placeholder="Select project..."),

            html.Hr(),

            dbc.Label("Map Type"),
            dbc.RadioItems(
                id="cm-map-type",
                options=[
                    {"label": "Structure Map", "value": "structure"},
                    {"label": "Isopach Map", "value": "isopach"},
                    {"label": "Bubble Map", "value": "bubble"},
                    {"label": "Posted Values", "value": "posted"},
                    {"label": "Pie Chart Map", "value": "pie"},
                    {"label": "Grid Property", "value": "grid"},
                ],
                value="structure",
                className="mb-2",
            ),

            dbc.Label("Top Formation"),
            dbc.Select(id="cm-formation-top", placeholder="Select formation..."),

            html.Div(id="cm-base-div", children=[
                dbc.Label("Base Formation", className="mt-2"),
                dbc.Select(id="cm-formation-base", placeholder="Select base..."),
            ], style={"display": "none"}),

            html.Hr(),

            dbc.Label("Interpolation Method"),
            dbc.Select(
                id="cm-interp-method",
                options=[
                    {"label": "Cubic", "value": "cubic"},
                    {"label": "Linear", "value": "linear"},
                    {"label": "Nearest", "value": "nearest"},
                    {"label": "Ordinary Kriging", "value": "kriging"},
                    {"label": "IDW", "value": "idw"},
                ],
                value="cubic",
            ),

            dbc.Label("Grid Resolution", className="mt-2"),
            dbc.Input(id="cm-resolution", type="number", value=100, min=20, max=500),

            # Kriging params (shown when kriging selected)
            html.Div(id="cm-kriging-div", children=[
                dbc.Label("Variogram Model", className="mt-2"),
                dbc.Select(
                    id="cm-kriging-model",
                    options=[
                        {"label": "Spherical", "value": "spherical"},
                        {"label": "Exponential", "value": "exponential"},
                        {"label": "Gaussian", "value": "gaussian"},
                    ],
                    value="spherical",
                ),
                dbc.Checkbox(id="cm-kriging-autofit", label="Auto-fit variogram",
                             value=True, className="mt-1"),
                dbc.Label("Sill", className="mt-1"),
                dbc.Input(id="cm-kriging-sill", type="number", step=0.1,
                          disabled=True),
                dbc.Label("Range", className="mt-1"),
                dbc.Input(id="cm-kriging-range", type="number", step=10,
                          disabled=True),
                dbc.Label("Nugget", className="mt-1"),
                dbc.Input(id="cm-kriging-nugget", type="number", step=0.1,
                          disabled=True),
            ], style={"display": "none"}),

            # IDW power (shown when IDW selected)
            html.Div(id="cm-idw-div", children=[
                dbc.Label("IDW Power", className="mt-2"),
                dcc.Slider(id="cm-idw-power", min=0.5, max=5, step=0.5,
                           value=2, marks={i: str(i) for i in range(1, 6)}),
            ], style={"display": "none"}),

            # Property selector for bubble/posted/grid maps
            html.Div(id="cm-property-div", children=[
                dbc.Label("Property", className="mt-2"),
                dbc.Select(
                    id="cm-property-select",
                    options=[
                        {"label": "KB Elevation", "value": "kb"},
                        {"label": "Total Depth", "value": "td"},
                        {"label": "Cum Oil", "value": "cum_oil"},
                        {"label": "Cum Gas", "value": "cum_gas"},
                    ],
                    value="kb",
                ),
            ], style={"display": "none"}),

            # Polygon area display
            html.Div(id="cm-polygon-div", children=[
                html.Hr(),
                dbc.Checkbox(id="cm-polygon-mode", label="Draw Polygon",
                             value=False, className="mt-1"),
                html.P(id="cm-polygon-area", children="",
                       className="text-muted small mt-1"),
            ]),

            dbc.Label("Color Scale", className="mt-2"),
            dbc.Select(
                id="cm-colorscale",
                options=[
                    {"label": "Viridis", "value": "Viridis"},
                    {"label": "Plasma", "value": "Plasma"},
                    {"label": "Earth", "value": "Earth"},
                    {"label": "Thermal", "value": "thermal"},
                    {"label": "RdYlGn", "value": "RdYlGn"},
                    {"label": "RdBu", "value": "RdBu"},
                ],
                value="Viridis",
            ),

            dbc.Button("Generate Map", id="cm-generate-btn", color="primary",
                        className="mt-3 w-100"),

            html.Hr(),

            # Save/load config
            dbc.Label("Config Name"),
            dbc.Input(id="cm-config-name", placeholder="My map config"),
            dbc.Button("Save Config", id="cm-save-config-btn", color="secondary",
                        size="sm", className="mt-1 w-100"),
            dbc.Select(id="cm-load-config", placeholder="Load saved config...",
                        className="mt-2"),

            html.Hr(),

            # Well coordinate editor
            html.H6("Well Coordinates"),
            html.P("Edit well X/Y coordinates:", className="text-muted small"),
            dash_table.DataTable(
                id="cm-well-coords-table",
                columns=[
                    {"name": "Well", "id": "name"},
                    {"name": "X", "id": "x_coord", "type": "numeric", "editable": True},
                    {"name": "Y", "id": "y_coord", "type": "numeric", "editable": True},
                    {"name": "KB", "id": "kb", "type": "numeric", "editable": True},
                ],
                data=[],
                editable=True,
                style_cell={"textAlign": "left", "padding": "4px", "fontSize": "11px"},
                style_header={"fontWeight": "bold", "fontSize": "11px"},
                page_size=10,
            ),
            dbc.Button("Save Coordinates", id="cm-save-coords-btn", color="info",
                        size="sm", className="mt-1 w-100"),

        ], md=3, className="border-end bg-light",
           style={"maxHeight": "calc(100vh - 56px)", "overflowY": "auto"}),

        # Main map area
        dbc.Col([
            dcc.Loading(
                dcc.Graph(id="cm-map-plot", style={"height": "calc(100vh - 70px)"}),
                type="circle",
            ),
            dbc.Alert(id="cm-alert", is_open=False, duration=4000, className="mt-2"),
        ], md=9),
    ]),
], fluid=True, className="px-0")


@callback(
    Output("cm-project-select", "options"),
    Output("cm-project-select", "value"),
    Input("cm-project-select", "id"),
    State("session-project-id", "data"),
)
def load_projects(_, session_pid):
    projects = project_repo.get_all()
    options = [{"label": p["name"], "value": str(p["id"])} for p in projects]
    value = str(session_pid) if session_pid else (options[0]["value"] if options else None)
    return options, value


@callback(
    Output("cm-formation-top", "options"),
    Output("cm-formation-base", "options"),
    Output("cm-well-coords-table", "data"),
    Output("cm-load-config", "options"),
    Input("cm-project-select", "value"),
)
def load_project_data(project_id):
    if not project_id:
        return [], [], [], []
    pid = int(project_id)

    formations = tops_repo.get_formations_in_project(pid)
    f_opts = [{"label": f, "value": f} for f in formations]

    wells = well_repo.get_by_project(pid)
    well_data = [{"id": w["id"], "name": w["name"],
                  "x_coord": w["x_coord"], "y_coord": w["y_coord"],
                  "kb": w["kb"]} for w in wells]

    configs = map_repo.get_by_project(pid)
    c_opts = [{"label": c["name"], "value": str(c["id"])} for c in configs]

    return f_opts, f_opts, well_data, c_opts


@callback(
    Output("cm-base-div", "style"),
    Output("cm-property-div", "style"),
    Input("cm-map-type", "value"),
)
def toggle_map_type_controls(map_type):
    base_style = {"display": "none"}
    prop_style = {"display": "none"}
    if map_type == "isopach":
        base_style = {"display": "block"}
    if map_type in ("bubble", "posted", "grid"):
        prop_style = {"display": "block"}
    return base_style, prop_style


@callback(
    Output("cm-kriging-div", "style"),
    Output("cm-idw-div", "style"),
    Input("cm-interp-method", "value"),
)
def toggle_interp_controls(method):
    kriging_style = {"display": "none"}
    idw_style = {"display": "none"}
    if method == "kriging":
        kriging_style = {"display": "block"}
    elif method == "idw":
        idw_style = {"display": "block"}
    return kriging_style, idw_style


@callback(
    Output("cm-kriging-sill", "disabled"),
    Output("cm-kriging-range", "disabled"),
    Output("cm-kriging-nugget", "disabled"),
    Input("cm-kriging-autofit", "value"),
)
def toggle_kriging_manual(autofit):
    return autofit, autofit, autofit


@callback(
    Output("cm-map-plot", "figure"),
    Output("cm-alert", "children"),
    Output("cm-alert", "color"),
    Output("cm-alert", "is_open"),
    Input("cm-generate-btn", "n_clicks"),
    State("cm-project-select", "value"),
    State("cm-map-type", "value"),
    State("cm-formation-top", "value"),
    State("cm-formation-base", "value"),
    State("cm-interp-method", "value"),
    State("cm-resolution", "value"),
    State("cm-colorscale", "value"),
    State("cm-kriging-model", "value"),
    State("cm-kriging-autofit", "value"),
    State("cm-kriging-sill", "value"),
    State("cm-kriging-range", "value"),
    State("cm-kriging-nugget", "value"),
    State("cm-idw-power", "value"),
    State("cm-property-select", "value"),
    prevent_initial_call=True,
)
def generate_map(n_clicks, project_id, map_type, formation_top, formation_base,
                 method, resolution, colorscale,
                 kriging_model, kriging_autofit, kriging_sill, kriging_range,
                 kriging_nugget, idw_power, property_key):
    import plotly.graph_objects as go
    import numpy as np

    if not project_id:
        return go.Figure(), "Select a project", "warning", True

    pid = int(project_id)
    resolution = int(resolution) if resolution else 100

    def _get_wells_with_coords():
        """Get project wells filtered to those with coordinates."""
        wells = well_repo.get_by_project(pid)
        return [w for w in wells if w.get("x_coord") is not None
                and w.get("y_coord") is not None]

    def _interpolate(x, y, z, res):
        """Dispatch to the selected interpolation method."""
        if method == "kriging":
            sill = float(kriging_sill) if not kriging_autofit and kriging_sill else None
            rng = float(kriging_range) if not kriging_autofit and kriging_range else None
            nug = float(kriging_nugget) if not kriging_autofit and kriging_nugget else None
            return MappingService.interpolate_grid_kriging(
                x, y, z, kriging_model or "spherical", sill, rng, nug, res)
        elif method == "idw":
            return MappingService.interpolate_grid_idw(
                x, y, z, float(idw_power or 2), res)
        else:
            return MappingService.interpolate_grid(x, y, z, method, res)

    # --- Structure map ---
    if map_type == "structure":
        if not formation_top:
            return go.Figure(), "Select a formation", "warning", True

        wells_data = tops_repo.get_by_formation(pid, formation_top)
        valid = [w for w in wells_data if w.get("x_coord") is not None
                 and w.get("y_coord") is not None]

        if len(valid) < 3:
            return (go.Figure().update_layout(
                        title="Need at least 3 wells with coordinates and picks"),
                    f"Only {len(valid)} valid wells found. Need at least 3.",
                    "warning", True)

        if method in ("kriging", "idw"):
            x = np.array([w["x_coord"] for w in valid])
            y = np.array([w["y_coord"] for w in valid])
            z = np.array([(w.get("kb", 0) or 0) - w["md_top"] for w in valid])
            names = [w.get("well_name", "") for w in valid]
            xi, yi, zi = _interpolate(x, y, z, resolution)
            fig = MappingService.build_contour_figure(
                xi, yi, zi, x, y, z, names,
                title=f"Structure Map — {formation_top}",
                colorscale=colorscale, z_label="TVDSS (ft)")
        else:
            fig = MappingService.build_structure_map(
                valid, formation_top, method, resolution, colorscale)
        return fig, "", "info", False

    # --- Isopach map ---
    elif map_type == "isopach":
        if not formation_top or not formation_base:
            return go.Figure(), "Select top and base formations", "warning", True

        top_data = tops_repo.get_by_formation(pid, formation_top)
        base_data = tops_repo.get_by_formation(pid, formation_base)
        base_by_well = {b["well_id"]: b for b in base_data}
        valid = []
        for t in top_data:
            if (t["well_id"] in base_by_well
                    and t.get("x_coord") is not None
                    and t.get("y_coord") is not None):
                b = base_by_well[t["well_id"]]
                valid.append({
                    "x_coord": t["x_coord"], "y_coord": t["y_coord"],
                    "md_top": t["md_top"], "md_base": b["md_top"],
                    "well_name": t.get("well_name", ""),
                })

        if len(valid) < 3:
            return (go.Figure().update_layout(
                        title="Need at least 3 wells with both picks"),
                    f"Only {len(valid)} valid wells. Need at least 3.",
                    "warning", True)

        if method in ("kriging", "idw"):
            x = np.array([w["x_coord"] for w in valid])
            y = np.array([w["y_coord"] for w in valid])
            z = np.array([w["md_base"] - w["md_top"] for w in valid])
            names = [w.get("well_name", "") for w in valid]
            xi, yi, zi = _interpolate(x, y, z, resolution)
            fig = MappingService.build_contour_figure(
                xi, yi, zi, x, y, z, names,
                title=f"Isopach — {formation_top} to {formation_base}",
                colorscale=colorscale, z_label="Thickness (ft)")
        else:
            fig = MappingService.build_isopach_map(
                valid, formation_top, formation_base, method, resolution, colorscale)
        return fig, "", "info", False

    # --- Bubble map ---
    elif map_type == "bubble":
        wells = _get_wells_with_coords()
        if not wells:
            return go.Figure(), "No wells with coordinates", "warning", True

        prop = property_key or "kb"
        wells_data = []
        if prop in ("cum_oil", "cum_gas"):
            for w in wells:
                cum = prod_repo.get_cumulative(w["id"])
                wells_data.append({
                    "x_coord": w["x_coord"], "y_coord": w["y_coord"],
                    "well_name": w["name"], prop: cum.get(prop, 0),
                })
        else:
            wells_data = [{
                "x_coord": w["x_coord"], "y_coord": w["y_coord"],
                "well_name": w["name"], prop: w.get(prop, 0),
            } for w in wells]

        fig = MappingService.build_bubble_map(
            wells_data, prop, f"Bubble Map — {prop}", colorscale)
        return fig, "", "info", False

    # --- Posted values ---
    elif map_type == "posted":
        wells = _get_wells_with_coords()
        if not wells:
            return go.Figure(), "No wells with coordinates", "warning", True

        prop = property_key or "kb"
        wells_data = [{
            "x_coord": w["x_coord"], "y_coord": w["y_coord"],
            "well_name": w["name"], prop: w.get(prop, 0),
        } for w in wells]

        fig = MappingService.build_posted_values_map(
            wells_data, prop, f"Posted Values — {prop}")
        return fig, "", "info", False

    # --- Pie chart map ---
    elif map_type == "pie":
        wells = _get_wells_with_coords()
        if not wells:
            return go.Figure(), "No wells with coordinates", "warning", True

        wells_data = []
        for w in wells:
            cum = prod_repo.get_cumulative(w["id"])
            wells_data.append({
                "x_coord": w["x_coord"], "y_coord": w["y_coord"],
                "well_name": w["name"],
                "cum_oil": cum.get("cum_oil", 0),
                "cum_gas": cum.get("cum_gas", 0),
                "cum_water": cum.get("cum_water", 0),
            })

        fig = MappingService.build_pie_chart_map(wells_data, "Pie Chart Map")
        return fig, "", "info", False

    # --- Grid property map ---
    elif map_type == "grid":
        wells = _get_wells_with_coords()
        prop = property_key or "kb"
        valid = [w for w in wells if w.get(prop) is not None]

        if len(valid) < 3:
            return (go.Figure(), f"Need 3+ wells with {prop}", "warning", True)

        x = np.array([w["x_coord"] for w in valid])
        y = np.array([w["y_coord"] for w in valid])
        z = np.array([w.get(prop, 0) for w in valid])
        names = [w.get("name", "") for w in valid]

        xi, yi, zi = _interpolate(x, y, z, resolution)
        fig = MappingService.build_grid_property_map(
            xi, yi, zi, x, y, names, f"Grid — {prop}", colorscale)
        return fig, "", "info", False

    return go.Figure(), "Unknown map type", "danger", True


@callback(
    Output("cm-save-config-btn", "n_clicks"),
    Input("cm-save-config-btn", "n_clicks"),
    State("cm-project-select", "value"),
    State("cm-config-name", "value"),
    State("cm-map-type", "value"),
    State("cm-formation-top", "value"),
    State("cm-formation-base", "value"),
    State("cm-interp-method", "value"),
    State("cm-resolution", "value"),
    State("cm-colorscale", "value"),
    prevent_initial_call=True,
)
def save_config(n_clicks, project_id, name, map_type, f_top, f_base,
                method, resolution, colorscale):
    if not project_id or not name:
        return no_update
    map_repo.create(
        int(project_id), name, map_type, f_top, f_base,
        method, int(resolution or 100), colorscale or "Viridis",
    )
    return no_update


@callback(
    Output("cm-map-type", "value"),
    Output("cm-formation-top", "value"),
    Output("cm-formation-base", "value"),
    Output("cm-interp-method", "value"),
    Output("cm-resolution", "value"),
    Output("cm-colorscale", "value"),
    Input("cm-load-config", "value"),
    prevent_initial_call=True,
)
def load_config(config_id):
    if not config_id:
        return no_update, no_update, no_update, no_update, no_update, no_update
    c = map_repo.get_by_id(int(config_id))
    if not c:
        return no_update, no_update, no_update, no_update, no_update, no_update
    return (c["map_type"], c["formation_top"], c["formation_base"],
            c["interpolation_method"], c["grid_resolution"], c["colorscale"])


@callback(
    Output("cm-save-coords-btn", "n_clicks"),
    Input("cm-save-coords-btn", "n_clicks"),
    State("cm-well-coords-table", "data"),
    prevent_initial_call=True,
)
def save_coordinates(n_clicks, data):
    if data:
        for row in data:
            well_repo.update(
                row["id"],
                x_coord=float(row["x_coord"]) if row.get("x_coord") is not None else None,
                y_coord=float(row["y_coord"]) if row.get("y_coord") is not None else None,
                kb=float(row["kb"]) if row.get("kb") is not None else None,
            )
    return no_update


@callback(
    Output("cm-map-plot", "config"),
    Input("cm-polygon-mode", "value"),
)
def toggle_polygon_draw(enabled):
    if enabled:
        return {"modeBarButtonsToAdd": ["drawclosedpath", "eraseshape"],
                "editable": True}
    return {}


@callback(
    Output("cm-polygon-area", "children"),
    Output("session-polygon-area", "data"),
    Output("session-polygon-vertices", "data"),
    Input("cm-map-plot", "relayoutData"),
    State("cm-polygon-mode", "value"),
    prevent_initial_call=True,
)
def compute_polygon_area(relayout_data, polygon_mode):
    if not polygon_mode or not relayout_data:
        return "", None, None

    # Extract SVG path from shapes
    shapes = relayout_data.get("shapes")
    if not shapes:
        # Check for individual shape updates
        for key in relayout_data:
            if "shapes" in key and "path" in key:
                break
        else:
            return no_update, no_update, no_update

    if shapes:
        last_shape = shapes[-1]
        path = last_shape.get("path", "")
        if path:
            import re
            # Parse SVG path — extract coordinates from M, L commands
            coords = re.findall(r'[-+]?\d*\.?\d+', path)
            if len(coords) >= 6:
                vertices = [(float(coords[i]), float(coords[i+1]))
                            for i in range(0, len(coords) - 1, 2)]
                area_acres = VolumetricsEngine.polygon_area_acres(vertices)
                return (f"Polygon Area: {area_acres:.2f} acres",
                        area_acres, vertices)

    return no_update, no_update, no_update
