"""Production Data page — time-series charts, decline curve analysis,
multi-well comparison, and editable production table."""

import dash
from dash import html, dcc, callback, Input, Output, State, no_update, ctx, dash_table
import dash_bootstrap_components as dbc
import plotly.graph_objects as go
import numpy as np

from database.repositories import ProjectRepository, WellRepository, ProductionRepository
from services.decline_curve import DeclineCurveEngine

dash.register_page(__name__, path="/production-data", name="Production Data")

project_repo = ProjectRepository()
well_repo = WellRepository()
prod_repo = ProductionRepository()

layout = dbc.Container([
    dbc.Row([
        # Sidebar
        dbc.Col([
            html.H5("Production Data", className="mt-3"),

            dbc.Label("Project"),
            dbc.Select(id="pd-project-select", placeholder="Select project..."),

            dbc.Label("Well", className="mt-2"),
            dbc.Select(id="pd-well-select", placeholder="Select well..."),

            html.Hr(),

            dbc.Card(dbc.CardBody([
                html.H6("Chart Options", className="card-title"),
                dbc.Label("Fluids"),
                dbc.Checklist(
                    id="pd-fluid-checklist",
                    options=[
                        {"label": "Oil", "value": "oil"},
                        {"label": "Gas", "value": "gas"},
                        {"label": "Water", "value": "water"},
                    ],
                    value=["oil", "gas", "water"],
                    inline=True,
                ),
                dbc.Label("Y-axis", className="mt-1"),
                dbc.RadioItems(
                    id="pd-y-scale",
                    options=[
                        {"label": "Linear", "value": "linear"},
                        {"label": "Log", "value": "log"},
                    ],
                    value="linear",
                    inline=True,
                ),
            ]), className="mb-2"),

            dbc.Card(dbc.CardBody([
                html.H6("Decline Curve Analysis", className="card-title"),
                dbc.Label("Fit Model"),
                dbc.Select(
                    id="pd-dca-model",
                    options=[
                        {"label": "Best Fit", "value": "best"},
                        {"label": "Exponential", "value": "exponential"},
                        {"label": "Hyperbolic", "value": "hyperbolic"},
                    ],
                    value="best",
                ),
                dbc.Label("Fluid to Fit", className="mt-1"),
                dbc.Select(
                    id="pd-dca-fluid",
                    options=[
                        {"label": "Oil", "value": "oil_vol"},
                        {"label": "Gas", "value": "gas_vol"},
                    ],
                    value="oil_vol",
                ),
                dbc.Label("Economic Limit", className="mt-1"),
                dbc.Input(id="pd-econ-limit", type="number", value=100, min=0),
                dbc.Label("Forecast Months", className="mt-1"),
                dbc.Input(id="pd-forecast-months", type="number", value=360,
                          min=12, max=600),
                dbc.Button("Run DCA", id="pd-run-dca-btn", color="info",
                           size="sm", className="mt-2 w-100"),
            ]), className="mb-2"),

            dbc.Card(dbc.CardBody([
                html.H6("Multi-Well Comparison", className="card-title"),
                dbc.Checklist(id="pd-multi-well-checklist", options=[], value=[],
                              className="small",
                              style={"maxHeight": "150px", "overflowY": "auto"}),
                dbc.Button("Compare Wells", id="pd-compare-btn", color="secondary",
                           size="sm", className="mt-1 w-100"),
            ]), className="mb-2"),

            dbc.Card(dbc.CardBody([
                html.H6("Add Record", className="card-title"),
                dbc.Label("Date (YYYY-MM)", className="small"),
                dbc.Input(id="pd-new-date", placeholder="2020-01"),
                dbc.Row([
                    dbc.Col([
                        dbc.Label("Oil", className="small"),
                        dbc.Input(id="pd-new-oil", type="number", value=0),
                    ], width=6),
                    dbc.Col([
                        dbc.Label("Gas", className="small"),
                        dbc.Input(id="pd-new-gas", type="number", value=0),
                    ], width=6),
                ], className="mt-1"),
                dbc.Row([
                    dbc.Col([
                        dbc.Label("Water", className="small"),
                        dbc.Input(id="pd-new-water", type="number", value=0),
                    ], width=6),
                    dbc.Col([
                        dbc.Label("Days", className="small"),
                        dbc.Input(id="pd-new-days", type="number", value=30),
                    ], width=6),
                ], className="mt-1"),
                dbc.Button("Add Record", id="pd-add-row-btn", color="primary",
                           size="sm", className="mt-2 w-100"),
            ])),

        ], md=3, className="border-end bg-light",
           style={"maxHeight": "calc(100vh - 56px)", "overflowY": "auto"}),

        # Main area
        dbc.Col([
            # Summary cards
            dbc.Row(id="pd-summary-row", className="mt-2 mb-2"),

            # Chart tabs
            dbc.Tabs([
                dbc.Tab([
                    dcc.Loading(
                        dcc.Graph(id="pd-rate-chart",
                                  style={"height": "400px"}),
                        type="circle",
                    ),
                ], label="Rate vs Time"),
                dbc.Tab([
                    dcc.Loading(
                        dcc.Graph(id="pd-cum-chart",
                                  style={"height": "400px"}),
                        type="circle",
                    ),
                ], label="Cumulative"),
                dbc.Tab([
                    dcc.Loading(
                        dcc.Graph(id="pd-dca-chart",
                                  style={"height": "400px"}),
                        type="circle",
                    ),
                    html.Div(id="pd-dca-results", className="mt-2"),
                ], label="Decline Curve"),
                dbc.Tab([
                    dcc.Loading(
                        dcc.Graph(id="pd-compare-chart",
                                  style={"height": "400px"}),
                        type="circle",
                    ),
                ], label="Multi-Well"),
            ], className="mt-2"),

            # Editable DataTable
            html.H6("Production Records", className="mt-3"),
            dash_table.DataTable(
                id="pd-data-table",
                columns=[
                    {"name": "ID", "id": "id", "editable": False},
                    {"name": "Date", "id": "date", "editable": True},
                    {"name": "Oil Vol", "id": "oil_vol", "type": "numeric",
                     "editable": True},
                    {"name": "Gas Vol", "id": "gas_vol", "type": "numeric",
                     "editable": True},
                    {"name": "Water Vol", "id": "water_vol", "type": "numeric",
                     "editable": True},
                    {"name": "Days", "id": "days_produced", "type": "numeric",
                     "editable": True},
                ],
                data=[],
                editable=True,
                row_deletable=True,
                page_size=12,
                style_table={"overflowX": "auto"},
                style_cell={"textAlign": "left", "padding": "6px",
                             "fontSize": "12px"},
                style_header={"fontWeight": "bold", "fontSize": "12px",
                               "backgroundColor": "#f8f9fa"},
            ),
            dbc.Alert(id="pd-alert", is_open=False, duration=4000,
                      className="mt-2"),

            dcc.Store(id="pd-refresh-trigger", data=0),
        ], md=9),
    ]),
], fluid=True, className="px-0")


