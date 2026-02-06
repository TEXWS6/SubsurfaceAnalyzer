"""Navigation bar component."""

import dash_bootstrap_components as dbc
from dash import html


def create_navbar():
    return dbc.Navbar(
        dbc.Container([
            dbc.NavbarBrand("SubsurfaceAnalyzer", href="/", className="fw-bold"),
            dbc.NavbarToggler(id="navbar-toggler"),
            dbc.Collapse(
                dbc.Nav([
                    dbc.NavItem(dbc.NavLink("Home", href="/")),
                    dbc.NavItem(dbc.NavLink("Log Viewer", href="/well-log-viewer")),
                    dbc.NavItem(dbc.NavLink("Formation Tops", href="/formation-tops")),
                    dbc.NavItem(dbc.NavLink("Contour Maps", href="/contour-mapping")),
                    dbc.NavItem(dbc.NavLink("Cross Section", href="/cross-section")),
                    dbc.NavItem(dbc.NavLink("Petrophysics", href="/petrophysics")),
                    dbc.NavItem(dbc.NavLink("Production", href="/production-data")),
                ], navbar=True),
                id="navbar-collapse",
                navbar=True,
            ),
        ], fluid=True),
        color="primary",
        dark=True,
        sticky="top",
    )
