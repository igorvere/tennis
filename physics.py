import numpy as np

# ---------------- physics constants ----------------
g = 9.81
rho = 1.2
m = 0.057
r_ball = 0.033
A = np.pi * r_ball**2
C_D_default = 0.7
CL_SLOPE = 1.5
CL_MAX = 0.6

def kD(Cd):
    return (rho * Cd * A) / (2.0 * m)

def kM(CL):
    return (rho * A * CL) / (2.0 * m)

COURTS = {
    "hard": {
        "label": "Hard court",
        "desc": "Balanced bounce with neutral spin response.",
        "e_n": 0.75,
        "mu": 0.15,
        "spin_kick": 0.20,
        "color": "#0E77BF",
    },
    "clay": {
        "label": "Clay court",
        "desc": "High friction surface that amplifies topspin and slows the ball.",
        "e_n": 0.80,
        "mu": 0.22,
        "spin_kick": 0.28,
        "color": "#B75A2A",
    },
    "grass": {
        "label": "Grass court",
        "desc": "Low, skidding bounce with minimal spin interaction.",
        "e_n": 0.65,
        "mu": 0.10,
        "spin_kick": 0.12,
        "color": "#2E8B57",
    },
    "carpet": {
        "label": "Carpet (indoor)",
        "desc": "Very fast indoor surface with low friction and weak spin effects.",
        "e_n": 0.78,
        "mu": 0.08,
        "spin_kick": 0.08,
        "color": "#555555",
    },
}

# ---------------- trajectory integrator ----------------
def simulate(h0, v0, elev_deg, azim_deg, spin_rpm, spin_lat_rpm, spin_azim_deg, impact_x, impact_y, court_type, Cd=0.7):

    court = COURTS[court_type]

    e_n = court["e_n"]
    mu = court["mu"]
    spin_kick = court["spin_kick"]

    elev = np.radians(elev_deg)
    azim = np.radians(azim_deg)
    vx0 = v0 * np.cos(elev) * np.cos(azim)
    vy0 = v0 * np.cos(elev) * np.sin(azim)
    vz0 = v0 * np.sin(elev)

    vhat0 = np.array([vx0, vy0, vz0])/v0 
    grav = np.array([0, 0, -g])
    old_z = np.array([0, 0, 1])
    spin_azim = np.radians(spin_azim_deg) * -1
    omega_v = spin_lat_rpm * 2*np.pi/60 * vhat0
    new_z = old_z - vhat0 * np.inner(vhat0, old_z)  
    new_z = new_z / np.linalg.norm(new_z)
    new_y = np.cross(new_z, vhat0)
    omega_axis =  new_y * np.cos(spin_azim) + new_z * np.sin(spin_azim)
    omega_no_v = spin_rpm * 2*np.pi/60 * omega_axis
    omega = omega_v + omega_no_v

    k_d = kD(Cd)

    def magnus(v):
        vnorm = np.linalg.norm(v)
        if vnorm < 1e-8 or np.linalg.norm(omega) < 1e-8:
            return np.zeros(3)
        s = (np.linalg.norm(omega) * r_ball) / vnorm
        CL = min(CL_SLOPE * s, CL_MAX)
        vhat = v / vnorm
        omegahat = omega / np.linalg.norm(omega)
        return kM(CL) * (vnorm**2) * np.cross(omegahat, vhat)

    def accel(v):
        vnorm = np.linalg.norm(v)
        drag = -k_d * vnorm * v
        return grav + drag + magnus(v)

    p = np.array([-impact_x, -impact_y, h0])
    v = np.array([vx0, vy0, vz0])
    t = 0.0

    dt = 0.002
    traj = [p.copy()]
    v_traj = [v.copy()]
    T = []
    T.append(t)

    bounced = False
    for _ in range(5000):
        # RK4
        k1v = accel(v)
        k1p = v
        k2v = accel(v + 0.5*dt*k1v)
        k2p = v + 0.5*dt*k1v
        k3v = accel(v + 0.5*dt*k2v)
        k3p = v + 0.5*dt*k2v
        k4v = accel(v + dt*k3v)
        k4p = v + dt*k3v

        v += (dt/6)*(k1v + 2*k2v + 2*k3v + k4v)
        p += (dt/6)*(k1p + 2*k2p + 2*k3p + k4p)
        
        if p[2] <= 0 and not bounced:
            bounced = True

            # ---- pre-bounce state ----
            vx, vy, vz = v
            wx, wy, wz = omega

            R = r_ball
            I = (2/5) * m * R**2

            # Normal impulse magnitude (approx)
            Jn = m * (1 + e_n) * abs(vz)

            # Tangential slip velocity at contact point
            vct = np.array([vx + R*wy,  # x component
                            vy - R*wx]) # y component
            vct_mag = np.linalg.norm(vct)

            Jt = np.array([0.0, 0.0, 0.0])
            if vct_mag > 1e-6:
                # sliding friction impulse at Coulomb limit
                Jt_xy = -mu * Jn * (vct / vct_mag)   # 2D
                Jt = np.array([Jt_xy[0], Jt_xy[1], 0.0])

            # ---- update linear velocity ----
            v_post = v + Jt / m
            v_post[2] = -e_n * vz  # restitution vertical

            # ---- update spin ----
            # Δω = I^{-1} (r × Jt), with r = (0,0,-R)
            domega = np.array([ (R * Jt[1]) / I,
                                (-R * Jt[0]) / I,
                                0.0 ])
            omega_post = omega + domega
            omega_post *= 0.98  # small spin loss in impact (tunable)

            p[2] = 0.0
            omega = omega_post
            v = v_post

        elif p[2] <= 0 and bounced:
            break

        traj.append(p.copy())
        v_traj.append(v.copy())
        t += dt
        T.append(t)

        

    return np.array(traj), np.array(v_traj), np.array(T)