# --- Callbacks ---

@callback(
    Output("pd-project-select", "options"),
    Output("pd-project-select", "value"),
    Input("pd-project-select", "id"),
    State("session-project-id", "data"),
)
def load_projects(_, session_pid):
    projects = project_repo.get_all()
    options = [{"label": p["name"], "value": str(p["id"])} for p in projects]
    value = str(session_pid) if session_pid else (
        options[0]["value"] if options else None)
    return options, value


@callback(
    Output("pd-well-select", "options"),
    Output("pd-well-select", "value"),
    Output("pd-multi-well-checklist", "options"),
    Input("pd-project-select", "value"),
    Input("session-well-id", "data"),
)
def load_wells(project_id, session_wid):
    if not project_id:
        return [], None, []
    wells = well_repo.get_by_project(int(project_id))
    options = [{"label": w["name"], "value": str(w["id"])} for w in wells]
    value = str(session_wid) if session_wid else (
        options[0]["value"] if options else None)
    checklist_opts = [{"label": w["name"], "value": str(w["id"])} for w in wells]
    return options, value, checklist_opts


@callback(
    Output("pd-data-table", "data"),
    Output("pd-rate-chart", "figure"),
    Output("pd-cum-chart", "figure"),
    Output("pd-summary-row", "children"),
    Output("pd-alert", "children"),
    Output("pd-alert", "color"),
    Output("pd-alert", "is_open"),
    Output("pd-refresh-trigger", "data"),
    Input("pd-well-select", "value"),
    Input("pd-add-row-btn", "n_clicks"),
    Input("pd-data-table", "data_timestamp"),
    Input("pd-fluid-checklist", "value"),
    Input("pd-y-scale", "value"),
    State("pd-new-date", "value"),
    State("pd-new-oil", "value"),
    State("pd-new-gas", "value"),
    State("pd-new-water", "value"),
    State("pd-new-days", "value"),
    State("pd-data-table", "data"),
    State("pd-data-table", "data_previous"),
    State("pd-refresh-trigger", "data"),
    prevent_initial_call=True,
)
def manage_data_and_charts(well_id, add_clicks, data_ts,
                           fluids, y_scale,
                           new_date, new_oil, new_gas, new_water, new_days,
                           table_data, prev_data, trigger):
    alert_msg, alert_color, alert_open = "", "info", False
    trigger = trigger or 0

    if not well_id:
        empty = go.Figure().update_layout(title="Select a well")
        return [], empty, empty, [], "", "info", False, trigger

    wid = int(well_id)
    triggered = ctx.triggered_id

    # Handle add record
    if triggered == "pd-add-row-btn" and new_date:
        prod_repo.create(
            wid, new_date,
            float(new_oil or 0), float(new_gas or 0),
            float(new_water or 0), float(new_days or 30),
        )
        alert_msg = f"Added record for {new_date}"
        alert_color = "success"
        alert_open = True

    # Handle row deletion
    if triggered == "pd-data-table" and prev_data is not None and table_data is not None:
        if len(prev_data) > len(table_data):
            current_ids = {r["id"] for r in table_data}
            for r in prev_data:
                if r["id"] not in current_ids:
                    prod_repo.delete(r["id"])
            alert_msg = "Record deleted"
            alert_color = "warning"
            alert_open = True
        elif len(prev_data) == len(table_data):
            # Inline edit — update changed rows
            for old_row, new_row in zip(prev_data, table_data):
                if old_row != new_row:
                    prod_repo.update(
                        new_row["id"],
                        date=new_row.get("date", old_row["date"]),
                        oil_vol=float(new_row.get("oil_vol", 0) or 0),
                        gas_vol=float(new_row.get("gas_vol", 0) or 0),
                        water_vol=float(new_row.get("water_vol", 0) or 0),
                        days_produced=float(new_row.get("days_produced", 0) or 0),
                    )

    # Fetch fresh data
    records = prod_repo.get_by_well(wid)
    table = [{"id": r["id"], "date": r["date"], "oil_vol": r["oil_vol"],
              "gas_vol": r["gas_vol"], "water_vol": r["water_vol"],
              "days_produced": r["days_produced"]} for r in records]

    # Build charts
    fluids = fluids or ["oil", "gas", "water"]
    rate_fig = _build_rate_chart(records, fluids, y_scale or "linear")
    cum_fig = _build_cumulative_chart(records, fluids, y_scale or "linear")

    # Summary cards
    cum = prod_repo.get_cumulative(wid)
    avg_daily = (cum["cum_oil"] / cum["cum_days"]
                 if cum["cum_days"] > 0 else 0)
    summary = _build_summary_cards(cum, avg_daily)

    return (table, rate_fig, cum_fig, summary,
            alert_msg, alert_color, alert_open, trigger + 1)


