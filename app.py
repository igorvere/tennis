import plotly.graph_objects as go
from dash import Dash, dcc, html, Input, Output, State
import numpy as np
from shots import SHOT_PRESETS, preset_options

from physics import simulate

import time

neon_net = "#00eaff"
neon_lines = "#b25cd1"

# ---------------- tennis court drawing ----------------
court_length = 23.77
court_width = 8.23
halfW = court_width / 2
service = 6.40
NET_H = 0.914   # real tennis net height at center
NET_X = court_length / 2      # net plane location in your coordinate system
camera = None
# -------- Realistic tennis net (curved + top tape + mesh cords) --------
def make_realistic_net():
    N = 40  # number of vertical mesh cords
    xs = []
    ys = []
    zs = []

    # Coordinates
    x_net = court_length / 2
    y_vals = np.linspace(-halfW, halfW, N)

    # Net height follows sagged line: center = 0.914 m, posts = 1.07 m
    h_center = 0.914
    h_post = 1.07

    # Fit a quadratic curve h(y)
    # h(y) = a*y^2 + h_center,  with h(halfW) = h_post
    a = (h_post - h_center) / (halfW**2)

    for y in y_vals:
        h_y = a * (y**2) + h_center
        xs.extend([x_net, x_net])
        ys.extend([y, y])
        zs.extend([0.0, h_y])

    # Vertical cords
    cords = go.Scatter3d(
        x=xs,
        y=ys,
        z=zs,
        mode="lines",
        line=dict(color=neon_net, width=3),
        opacity=0.9
    )

    # Top tape (white)
    tape_y = np.linspace(-halfW, halfW, 100)
    tape_height = a*tape_y**2 + h_center
    tape = go.Scatter3d(
        x=[x_net]*100,
        y=tape_y,
        z=tape_height,
        mode="lines",
        line=dict(color=neon_net, width=12)
    )

    return cords, tape


def compute_net_clearance(x, z):
    # Find index where trajectory crosses the net x-position
    idx = np.argmin(np.abs(x - NET_X))
    z_at_net = z[idx]
    clearance = z_at_net - NET_H
    return float(clearance), float(z_at_net)


def compute_landing_depth(x, z):
    # Find first bounce: z <= 0
    ground_idx = np.where(z <= 0)[0]
    if len(ground_idx) == 0:
        return None  # ball never lands (rare)
    first = ground_idx[0]

    landing_x = x[first]
    # Distance from opponent's baseline (x = court_length)
    depth = court_length - landing_x
    return float(depth), float(landing_x)

def plot_court_fig(X, Y, Z, camera):
    mesh = go.Mesh3d(
        x=[0, court_length, court_length, 0],
        y=[-halfW, -halfW, halfW, halfW],
        z=[0, 0, 0, 0],
        color="black",
        opacity=0.0,    # fully transparent floor
        showscale=False
    )


    lines = []

    # Outer lines
    outer_x = [0, court_length, court_length, 0, 0]
    outer_y = [-halfW, -halfW, halfW, halfW, -halfW]
    lines.append(go.Scatter3d(x=outer_x, y=outer_y, z=[0]*5,
        mode="lines", line=dict(color=neon_lines, width=8)))

    # Service lines
    for s in [court_length/2 - service, court_length/2 + service]:
        lines.append(go.Scatter3d(
            x=[s, s], y=[-halfW, halfW], z=[0,0],
            mode="lines", line=dict(color=neon_lines, width=8)
        ))

    # Center service line
    lines.append(go.Scatter3d(
        x=[court_length/2 - service, court_length/2 + service],
        y=[0,0], z=[0,0],
        mode="lines", line=dict(color=neon_lines, width=8)
    ))

   # Add realistic net
    net_cords, net_tape = make_realistic_net()
    lines.append(net_cords)
    lines.append(net_tape)

    # Ball path
    trail = go.Scatter3d(
        x=X, y=Y, z=Z,
        mode="lines", line=dict(color="yellow", width=6)
    )

    ball = go.Scatter3d(
        x=[X[-1]], y=[Y[-1]], z=[Z[-1]],
        mode="markers", marker=dict(color="yellow", size=6)
    )

    fig = go.Figure(data=[mesh] + lines + [trail, ball])

    fig.update_layout(
        scene=dict(
            xaxis=dict(visible=False, backgroundcolor="black"),
            yaxis=dict(visible=False, backgroundcolor="black"),
            zaxis=dict(visible=False, backgroundcolor="black"),
            aspectmode="data",
            camera = camera if camera else dict(
                eye=dict(x=1.6, y=-2.2, z=1))
        ),
        margin=dict(l=0, r=0, t=0, b=0),
        showlegend=False, 
        paper_bgcolor="black",
        plot_bgcolor="black",
    )

    return fig




# ---------------- Dash app ----------------
app = Dash(__name__)
server = app.server
slider_params = dict(updatemode = "mouseup", marks=None, tooltip={"placement": "bottom", "always_visible": True})
slider_params2 = dict(updatemode = "mouseup", tooltip={"placement": "bottom", "always_visible": True})

