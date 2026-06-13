"""Run the Python free-form energy balance with the SAME settings as the MATLAB
driver (manual equilibrium at 319 K, Vmpp = 0.6586 V), and dump the same
comparison files (energyBalanceTerms.txt, scalars.txt) next to the standard
outputs. Prints the output folder path.
"""

import os

import numpy as np

from radcoolpv import config as cm
from radcoolpv import pipeline

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "python_out")


def main():
    cfg = cm.load(os.path.join(HERE, "..", "configs", "freeform.yaml"))
    # Match the MATLAB driver exactly.
    cfg.run.plots = False                 # comparison plots are made separately
    cfg.run.results_dir = OUT
    cfg.thermal.equilibrium = "manual"
    cfg.thermal.emit_temp = 319.0
    cfg.thermal.vmpp = 0.6586

    ctx = pipeline.run(cfg)
    t = ctx.thermal
    d = ctx.results_dir

    # Energy-balance terms vs emitter temperature (same 7 columns as MATLAB).
    atm = np.full_like(t.emit_temp, t.atm_power)
    cols = np.column_stack([t.emit_temp, t.rad_power, atm, t.conv_power,
                            t.cool_power, t.max_power_point, t.non_thermal_power])
    np.savetxt(os.path.join(d, "energyBalanceTerms.txt"), cols, fmt="%g")

    # Scalar results (same keys as MATLAB scalars.txt).
    scalars = {
        "isc_A_m2": t.isc,
        "voc_equil_V": t.voc_equil,
        "voc_amb_V": t.voc_amb,
        "ff_equil": t.ff_equil,
        "ff_amb": t.ff_amb,
        "mpp_equil_W_m2": t.mpp_equil,
        "mpp_amb_W_m2": t.mpp_amb,
        "atm_power_W_m2": t.atm_power,
        "solar_power_abs_W_m2": t.solar_power,
        "solar_power_am15_W_m2": t.solar_power_am15,
        "beta_p_perc_K": t.beta_p,
        "efficiency_equil": t.efficiency_equil,
        "equil_temp_K": t.equil_temp,
        "vmpp_V": t.vmpp,
    }
    with open(os.path.join(d, "scalars.txt"), "w") as fh:
        for k, v in scalars.items():
            fh.write(f"{k} {v:.10g}\n")

    print(f"PYTHON_OUT_DIR={d}")


if __name__ == "__main__":
    main()
