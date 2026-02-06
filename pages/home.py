"""Home page — project management, LAS upload, well list table."""

import base64
import dash
from dash import html, dcc, callback, Input, Output, State, dash_table, no_update
import dash_bootstrap_components as dbc

from database.repositories import (
    ProjectRepository, WellRepository, CurveRepository,
    ProductionRepository, CompletionsRepository,
)
from services.las_parser import LASParser
from services.ihs_parser import IHSParser

dash.register_page(__name__, path="/", name="Home")

project_repo = ProjectRepository()
well_repo = WellRepository()
curve_repo = CurveRepository()
prod_repo = ProductionRepository()
comp_repo = CompletionsRepository()
las_parser = LASParser()
ihs_parser = IHSParser()

layout = dbc.Container([
    dbc.Row([
        dbc.Col([
            html.H3("Projects", className="mt-3"),
            dbc.InputGroup([
                dbc.Input(id="project-name-input", placeholder="New project name..."),
                dbc.Input(id="project-desc-input", placeholder="Description (optional)"),
                dbc.Button("Create", id="create-project-btn", color="primary"),
            ], className="mb-3"),
            dbc.Select(
                id="project-selector",
                placeholder="Select a project...",
                className="mb-3",
            ),
            dbc.Button("Delete Project", id="delete-project-btn", color="danger",
                        size="sm", className="mb-3"),
        ], md=12),
    ]),

    html.Hr(),

    dbc.Row([
        dbc.Col([
            dbc.Tabs([
                dbc.Tab([
                    html.H4("Import LAS File", className="mt-3"),
                    dcc.Upload(
                        id="las-upload",
                        children=dbc.Card(
                            dbc.CardBody([
                                html.I(className="bi bi-cloud-upload fs-1"),
                                html.P("Drag & drop or click to upload LAS file"),
                            ], className="text-center"),
                            className="border-dashed",
                        ),
                        multiple=False,
                    ),
                    dbc.Alert(id="upload-alert", is_open=False, duration=5000,
                              className="mt-2"),
                ], label="LAS Import"),

                dbc.Tab([
                    html.H4("Import IHS .297/.298", className="mt-3"),
                    dbc.Row([
                        dbc.Col([
                            dbc.Label("Well Headers (.297)"),
                            dcc.Upload(
                                id="ihs-297-upload",
                                children=dbc.Card(
                                    dbc.CardBody([
                                        html.I(className="bi bi-file-earmark-text fs-2"),
                                        html.P("Upload .297 file", className="small"),
                                    ], className="text-center py-2"),
                                    className="border-dashed",
                                ),
                                multiple=False,
                            ),
                        ], md=6),
                        dbc.Col([
                            dbc.Label("Production (.298)"),
                            dcc.Upload(
                                id="ihs-298-upload",
                                children=dbc.Card(
                                    dbc.CardBody([
                                        html.I(className="bi bi-file-earmark-text fs-2"),
                                        html.P("Upload .298 file", className="small"),
                                    ], className="text-center py-2"),
                                    className="border-dashed",
                                ),
                                multiple=False,
                            ),
                        ], md=6),
                    ]),
                    dbc.Alert(id="ihs-alert", is_open=False, duration=5000,
                              className="mt-2"),
                    html.Div(id="ihs-summary", className="mt-2"),
                ], label="IHS .297/.298 Import"),
            ]),
        ], md=6),
        dbc.Col([
            html.H4("Project Wells"),
            dash_table.DataTable(
                id="wells-table",
                columns=[
                    {"name": "ID", "id": "id"},
                    {"name": "Well Name", "id": "name"},
                    {"name": "UWI", "id": "uwi"},
                    {"name": "X", "id": "x_coord"},
                    {"name": "Y", "id": "y_coord"},
                    {"name": "KB", "id": "kb"},
                    {"name": "TD", "id": "td"},
                ],
                data=[],
                row_selectable="single",
                page_size=15,
                style_table={"overflowX": "auto"},
                style_cell={"textAlign": "left", "padding": "8px", "fontSize": "13px"},
                style_header={"fontWeight": "bold", "backgroundColor": "#f8f9fa"},
            ),
            dbc.Button("Delete Well", id="delete-well-btn", color="danger",
                        size="sm", className="mt-2"),
        ], md=6),
    ]),

    # Hidden stores
    dcc.Store(id="session-project-id", storage_type="session"),
    dcc.Store(id="session-well-id", storage_type="session"),
    dcc.Store(id="upload-trigger", data=0),
], fluid=True)


