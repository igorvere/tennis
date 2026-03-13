"""
Plot second-bounce distance vs horizontal angular velocity.

Two model curves per court surface:
  ── Gravity only (analytical, no drag/Magnus)
  ── Full physics (drag + Magnus, numerical RK4)

Setup: ball dropped vertically from h0 = 1 m, zero initial horizontal velocity,
       pure horizontal spin ωy (around y-axis).
"""

import numpy as np
import plotly.graph_objects as go

from physics import COURTS, g, rho, m, r_ball, A, kD, kM, CL_SLOPE, CL_MAX, C_D_default

R  = r_ball
I  = (2.0 / 5.0) * m * R**2
h0 = 1.0                            # drop height (m)

# ──────────────────────────────────────────────
# Gravity-only analytical model
# ──────────────────────────────────────────────

def dist_gravity_only(omega_h, e_n, mu):
    """Closed-form second-bounce distance under pure gravity."""
    vz = np.sqrt(2 * g * h0)
    Jn = m * (1 + e_n) * vz
    vct = R * omega_h
    if vct < 1e-9:
        return 0.0
    Jt_roll = (2.0 / 7.0) * m * vct
    v_h = (Jt_roll if Jt_roll <= mu * Jn else mu * Jn) / m
    T = 2 * e_n * vz / g
    return v_h * T


# ──────────────────────────────────────────────
# Full-physics numerical model (RK4)
# ──────────────────────────────────────────────

def _magnus(v, omega):
    vnorm = np.linalg.norm(v)
    onorm = np.linalg.norm(omega)
    if vnorm < 1e-8 or onorm < 1e-8:
        return np.zeros(3)
    s = onorm * R / vnorm
    CL = min(CL_SLOPE * s, CL_MAX)
    return kM(CL) * vnorm**2 * np.cross(omega / onorm, v / vnorm)


def _accel(v, omega, k_d):
    vnorm = np.linalg.norm(v)
    return np.array([0.0, 0.0, -g]) - k_d * vnorm * v + _magnus(v, omega)


def _rk4_step(p, v, omega, k_d, dt):
    a1 = _accel(v, omega, k_d)
    a2 = _accel(v + 0.5 * dt * a1, omega, k_d)
    a3 = _accel(v + 0.5 * dt * a2, omega, k_d)
    a4 = _accel(v + dt * a3, omega, k_d)
    v_new = v + (dt / 6) * (a1 + 2 * a2 + 2 * a3 + a4)
    p_new = p + dt * (v + v_new) / 2        # trapezoidal on position
    return p_new, v_new


def _bounce(v, omega, e_n, mu):
    """Apply impulse-based bounce model. Returns v_post, omega_post."""
    vx, vy, vz = v
    wx, wy, wz = omega

    Jn = m * (1 + e_n) * abs(vz)
    vct = np.array([vx + R * wy, vy - R * wx])
    vct_mag = np.linalg.norm(vct)

    Jt = np.zeros(3)
    if vct_mag > 1e-6:
        Jt_roll_mag = (2.0 / 7.0) * m * vct_mag
        if Jt_roll_mag <= mu * Jn:
            Jt_xy = -(2.0 / 7.0) * m * vct
        else:
            Jt_xy = -mu * Jn * (vct / vct_mag)
        Jt[:2] = Jt_xy

    v_post = np.array([vx + Jt[0] / m,
                       vy + Jt[1] / m,
                       e_n * abs(vz)])
    domega = np.array([(R * Jt[1]) / I, (-R * Jt[0]) / I, 0.0])
    omega_post = (omega + domega) * 0.98
    return v_post, omega_post


def dist_full_physics(omega_h, e_n, mu, Cd=C_D_default, dt=0.001):
    """
    Numerically simulate drop → bounce → landing.
    omega_h: horizontal spin (rad/s) around y-axis.
    Returns second-bounce distance from first-bounce point.
    """
    omega = np.array([0.0, omega_h, 0.0])
    k_d = kD(Cd)

    # ── Phase 1: fall ────────────────────────
    p = np.array([0.0, 0.0, float(h0)])
    v = np.array([0.0, 0.0, -1e-4])

    for _ in range(30000):
        p, v = _rk4_step(p, v, omega, k_d, dt)
        if p[2] <= 0.0:
            break

    x_first = p[0]

    # ── Bounce ───────────────────────────────
    v, omega = _bounce(v, omega, e_n, mu)
    p[2] = 0.0

    # ── Phase 2: post-bounce flight ──────────
    for _ in range(30000):
        p, v = _rk4_step(p, v, omega, k_d, dt)
        if p[2] <= 0.0:
            break

    return abs(p[0] - x_first)