@callback(
    Output("pd-dca-chart", "figure"),
    Output("pd-dca-results", "children"),
    Input("pd-run-dca-btn", "n_clicks"),
    State("pd-well-select", "value"),
    State("pd-dca-model", "value"),
    State("pd-dca-fluid", "value"),
    State("pd-econ-limit", "value"),
    State("pd-forecast-months", "value"),
    prevent_initial_call=True,
)
def run_dca(n_clicks, well_id, model, fluid_col, econ_limit, forecast_months):
    if not well_id:
        return go.Figure().update_layout(title="Select a well"), ""

    wid = int(well_id)
    econ_limit = float(econ_limit or 100)
    forecast_months = int(forecast_months or 360)

    records = prod_repo.get_by_well(wid)
    if len(records) < 3:
        return (go.Figure().update_layout(title="Need at least 3 production records"),
                dbc.Alert("Insufficient data for DCA", color="warning"))

    # Convert to numpy arrays
    rates = np.array([r.get(fluid_col, 0) or 0 for r in records], dtype=float)
    t = np.arange(len(rates), dtype=float)
    dates = [r["date"] for r in records]

    # Fit model
    if model == "exponential":
        fit = DeclineCurveEngine.fit_exponential(t, rates)
    elif model == "hyperbolic":
        fit = DeclineCurveEngine.fit_hyperbolic(t, rates)
    else:
        fit = DeclineCurveEngine.fit_best(t, rates)

    if fit.qi <= 0:
        return (go.Figure().update_layout(title="Could not fit decline curve"),
                dbc.Alert("Curve fitting failed — try different model or check data",
                          color="danger"))

    # Generate forecast
    t_forecast, r_forecast, c_forecast = DeclineCurveEngine.generate_forecast(
        fit, forecast_months, econ_limit)

    # Build chart
    fig = go.Figure()

    # Actual data
    fig.add_trace(go.Scatter(
        x=dates, y=rates,
        mode="markers",
        marker=dict(size=6, color="black"),
        name="Actual",
    ))

    # Fitted curve over historical range
    fitted_rates = (DeclineCurveEngine.hyperbolic_rate(t, fit.qi, fit.di, fit.b)
                    if fit.model == "hyperbolic" and fit.b > 0
                    else DeclineCurveEngine.exponential_rate(t, fit.qi, fit.di))
    fig.add_trace(go.Scatter(
        x=dates, y=fitted_rates,
        mode="lines",
        line=dict(color="red", width=2),
        name=f"Fit ({fit.model})",
    ))

    # Forecast beyond historical data
    if len(t_forecast) > 0 and len(dates) > 0:
        from datetime import datetime, timedelta
        try:
            last_date = datetime.strptime(dates[-1], "%Y-%m")
        except ValueError:
            last_date = datetime(2020, 1, 1)

        forecast_dates = []
        for m in t_forecast:
            d = last_date + timedelta(days=int(m) * 30)
            forecast_dates.append(d.strftime("%Y-%m"))

        fig.add_trace(go.Scatter(
            x=forecast_dates, y=r_forecast,
            mode="lines",
            line=dict(color="blue", width=2, dash="dash"),
            name="Forecast",
        ))

    eur = DeclineCurveEngine.calculate_eur(fit, econ_limit, forecast_months)
    fluid_label = "Oil" if fluid_col == "oil_vol" else "Gas"

    fig.update_layout(
        title=f"Decline Curve Analysis — {fluid_label}",
        xaxis_title="Date",
        yaxis_title=f"{fluid_label} Rate",
        height=400,
        margin=dict(l=60, r=20, t=50, b=60),
    )

    # Results summary
    results = dbc.Card(dbc.CardBody([
        html.H6("DCA Results"),
        html.P([
            html.B("Model: "), f"{fit.model.title()}", html.Br(),
            html.B("qi: "), f"{fit.qi:,.1f}", html.Br(),
            html.B("di: "), f"{fit.di:.4f} /month", html.Br(),
            html.B("b: "), f"{fit.b:.3f}", html.Br(),
            html.B("R²: "), f"{fit.r_squared:.4f}", html.Br(),
            html.B("EUR: "), f"{eur:,.0f}", html.Br(),
        ], className="small mb-0"),
    ]))

    return fig, results


