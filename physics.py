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

# ---------------- trajectory integrator ----------------
def simulate(h0, v0, elev_deg, azim_deg, spin_rpm, spin_lat_rpm, spin_azim_deg, impact_x, impact_y, Cd=0.7):
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

    dt = 0.002
    traj = [p.copy()]

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

        traj.append(p.copy())
        if p[2] <= 0:
            break

    return np.array(traj)