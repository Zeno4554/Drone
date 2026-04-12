"""
Drone Swarm Hybrid Communication - Live Animation
Cellular (LTE/5G style) + RF direct links

This is a Python adaptation of the provided MATLAB simulation with:
- live 3D drone motion
- dynamic cellular and RF link rendering
- real-time status text panel

Requested simplification:
- no SINR bar graph
- no hybrid throughput bar graph
- no scrolling SINR timeseries graph
"""
import matplotlib.pyplot as plt
import numpy as np



def main() -> None:
    # ============================================================
    # PARAMETERS
    # ============================================================
    n_drones = 6
    total_time_s = 120.0
    dt = 0.2
    t_vec = np.arange(0.0, total_time_s + dt, dt)
    steps = t_vec.size

    area_xy = 1000.0
    max_alt = 150.0
    bs = np.array([500.0, 500.0, 0.0])

    # Cellular
    f_cell = 2.4e9
    pt_ue_dbm = 23.0
    nf_cell_db = 7.0
    bw_cell_hz = 10e6
    n_cell = 3.5
    d0_cell = 100.0

    # RF direct
    f_rf = 915e6
    pt_rf_dbm = 20.0
    nf_rf_db = 5.0
    bw_rf_hz = 1e6
    n_rf = 2.2
    d0_rf = 10.0
    rf_range = 400.0

    # Physical constants
    c = 3e8
    k_b = 1.38e-23
    t_noise = 290.0

    # Derived link parameters
    pl0_cell_db = 20.0 * np.log10(4.0 * np.pi * d0_cell * f_cell / c)
    pl0_rf_db = 20.0 * np.log10(4.0 * np.pi * d0_rf * f_rf / c)

    n0_cell_dbm = 10.0 * np.log10(k_b * t_noise * bw_cell_hz) + 30.0 + nf_cell_db
    n0_rf_dbm = 10.0 * np.log10(k_b * t_noise * bw_rf_hz) + 30.0 + nf_rf_db

    sinr_min_cell_db = 5.0
    sinr_min_rf_db = 3.0

    anim_skip = 1
    trail_len = 40

    # ============================================================
    # PRE-COMPUTE TRAJECTORIES
    # ============================================================
    rng = np.random.default_rng(42)

    pos = np.zeros((n_drones, 3, steps), dtype=float)
    vel = np.zeros((n_drones, 3), dtype=float)
    waypoints = np.zeros((n_drones, 3), dtype=float)

    for i in range(n_drones):
        pos[i, :, 0] = np.array(
            [
                rng.uniform(0.0, area_xy),
                rng.uniform(0.0, area_xy),
                rng.uniform(50.0, 150.0),
            ]
        )
        waypoints[i, :] = np.array(
            [
                rng.uniform(0.0, area_xy),
                rng.uniform(0.0, area_xy),
                rng.uniform(50.0, 150.0),
            ]
        )
        spd = rng.uniform(12.0, 20.0)
        direction = waypoints[i, :] - pos[i, :, 0]
        vel[i, :] = direction / (np.linalg.norm(direction) + 1e-9) * spd

    for k in range(1, steps):
        for i in range(n_drones):
            cur = pos[i, :, k - 1].copy()
            if np.linalg.norm(waypoints[i, :] - cur) < 25.0:
                waypoints[i, :] = np.array(
                    [
                        rng.uniform(0.0, area_xy),
                        rng.uniform(0.0, area_xy),
                        rng.uniform(50.0, 150.0),
                    ]
                )
                spd = rng.uniform(12.0, 20.0)
                direction = waypoints[i, :] - cur
                vel[i, :] = direction / (np.linalg.norm(direction) + 1e-9) * spd

            nxt = cur + vel[i, :] * dt
            nxt[0] = np.clip(nxt[0], 0.0, area_xy)
            nxt[1] = np.clip(nxt[1], 0.0, area_xy)
            nxt[2] = np.clip(nxt[2], 20.0, max_alt)
            pos[i, :, k] = nxt

    # ============================================================
    # PRE-COMPUTE CHANNEL DATA
    # ============================================================
    print("Pre-computing channel data...")

    sinr_cell = np.zeros((n_drones, steps), dtype=float)
    sinr_rf = np.full((n_drones, n_drones, steps), -np.inf, dtype=float)
    thr = np.zeros((n_drones, steps), dtype=float)

    for k in range(steps):
        c_cell = np.zeros(n_drones, dtype=float)
        best_rf = np.zeros(n_drones, dtype=float)

        # Cellular SINR and cellular-only capacity for each drone.
        for i in range(n_drones):
            p_i = pos[i, :, k]
            d_bs = np.linalg.norm(p_i - bs)
            pl_c = pl0_cell_db + 10.0 * n_cell * np.log10(max(d_bs, d0_cell) / d0_cell) + 6.0 * rng.normal()
            sinr_cell[i, k] = pt_ue_dbm - pl_c - n0_cell_dbm

            if sinr_cell[i, k] >= sinr_min_cell_db:
                c_cell[i] = bw_cell_hz * np.log2(1.0 + 10.0 ** (sinr_cell[i, k] / 10.0)) / 1e6

        # Pairwise RF links computed once and mirrored to keep adjacency symmetric.
        for i in range(n_drones):
            p_i = pos[i, :, k]
            for j in range(i + 1, n_drones):
                p_j = pos[j, :, k]
                d_ij = np.linalg.norm(p_i - p_j)
                if d_ij < rf_range:
                    pl_r = pl0_rf_db + 10.0 * n_rf * np.log10(max(d_ij, d0_rf) / d0_rf) + 2.0 * rng.normal()
                    sinr_ij = pt_rf_dbm - pl_r - n0_rf_dbm
                    sinr_rf[i, j, k] = sinr_ij
                    sinr_rf[j, i, k] = sinr_ij
                    if sinr_ij >= sinr_min_rf_db:
                        c_rf = bw_rf_hz * np.log2(1.0 + 10.0 ** (sinr_ij / 10.0)) / 1e6
                        best_rf[i] = max(best_rf[i], c_rf)
                        best_rf[j] = max(best_rf[j], c_rf)

        thr[:, k] = c_cell + best_rf

    print("Done. Starting animation...\n")

    # ============================================================
    # FIGURE SETUP
    # ============================================================
    colors = plt.get_cmap("tab10")(np.linspace(0, 1, n_drones))
    drone_names = [f"D{i + 1}" for i in range(n_drones)]

    plt.style.use("dark_background")
    fig = plt.figure(figsize=(14, 8), facecolor="#141923")
    fig.canvas.manager.set_window_title("DRONE SWARM LIVE SIM")

    ax3d = fig.add_axes([0.03, 0.20, 0.72, 0.76], projection="3d", facecolor="#0d1220")
    ax3d.grid(True, alpha=0.35)
    ax3d.set_xlim(0.0, area_xy)
    ax3d.set_ylim(0.0, area_xy)
    ax3d.set_zlim(0.0, max_alt + 30.0)
    ax3d.set_xlabel("X (m)")
    ax3d.set_ylabel("Y (m)")
    ax3d.set_zlabel("Altitude (m)")
    ax3d.set_title("[ LIVE DRONE SWARM VIEW ]", color="cyan", fontsize=13, fontweight="bold", pad=10)
    ax3d.view_init(elev=28.0, azim=42.0)

    # Base station marker
    ax3d.scatter([bs[0]], [bs[1]], [bs[2]], s=260, c="red", marker="P")
    ax3d.text(bs[0] + 20.0, bs[1] + 20.0, bs[2] + 10.0, "gNB", color="#ff6f6f", fontsize=11, fontweight="bold")

    # Animated objects
    h_trail = []
    h_drones = []
    h_cell_links = []
    h_rf_links = [[None for _ in range(n_drones)] for _ in range(n_drones)]
    h_labels = []

    for i in range(n_drones):
        trail, = ax3d.plot([], [], [], lw=1.2, color=(*colors[i, :3], 0.25))
        drone = ax3d.scatter([], [], [], s=120, c=[colors[i, :3]], marker="D")
        cell_link, = ax3d.plot([], [], [], "--", lw=1.4, color=(0.30, 0.55, 1.0, 0.70))
        label = ax3d.text(0.0, 0.0, 0.0, drone_names[i], color=colors[i, :3], fontsize=9, fontweight="bold")

        h_trail.append(trail)
        h_drones.append(drone)
        h_cell_links.append(cell_link)
        h_labels.append(label)

        for j in range(n_drones):
            rf_link, = ax3d.plot([], [], [], "-", lw=2.0, color=(0.15, 1.0, 0.35, 0.8))
            h_rf_links[i][j] = rf_link

    # Status panel
    ax_status = fig.add_axes([0.03, 0.02, 0.72, 0.14], facecolor="#0d1220")
    ax_status.axis("off")
    h_status = ax_status.text(
        0.01,
        0.55,
        "",
        transform=ax_status.transAxes,
        ha="left",
        va="center",
        fontsize=8.7,
        family="monospace",
        color="#d7f0d7",
    )

    # Right-side info panel (no graphs)
    ax_info = fig.add_axes([0.77, 0.20, 0.21, 0.76], facecolor="#0d1220")
    ax_info.axis("off")
    h_time = ax_info.text(
        0.5,
        0.93,
        "t =   0.0 s",
        ha="center",
        va="center",
        color="cyan",
        fontsize=15,
        fontweight="bold",
        family="monospace",
    )

    h_legend = ax_info.text(
        0.04,
        0.78,
        "LEGEND\n"
        "- - Cellular Link (2.4 GHz)\n"
        "___ RF D2D Link (915 MHz)\n"
        "D  UAV Drone\n"
        "P  gNB",
        ha="left",
        va="top",
        fontsize=10,
        color="#b7dbff",
        family="monospace",
        linespacing=1.4,
    )
    _ = h_legend

    h_live_stats = ax_info.text(
        0.04,
        0.50,
        "",
        ha="left",
        va="top",
        fontsize=10,
        color="#f6f0d2",
        family="monospace",
        linespacing=1.35,
    )

    # ============================================================
    # ANIMATION LOOP
    # ============================================================
    plt.show(block=False)

    try:
        for k in range(0, steps, anim_skip):
            if not plt.fignum_exists(fig.number):
                break

            # Update drone geometry and cellular links
            for i in range(n_drones):
                p_i = pos[i, :, k]

                k0 = max(0, k - trail_len)
                h_trail[i].set_data(pos[i, 0, k0 : k + 1], pos[i, 1, k0 : k + 1])
                h_trail[i].set_3d_properties(pos[i, 2, k0 : k + 1])

                h_drones[i]._offsets3d = ([p_i[0]], [p_i[1]], [p_i[2]])
                h_labels[i].set_position((p_i[0] + 18.0, p_i[1] + 18.0))
                h_labels[i].set_3d_properties(p_i[2] + 8.0)

                if sinr_cell[i, k] >= sinr_min_cell_db:
                    link_color = (0.30, 0.55, 1.0, 0.70)
                else:
                    link_color = (1.0, 0.25, 0.25, 0.35)

                h_cell_links[i].set_data([p_i[0], bs[0]], [p_i[1], bs[1]])
                h_cell_links[i].set_3d_properties([p_i[2], bs[2]])
                h_cell_links[i].set_color(link_color)

            # Update RF D2D links
            for i in range(n_drones):
                p_i = pos[i, :, k]
                for j in range(i + 1, n_drones):
                    p_j = pos[j, :, k]
                    if sinr_rf[i, j, k] >= sinr_min_rf_db:
                        h_rf_links[i][j].set_data([p_i[0], p_j[0]], [p_i[1], p_j[1]])
                        h_rf_links[i][j].set_3d_properties([p_i[2], p_j[2]])
                    else:
                        h_rf_links[i][j].set_data([], [])
                        h_rf_links[i][j].set_3d_properties([])

            # Update status text
            n_cell_ok = int(np.sum(sinr_cell[:, k] >= sinr_min_cell_db))
            n_rf_ok = int(np.sum(sinr_rf[:, :, k] >= sinr_min_rf_db) // 2)

            header = "  {:<4}  {:<8}  {:<18}  {:<10}  {:<10}".format(
                "Node", "Dist(m)", "Cellular SINR", "RF Peers", "Thr(Mbps)"
            )
            lines = [header, "  " + "-" * 62]

            for i in range(n_drones):
                p_i = pos[i, :, k]
                d_bs = np.linalg.norm(p_i - bs)
                if sinr_cell[i, k] >= sinr_min_cell_db:
                    cs = f"{sinr_cell[i, k]:+4.1f} dB [OK]"
                else:
                    cs = f"{sinr_cell[i, k]:+4.1f} dB [OUT]"
                rf_cnt = int(np.sum(sinr_rf[i, :, k] >= sinr_min_rf_db))
                lines.append(f"  D{i + 1:<3}  {d_bs:<8.0f}  {cs:<18}  {rf_cnt:<10d}  {thr[i, k]:.3f}")

            lines.append(
                "\n  Active: {} Cellular | {} RF D2D Links | System Avg: {:.3f} Mbps".format(
                    n_cell_ok, n_rf_ok, float(np.mean(thr[:, k]))
                )
            )
            h_status.set_text("\n".join(lines))

            h_time.set_text(f"t = {t_vec[k]:6.1f} / {int(total_time_s)} s")
            h_live_stats.set_text(
                "LIVE SUMMARY\n"
                f"Cellular OK: {n_cell_ok}/{n_drones}\n"
                f"RF Links:    {n_rf_ok}\n"
                f"Avg Thr:     {np.mean(thr[:, k]):.2f} Mbps"
            )

            plt.pause(0.001)

    except KeyboardInterrupt:
        print("Animation interrupted by user.")

    print("Animation complete.")
    plt.show()


if __name__ == "__main__":
    main()