controls = [
    html.H3("Adjust Shot"),

    html.Label("Speed (km/h)"),
    dcc.Slider(0, 250, 1, value=90, id="speed", **slider_params),

    html.Br(),
    html.Label("launch height (cm)"),
    dcc.Slider(0, 350, 1, value=100, id="height", **slider_params),

    html.Br(),
    html.Label("Launch angle (°)"),
    dcc.Slider(-10, 30, 0.1, value=10, id="elevation", **slider_params),

    html.Br(),
    html.Label("Azimuth (°)"),
    dcc.Slider(-20, 20, 1, value=0, id="azimuth", **slider_params),

    html.Br(),
    html.Label("Spin (rpm)"),
    dcc.Slider(-4000, 4000, 10, value=1500, id="spin", **slider_params),


    html.Br(),
    html.Label("Spin (°)"),

    dcc.Slider(id="spin_azim_deg", min=-90, max=90, step=1, value=0,
        marks={-90: "Left", 0: "Center", 90: "Right"}, **slider_params2
    ),

    html.Br(),
    html.Label("Spin lateral(rpm)"),
    dcc.Slider(-4000, 4000, 10, value=1500, id="spin_lat", **slider_params),


    html.Br(),
    html.Label("Depth (m from baseline)"),
    dcc.Slider(-NET_X, NET_X, 0.1, value=0, id="impact_x", **slider_params),

    html.Br(),
    html.Label("Lateral shift (m from center)"),
    dcc.Slider(-5, 5, 0.1, value=0, id="impact_y", **slider_params),

    dcc.Store(id="prev-shot"),

    html.H3("Shot Metrics"),
    html.Div(id="metric-net-clearance", style={"marginTop": "10px", "fontSize": "18px"}),
    html.Div(id="metric-landing-depth", style={"marginTop": "5px", "fontSize": "18px"}),
    html.Div(id="metric-compute", style={"marginTop": "15px", "fontSize": "18px"}),

    ]


app.layout = html.Div(
    id="graph-area",
    style={
        "height": "100vh",
        "background": "black",
        "position": "relative",
        "overflow": "hidden",
    },
    children=[

        dcc.Graph(
                id="court-graph",
                style={"height": "100%"},
                config={
                    "displayModeBar": False,
                    "scrollZoom": True,      # 🔑 REQUIRED
                    "doubleClick": "reset",  # optional
                },
            ),

        # Top-right buttons
        html.Div(
            style={
                "position": "absolute",
                "top": "12px",
                "right": "12px",
                "zIndex": 9999,
                "display": "flex",
                "gap": "8px",
            },
            children=[
                html.Button("＋", id="zoom-in"),
                html.Button("－", id="zoom-out"),
                html.Button("⟳", id="reset-camera"),
                html.Button("⛶", **{"data-action": "fullscreen"}),
                html.Button("☰", **{"data-action": "toggle"}),
            ],
        ),



        # Backdrop
        html.Div(
            id="backdrop",
            **{"data-action": "close"},
            style={
                "position": "absolute",
                "inset": 0,
                "background": "rgba(0,0,0,0.55)",
                "display": "none",
                "zIndex": 5,
            },
        ),

        # Drawer
        html.Div(
            id="drawer",
            style={
                "position": "absolute",
                "top": 0,
                "right": 0,
                "height": "100%",
                "width": "320px",
                "background": "#111",
                "color": "white",
                "zIndex": 8,
                "display": "flex",
                "flexDirection": "column",
                "boxShadow": "-6px 0 16px rgba(0,0,0,0.6)",
                "transform": "translateX(100%)",
                "transition": "transform 0.25s ease",
            },
            children=[
                html.Div(id="resize", style={
                    "position": "absolute",
                    "left": 0,
                    "top": 0,
                    "bottom": 0,
                    "width": "8px",
                    "cursor": "ew-resize",
                    "background": "rgba(255,255,255,0.05)",
                }),

                html.Div("Controls", style={
                    "padding": "12px",
                    "borderBottom": "1px solid #222",
                    "fontWeight": 700,
                }),

                html.Div(
                    style={"padding": "12px", "borderBottom": "1px solid #222"},
                    children=[
                        html.Label("Shot preset"),
                        dcc.Dropdown(
                            id="preset-dropdown",
                            options=preset_options,
                            className="dark-dropdown", 
                            placeholder="Choose a preset...",
                            searchable=False,
                            clearable=False,
                        ),
                    ],
                ),

                html.Div(id="controls-panel",
                    style={
                        "flex": "1",              # 🔑 take remaining height
                        "overflowY": "auto",      # 🔑 single scroll owner
                        "overflowX": "hidden",
                        "padding": "0",           # padding moves inside sections
                    },
                    children=[
                        html.Button(
                            "▶ Launch parameters",
                            id="toggle-launch",
                            n_clicks=0,
                            style={
                                "width": "100%",
                                "textAlign": "left",
                                "background": "#111",
                                "color": "white",
                                "border": "none",
                                "padding": "12px",
                                "fontSize": "16px",
                                "cursor": "pointer",
                            },
                        ),
                        html.Div(
                            id="launch-section",
                            style={
                                "display": "none",
                                "padding": "12px",
                                "borderBottom": "1px solid #222",
                            },
                            children=controls,
                        ),
                    ]
                )
            ],
        ),
    ],
)