@callback(
    Output("project-selector", "options"),
    Output("project-selector", "value"),
    Output("project-name-input", "value"),
    Output("project-desc-input", "value"),
    Input("create-project-btn", "n_clicks"),
    Input("delete-project-btn", "n_clicks"),
    State("project-name-input", "value"),
    State("project-desc-input", "value"),
    State("project-selector", "value"),
    prevent_initial_call=False,
)
def manage_projects(create_clicks, delete_clicks, name, desc, selected):
    ctx = dash.callback_context
    trigger = ctx.triggered[0]["prop_id"] if ctx.triggered else ""

    if "create-project-btn" in trigger and name and name.strip():
        try:
            new_id = project_repo.create(name.strip(), desc or "")
            selected = str(new_id)
        except Exception:
            pass

    if "delete-project-btn" in trigger and selected:
        try:
            project_repo.delete(int(selected))
            selected = None
        except Exception:
            pass

    projects = project_repo.get_all()
    options = [{"label": p["name"], "value": str(p["id"])} for p in projects]
    if selected is None and options:
        selected = options[0]["value"]

    return options, selected, "", ""


@callback(
    Output("session-project-id", "data"),
    Input("project-selector", "value"),
)
def store_project_id(project_id):
    return int(project_id) if project_id else None


@callback(
    Output("wells-table", "data"),
    Output("upload-alert", "children"),
    Output("upload-alert", "color"),
    Output("upload-alert", "is_open"),
    Output("upload-trigger", "data"),
    Input("las-upload", "contents"),
    Input("project-selector", "value"),
    Input("delete-well-btn", "n_clicks"),
    Input("upload-trigger", "data"),
    State("las-upload", "filename"),
    State("wells-table", "selected_rows"),
    State("wells-table", "data"),
    prevent_initial_call=False,
)
def handle_wells(contents, project_id, delete_clicks, trigger,
                 filename, selected_rows, table_data):
    ctx = dash.callback_context
    triggered = ctx.triggered[0]["prop_id"] if ctx.triggered else ""

    alert_msg = ""
    alert_color = "info"
    alert_open = False

    if not project_id:
        return [], "", "info", False, trigger or 0

    pid = int(project_id)

    # Handle LAS upload
    if "las-upload" in triggered and contents:
        try:
            content_type, content_string = contents.split(",")
            decoded = base64.b64decode(content_string)
            result = las_parser.parse_from_bytes(decoded, filename)
            meta = result["metadata"]

            well_id = well_repo.create(
                project_id=pid,
                name=meta["name"],
                uwi=meta.get("uwi", ""),
                x_coord=meta.get("x_coord"),
                y_coord=meta.get("y_coord"),
                kb=meta.get("kb"),
                td=meta.get("td"),
                las_path=meta.get("las_path", filename),
            )

            for curve in result["curves"]:
                curve_repo.save_curve(
                    well_id=well_id,
                    mnemonic=curve["mnemonic"],
                    original_mnemonic=curve["original_mnemonic"],
                    unit=curve["unit"],
                    depth_data=curve["depth_data"],
                    curve_data=curve["data"],
                )

            alert_msg = f"Imported '{meta['name']}' with {len(result['curves'])} curves"
            alert_color = "success"
            alert_open = True
        except Exception as e:
            alert_msg = f"Error importing LAS: {str(e)}"
            alert_color = "danger"
            alert_open = True

    # Handle well deletion
    if "delete-well-btn" in triggered and selected_rows and table_data:
        try:
            row = table_data[selected_rows[0]]
            well_repo.delete(row["id"])
            alert_msg = f"Deleted well '{row['name']}'"
            alert_color = "warning"
            alert_open = True
        except Exception as e:
            alert_msg = f"Error deleting: {str(e)}"
            alert_color = "danger"
            alert_open = True

    wells = well_repo.get_by_project(pid)
    return wells, alert_msg, alert_color, alert_open, (trigger or 0) + 1


