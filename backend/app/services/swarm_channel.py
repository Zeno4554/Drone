"""
Shared hybrid communication channel model.

Implements:
  - Cellular uplink (LTE/5G-style, 2.4 GHz)
  - RF drone-to-drone direct links (915 MHz)
  - Hybrid throughput = cellular capacity + best RF peer capacity

Used by both HybridSwarmSim and SwarmObstacleSim.
"""

import numpy as np

# ── Physical constants ────────────────────────────────────────────────────────

_C      = 3e8          # speed of light (m/s)
_K_B    = 1.38e-23     # Boltzmann constant
_T_NOISE = 290.0       # noise temperature (K)

# ── Default channel parameters ────────────────────────────────────────────────

# Cellular (2.4 GHz LTE)
CELL_FREQ_HZ    = 2.4e9
CELL_PT_DBM     = 23.0
CELL_NF_DB      = 7.0
CELL_BW_HZ      = 10e6
CELL_PATH_EXP   = 3.5
CELL_D0_M       = 100.0
CELL_SINR_MIN   = 5.0    # dB — minimum for usable link

# RF D2D (915 MHz)
RF_FREQ_HZ      = 915e6
RF_PT_DBM       = 20.0
RF_NF_DB        = 5.0
RF_BW_HZ        = 1e6
RF_PATH_EXP     = 2.2
RF_D0_M         = 10.0
RF_RANGE_M      = 400.0
RF_SINR_MIN     = 3.0    # dB

# ── Pre-computed reference path losses ───────────────────────────────────────

_PL0_CELL = 20.0 * np.log10(4.0 * np.pi * CELL_D0_M * CELL_FREQ_HZ / _C)
_PL0_RF   = 20.0 * np.log10(4.0 * np.pi * RF_D0_M   * RF_FREQ_HZ   / _C)

_N0_CELL  = 10.0 * np.log10(_K_B * _T_NOISE * CELL_BW_HZ) + 30.0 + CELL_NF_DB
_N0_RF    = 10.0 * np.log10(_K_B * _T_NOISE * RF_BW_HZ)   + 30.0 + RF_NF_DB


# ── Public API ────────────────────────────────────────────────────────────────

def compute_channel(
    positions: np.ndarray,           # shape (n_drones, 3) — x, y, z in metres
    bs: np.ndarray,                  # shape (3,)           — base-station position
    rng: np.random.Generator,
    n_drones: int | None = None,
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """
    Compute per-drone cellular SINR, pairwise RF SINR, and hybrid throughput.

    Returns
    -------
    sinr_cell : ndarray (n_drones,)
        Cellular SINR in dB for each drone (can be below CELL_SINR_MIN).
    sinr_rf : ndarray (n_drones, n_drones)
        Pairwise RF SINR in dB; -inf where link does not exist (out of range).
    throughput : ndarray (n_drones,)
        Hybrid throughput in Mbps = cellular_capacity + best_rf_peer_capacity.
    """
    if n_drones is None:
        n_drones = positions.shape[0]

    sinr_cell = np.zeros(n_drones, dtype=float)
    sinr_rf   = np.full((n_drones, n_drones), -np.inf, dtype=float)
    c_cell    = np.zeros(n_drones, dtype=float)
    best_rf   = np.zeros(n_drones, dtype=float)

    # Cellular SINR per drone
    for i in range(n_drones):
        d_bs  = float(np.linalg.norm(positions[i] - bs))
        pl    = (_PL0_CELL
                 + 10.0 * CELL_PATH_EXP * np.log10(max(d_bs, CELL_D0_M) / CELL_D0_M)
                 + 6.0 * rng.normal())
        sinr_cell[i] = CELL_PT_DBM - pl - _N0_CELL
        if sinr_cell[i] >= CELL_SINR_MIN:
            c_cell[i] = CELL_BW_HZ * np.log2(1.0 + 10.0 ** (sinr_cell[i] / 10.0)) / 1e6

    # Pairwise RF SINR (upper triangle, then mirrored)
    for i in range(n_drones):
        for j in range(i + 1, n_drones):
            d_ij = float(np.linalg.norm(positions[i] - positions[j]))
            if d_ij >= RF_RANGE_M:
                continue
            pl = (_PL0_RF
                  + 10.0 * RF_PATH_EXP * np.log10(max(d_ij, RF_D0_M) / RF_D0_M)
                  + 2.0 * rng.normal())
            s_ij = RF_PT_DBM - pl - _N0_RF
            sinr_rf[i, j] = s_ij
            sinr_rf[j, i] = s_ij
            if s_ij >= RF_SINR_MIN:
                c_rf = RF_BW_HZ * np.log2(1.0 + 10.0 ** (s_ij / 10.0)) / 1e6
                best_rf[i] = max(best_rf[i], c_rf)
                best_rf[j] = max(best_rf[j], c_rf)

    return sinr_cell, sinr_rf, c_cell + best_rf


def frame_summary(
    sinr_cell: np.ndarray,
    sinr_rf: np.ndarray,
    throughput: np.ndarray,
) -> dict:
    """Aggregate stats for a single frame — used by both routers."""
    return {
        "active_cellular": int(np.sum(sinr_cell >= CELL_SINR_MIN)),
        "active_rf_links": int(np.sum(sinr_rf   >= RF_SINR_MIN) // 2),
        "avg_throughput_mbps": round(float(np.mean(throughput)), 3),
    }
