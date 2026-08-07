import json, numpy as np
from alpha_archive.replications.decomp2026_eval import build, full_set_table, switching, with_momentum, COPULAS
from alpha_archive.replications.decomp2026_paper import load, WINDOW

paths = {}
# k=3 and k=8 carry every wealth path the figures plot; Appendix C rides on k=8.
build(ks=(3, 8), verbose=True, paths=paths)
np.savez_compressed("data/wealth_paths_2606.04153.npz",
                    **{k: np.asarray(v, dtype=np.float64) for k, v in paths.items()})
print(f"{len(paths)} wealth paths saved")