@callback(
    Output("pd-compare-chart", "figure"),
    Input("pd-compare-btn", "n_clicks"),
    State("pd-multi-well-checklist", "value"),
    State("pd-fluid-checklist", "value"),
    State("pd-y-scale", "value"),
    prevent_initial_call=True,
)
def compare_wells(n_clicks, selected_wells, fluids, y_scale):
    if not selected_wells:
        return go.Figure().update_layout(title="Select wells to compare")

    fluids = fluids or ["oil"]
    primary_fluid = fluids[0]
    fluid_col = f"{primary_fluid}_vol"
    fluid_label = primary_fluid.title()
    colors = {"oil": "green", "gas": "red", "water": "blue"}

    fig = go.Figure()

    for wid_str in selected_wells:
        wid = int(wid_str)
        well = well_repo.get_by_id(wid)
        well_name = well["name"] if well else f"Well {wid}"
        records = prod_repo.get_by_well(wid)
        if not records:
            continue

        dates = [r["date"] for r in records]

        for fluid in fluids:
            col = f"{fluid}_vol"
            values = [r.get(col, 0) or 0 for r in records]
            fig.add_trace(go.Scatter(
                x=dates, y=values,
                mode="lines+markers",
                marker=dict(size=4),
                line=dict(color=colors.get(fluid, "gray")),
                name=f"{well_name} — {fluid.title()}",
                legendgroup=well_name,
            ))

    fig.update_layout(
        title=f"Multi-Well Comparison",
        xaxis_title="Date",
        yaxis_title="Volume",
        yaxis_type=y_scale or "linear",
        height=400,
        margin=dict(l=60, r=20, t=50, b=60),
    )
    return fig


