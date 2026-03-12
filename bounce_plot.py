"""
Plot second-bounce distance vs horizontal angular velocity
for a ball dropped vertically under pure gravity.

Physics:
  - Drop from h0 = 1 m, no horizontal velocity, only gravity
  - Rolling regime  (small ω): d = (2/7) * R * ω_h * 2*e_n*vz / g  → linear in ω
  - Sliding regime (large ω): d = 4 * μ * e_n * (1+e_n) * h0        → constant
  - Threshold: ω* = 7*μ*(1+e_n)*vz / (2*R)
"""

import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots

from physics import COURTS, g, r_ball, m

h0 = 1.0  # drop height (m)
vz = np.sqrt(2 * g * h0)  # impact speed (m/s)
R = r_ball

omega_rpm = np.linspace(0, 5000, 1000)
omega_rads = omega_rpm * 2 * np.pi / 60


def second_bounce_distance(omega_h_rads, e_n, mu):
    """Analytically compute second-bounce distance for given spin (rad/s)."""
    Jn = m * (1 + e_n) * vz
    vct_mag = R * omega_h_rads

    if vct_mag < 1e-9:
        return 0.0

    Jt_rolling_mag = (2.0 / 7.0) * m * vct_mag
    if Jt_rolling_mag <= mu * Jn:
        v_h = (2.0 / 7.0) * R * omega_h_rads  # linear in ω
    else:
        v_h = mu * (1 + e_n) * vz              # saturated (constant)

    T = 2 * e_n * vz / g
    return v_h * T


fig = go.Figure()

for court_name, court in COURTS.items():
    e_n = court["e_n"]
    mu = court["mu"]
    color = court["color"]

    distances = [second_bounce_distance(w, e_n, mu) * 100 for w in omega_rads]  # cm

    # Saturation threshold in RPM
    w_thresh_rads = (7 * mu * (1 + e_n) * vz) / (2 * R)
    w_thresh_rpm = w_thresh_rads * 60 / (2 * np.pi)
    d_sat_cm = 4 * mu * e_n * (1 + e_n) * h0 * 100

    fig.add_trace(go.Scatter(
        x=omega_rpm,
        y=distances,
        name=court["label"],
        line=dict(color=color, width=3),
    ))

    # Threshold marker
    fig.add_shape(
        type="line",
        x0=w_thresh_rpm, x1=w_thresh_rpm,
        y0=0, y1=d_sat_cm,
        line=dict(color=color, width=1, dash="dot"),
    )
    fig.add_annotation(
        x=w_thresh_rpm, y=d_sat_cm,
        text=f"ω* {court['label'][:4]}<br>{w_thresh_rpm:.0f} rpm",
        showarrow=False,
        font=dict(color=color, size=10),
        yshift=8,
    )

fig.update_layout(
    title=dict(
        text=f"Second-bounce distance vs spin (vertical drop from {h0} m, gravity only)",
        font=dict(color="white"),
    ),
    xaxis=dict(
        title="Horizontal angular velocity (RPM)",
        color="white",
        gridcolor="#333",
        zerolinecolor="#555",
    ),
    yaxis=dict(
        title="Second-bounce distance (cm)",
        color="white",
        gridcolor="#333",
        zerolinecolor="#555",
    ),
    legend=dict(font=dict(color="white"), bgcolor="#111"),
    paper_bgcolor="black",
    plot_bgcolor="#111",
    annotations=[
        dict(
            x=0.5, y=-0.12, xref="paper", yref="paper",
            text="Rolling regime (linear) → Sliding regime (flat) at each court's ω*",
            showarrow=False,
            font=dict(color="#aaa", size=11),
        )
    ],
)

fig.write_html("bounce_spin_dependency.html")
print("Saved bounce_spin_dependency.html")

# Print table of thresholds and saturation distances
print(f"\n{'Court':<10} {'e_n':>5} {'mu':>5} {'ω* (rpm)':>10} {'d_sat (cm)':>12}")
print("-" * 46)
for court_name, court in COURTS.items():
    e_n, mu = court["e_n"], court["mu"]
    w_thresh_rads = (7 * mu * (1 + e_n) * vz) / (2 * R)
    w_thresh_rpm = w_thresh_rads * 60 / (2 * np.pi)
    d_sat_cm = 4 * mu * e_n * (1 + e_n) * h0 * 100
    print(f"{court_name:<10} {e_n:>5.2f} {mu:>5.2f} {w_thresh_rpm:>10.0f} {d_sat_cm:>12.1f}")