@app.callback(
    Output("court-graph", "figure"),
    Output("prev-shot", "data"),
    Output("metric-net-clearance", "children"),
    Output("metric-landing-depth", "children"),
    Output("metric-compute", "children"),
    Input("speed", "value"),
    Input("height", "value"),
    Input("elevation", "value"),
    Input("azimuth", "value"),
    Input("spin", "value"),
    Input("spin_lat", "value"),
    Input("spin_azim_deg", "value"),
    Input("impact_x", "value"),
    Input("impact_y", "value"),
    State("prev-shot", "data"),
)
def update(speed, height, elevation, azimuth, spin, spin_lat, spin_azim, impact_x, impact_y, prev_shot):
    
    time0 = time.time()

    cc = 1000/3600 
    traj = simulate(height/100, speed * cc, elevation, azimuth, spin, spin_lat, spin_azim, impact_x, impact_y)
    X, Y, Z = traj[:,0], traj[:,1], traj[:,2]

    fig =  plot_court_fig(X, Y, Z, camera)
    # Draw previous shot if exists
    if prev_shot:
        fig.add_trace(go.Scatter3d(
            x=prev_shot["x"],
            y=prev_shot["y"],
            z=prev_shot["z"],
            mode="lines",
            line=dict(color="yellow", width=8, dash="dash"),
            opacity=0.6,
            name="Previous shot"
        ))

    new_prev = {
        "x": X.tolist(),
        "y": Y.tolist(),
        "z": Z.tolist()
    }

        # Compute metrics
    net_clear_cm, z_at_net = compute_net_clearance(X, Z)
    landing_info = compute_landing_depth(X, Z)

    if landing_info:
        landing_depth, landing_x = landing_info
        landing_text = f"Landing depth: {landing_depth:.2f} m"
    else:
        landing_text = "Landing depth: (no landing detected)"

    clear_text = f"Net clearance: {net_clear_cm*100:.1f} cm"
    compute_took_txt = f"Compute took: {time.time() - time0:.2f} sec"

    return fig, new_prev, clear_text, landing_text, compute_took_txt

@app.callback(
    Input("court-graph", "relayoutData")
)
def update_camera(relayout):
    if relayout and "scene.camera" in relayout:
        camera = relayout["scene.camera"]

@app.callback(
    Output("launch-section", "style"),
    Input("toggle-launch", "n_clicks"),
    State("launch-section", "style"),
)
def toggle_launch(n, style):
    if n % 2 == 1:
        return {**style, "display": "block"}
    return {**style, "display": "none"}

@app.callback(
    Output("toggle-launch", "children"),
    Input("toggle-launch", "n_clicks"),
)
def rotate_arrow(n):
    return "▼ Launch parameters" if n % 2 else "▶ Launch parameters"

@app.callback(
    Output("speed", "value"),
    Output("height", "value"),
    Output("elevation", "value"),
    Output("azimuth", "value"),
    Output("spin", "value"),
    Output("spin_lat", "value"),
    Output("spin_azim_deg", "value"),
    Output("impact_x", "value"),
    Output("impact_y", "value"),
    Input("preset-dropdown", "value"),
    prevent_initial_call=True
)
def load_preset(preset_key):

    if preset_key is None:
        raise dash.exceptions.PreventUpdate

    p = SHOT_PRESETS[preset_key]

    return (
        p["launch_speed_kmh"],
        p["launch_height_m"]*100,
        p["launch_angle_deg"],
        p["launch_azimuth_deg"],
        p["spin_rpm"],
        p["spin_gyro_rpm"], 
        p["spin_azim_deg"], 
        p['depth_m'],
        p["center_shift_m"]
    )

from dash import callback_context
from dash import Patch

@app.callback(
    Output("court-graph", "figure", allow_duplicate=True),
    Input("zoom-in", "n_clicks"),
    Input("zoom-out", "n_clicks"),
    Input("reset-camera", "n_clicks"),
    State("court-graph", "figure"),
    prevent_initial_call=True
)
def zoom_camera(zin, zout, reset, fig):
    ctx = callback_context
    trigger = ctx.triggered[0]["prop_id"].split(".")[0]

    # Default camera
    default_eye = {"x": 1.5, "y": -2.0, "z": 1.2}

    camera = fig.get("layout", {}).get("scene", {}).get("camera", {})
    eye = camera.get("eye", default_eye)

    if trigger == "zoom-in":
        scale = 0.85
        new_eye = {k: v * scale for k, v in eye.items()}

    elif trigger == "zoom-out":
        scale = 1.15
        new_eye = {k: v * scale for k, v in eye.items()}

    elif trigger == "reset-camera":
        new_eye = default_eye

    patch = Patch()
    patch["layout"]["scene"]["camera"]["eye"] = new_eye
    return patch

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8050)