# --- Helper functions ---

def _build_rate_chart(records: list, fluids: list,
                      y_scale: str) -> go.Figure:
    if not records:
        return go.Figure().update_layout(title="No production data")

    dates = [r["date"] for r in records]
    fig = go.Figure()

    fluid_config = {
        "oil": ("oil_vol", "green", "Oil (bbl)"),
        "gas": ("gas_vol", "red", "Gas (mcf)"),
        "water": ("water_vol", "blue", "Water (bbl)"),
    }

    for fluid in fluids:
        if fluid not in fluid_config:
            continue
        col, color, label = fluid_config[fluid]
        values = [r.get(col, 0) or 0 for r in records]
        fig.add_trace(go.Scatter(
            x=dates, y=values,
            mode="lines+markers",
            marker=dict(size=4),
            line=dict(color=color, width=2),
            name=label,
        ))

    fig.update_layout(
        title="Production Rate vs Time",
        xaxis_title="Date",
        yaxis_title="Volume",
        yaxis_type=y_scale,
        height=400,
        margin=dict(l=60, r=20, t=50, b=60),
    )
    return fig


def _build_cumulative_chart(records: list, fluids: list,
                            y_scale: str) -> go.Figure:
    if not records:
        return go.Figure().update_layout(title="No production data")

    dates = [r["date"] for r in records]
    fig = go.Figure()

    fluid_config = {
        "oil": ("oil_vol", "green", "Cum Oil"),
        "gas": ("gas_vol", "red", "Cum Gas"),
        "water": ("water_vol", "blue", "Cum Water"),
    }

    for fluid in fluids:
        if fluid not in fluid_config:
            continue
        col, color, label = fluid_config[fluid]
        values = [r.get(col, 0) or 0 for r in records]
        cum = np.cumsum(values).tolist()
        fig.add_trace(go.Scatter(
            x=dates, y=cum,
            mode="lines",
            line=dict(color=color, width=2),
            name=label,
        ))

    fig.update_layout(
        title="Cumulative Production",
        xaxis_title="Date",
        yaxis_title="Cumulative Volume",
        yaxis_type=y_scale,
        height=400,
        margin=dict(l=60, r=20, t=50, b=60),
    )
    return fig


def _build_summary_cards(cum: dict, avg_daily: float) -> list:
    cards = [
        ("Cum Oil", f"{cum.get('cum_oil', 0):,.0f} bbl", "success"),
        ("Cum Gas", f"{cum.get('cum_gas', 0):,.0f} mcf", "danger"),
        ("Cum Water", f"{cum.get('cum_water', 0):,.0f} bbl", "primary"),
        ("Avg Daily Oil", f"{avg_daily:,.1f} bbl/d", "warning"),
    ]
    return [
        dbc.Col(
            dbc.Card(dbc.CardBody([
                html.P(label, className="text-muted small mb-0"),
                html.H5(value, className="mb-0"),
            ]), color=color, outline=True),
            md=3,
        )
        for label, value, color in cards
    ]