# ──────────────────────────────────────────────
# Sweep and plot
# ──────────────────────────────────────────────

omega_rpm  = np.linspace(0, 5000, 300)
omega_rads = omega_rpm * (2 * np.pi / 60)

fig = go.Figure()

for court_name, court in COURTS.items():
    e_n, mu = court["e_n"], court["mu"]
    color    = court["color"]
    label    = court["label"]

    # Gravity-only (vectorised, analytical)
    d_grav = np.array([dist_gravity_only(w, e_n, mu) for w in omega_rads]) * 100  # cm

    # Full physics (numerical)
    d_full = np.array([dist_full_physics(w, e_n, mu) for w in omega_rads]) * 100  # cm

    fig.add_trace(go.Scatter(
        x=omega_rpm, y=d_grav,
        name=f"{label} – gravity only",
        line=dict(color=color, width=2, dash="dash"),
        legendgroup=court_name,
    ))
    fig.add_trace(go.Scatter(
        x=omega_rpm, y=d_full,
        name=f"{label} – drag + Magnus",
        line=dict(color=color, width=3),
        legendgroup=court_name,
    ))

    # Saturation threshold annotation (gravity-only)
    vz0 = np.sqrt(2 * g * h0)
    w_thresh_rpm = (7 * mu * (1 + e_n) * vz0 / (2 * R)) * 60 / (2 * np.pi)
    d_sat_cm     = 4 * mu * e_n * (1 + e_n) * h0 * 100
    fig.add_shape(type="line",
                  x0=w_thresh_rpm, x1=w_thresh_rpm,
                  y0=0, y1=d_sat_cm,
                  line=dict(color=color, width=1, dash="dot"))
    fig.add_annotation(x=w_thresh_rpm, y=d_sat_cm,
                       text=f"ω* {label[:4]}", showarrow=False,
                       font=dict(color=color, size=10), yshift=10)

fig.update_layout(
    title=dict(
        text="Second-bounce distance vs spin  |  drop h₀ = 1 m, ωy only",
        font=dict(color="white", size=16),
    ),
    xaxis=dict(title="Horizontal angular velocity (RPM)",
               color="white", gridcolor="#333", zerolinecolor="#555"),
    yaxis=dict(title="Second-bounce distance from first bounce (cm)",
               color="white", gridcolor="#333", zerolinecolor="#555"),
    legend=dict(font=dict(color="white"), bgcolor="#111",
                orientation="v", x=1.02, y=1),
    paper_bgcolor="black",
    plot_bgcolor="#111",
    annotations=[
        dict(x=0.5, y=-0.13, xref="paper", yref="paper", showarrow=False,
             font=dict(color="#aaa", size=11),
             text="Dashed = gravity only (analytical) · Solid = drag + Magnus (RK4, Cd=0.7) · ω* marks rolling→sliding threshold"),
    ],
)

fig.write_html("bounce_spin_dependency.html")
print("Saved bounce_spin_dependency.html")

# Console summary
vz0 = np.sqrt(2 * g * h0)
print(f"\n{'Court':<10} {'e_n':>5} {'mu':>5}  {'ω* (rpm)':>9}  {'d_sat grav (cm)':>16}  {'d_sat full (cm)':>16}")
print("-" * 68)
for court_name, court in COURTS.items():
    e_n, mu = court["e_n"], court["mu"]
    w_thresh_rpm = (7 * mu * (1 + e_n) * vz0 / (2 * R)) * 60 / (2 * np.pi)
    d_sat_grav   = 4 * mu * e_n * (1 + e_n) * h0 * 100
    d_sat_full   = dist_full_physics(w_thresh_rpm * 2 * np.pi / 60 * 2, e_n, mu) * 100
    print(f"{court_name:<10} {e_n:>5.2f} {mu:>5.2f}  {w_thresh_rpm:>9.0f}  {d_sat_grav:>16.1f}  {d_sat_full:>16.1f}")