@callback(
    Output("session-well-id", "data"),
    Input("wells-table", "selected_rows"),
    State("wells-table", "data"),
)
def store_well_id(selected_rows, data):
    if selected_rows and data:
        return data[selected_rows[0]]["id"]
    return None


@callback(
    Output("ihs-alert", "children"),
    Output("ihs-alert", "color"),
    Output("ihs-alert", "is_open"),
    Output("ihs-summary", "children"),
    Output("upload-trigger", "data", allow_duplicate=True),
    Input("ihs-297-upload", "contents"),
    Input("ihs-298-upload", "contents"),
    State("ihs-297-upload", "filename"),
    State("ihs-298-upload", "filename"),
    State("project-selector", "value"),
    State("upload-trigger", "data"),
    prevent_initial_call=True,
)
def handle_ihs_import(content_297, content_298, filename_297, filename_298,
                      project_id, trigger):
    import base64
    ctx_obj = dash.callback_context
    triggered = ctx_obj.triggered[0]["prop_id"] if ctx_obj.triggered else ""

    if not project_id:
        return "Select a project first", "warning", True, "", trigger or 0

    pid = int(project_id)
    summary_parts = []

    # Handle .297 well header upload
    if "ihs-297-upload" in triggered and content_297:
        try:
            content_type, content_string = content_297.split(",")
            decoded = base64.b64decode(content_string).decode("utf-8", errors="replace")
            wells_data = ihs_parser.parse_297(decoded)
            result = ihs_parser.import_297_to_project(wells_data, pid, well_repo)

            # Also import completions if present
            try:
                completions = ihs_parser.parse_297_completions(decoded)
                comp_count = 0
                for c in completions:
                    well = well_repo.get_by_uwi(pid, c["uwi"])
                    if well:
                        comp_repo.create(
                            well_id=well["id"],
                            perf_top=c.get("perf_top"),
                            perf_base=c.get("perf_base"),
                            completion_date=c.get("completion_date"),
                            treatment_type=c.get("treatment_type", ""),
                        )
                        comp_count += 1
                if comp_count:
                    summary_parts.append(f"{comp_count} completions imported")
            except Exception:
                pass

            msg = (f".297: {result['created']} wells created, "
                   f"{result['skipped']} skipped (total: {result['total']})")
            summary_parts.insert(0, msg)
            return msg, "success", True, html.P("; ".join(summary_parts)), (trigger or 0) + 1
        except Exception as e:
            return f"Error parsing .297: {str(e)}", "danger", True, "", trigger or 0

    # Handle .298 production upload
    if "ihs-298-upload" in triggered and content_298:
        try:
            content_type, content_string = content_298.split(",")
            decoded = base64.b64decode(content_string).decode("utf-8", errors="replace")
            records = ihs_parser.parse_298(decoded)

            matched = 0
            unmatched = 0
            bulk_records = []
            for rec in records:
                well = well_repo.get_by_uwi(pid, rec["uwi"])
                if well:
                    bulk_records.append((
                        well["id"], rec["date"], rec["oil_vol"],
                        rec["gas_vol"], rec["water_vol"], rec["days_produced"],
                    ))
                    matched += 1
                else:
                    unmatched += 1

            if bulk_records:
                prod_repo.bulk_create(bulk_records)

            msg = (f".298: {matched} records matched, "
                   f"{unmatched} unmatched UWIs (total: {len(records)})")
            return msg, "success", True, html.P(msg), (trigger or 0) + 1
        except Exception as e:
            return f"Error parsing .298: {str(e)}", "danger", True, "", trigger or 0

    return no_update, no_update, no_update, no_update, trigger or 0
