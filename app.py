"""SubsurfaceAnalyzer — Dash entry point."""

import dash
import dash_bootstrap_components as dbc
from dash import html, dcc

from config import APP_TITLE, APP_HOST, APP_PORT, DEBUG
from database.schema import init_db
from components.navbar import create_navbar

# Initialize DB
init_db()

# Create Dash app with pages
app = dash.Dash(
    __name__,
    use_pages=True,
    external_stylesheets=[dbc.themes.FLATLY, dbc.icons.BOOTSTRAP],
    suppress_callback_exceptions=True,
    title=APP_TITLE,
)

app.layout = html.Div([
    create_navbar(),

    # Session stores — accessible cross-page
    dcc.Store(id="session-project-id", storage_type="session"),
    dcc.Store(id="session-well-id", storage_type="session"),
    dcc.Store(id="session-polygon-area", storage_type="session"),
    dcc.Store(id="session-polygon-vertices", storage_type="session"),

    # Page container
    dash.page_container,
])

server = app.server

if __name__ == "__main__":
    try:
        from waitress import serve
        print(f"Starting {APP_TITLE} on http://{APP_HOST}:{APP_PORT}")
        serve(server, host=APP_HOST, port=APP_PORT)
    except ImportError:
        print(f"Starting {APP_TITLE} in dev mode on http://{APP_HOST}:{APP_PORT}")
        app.run(host=APP_HOST, port=APP_PORT, debug=DEBUG)
