from __future__ import division
import numpy as np

def inclusive_range(start, stop=None, step=None):
    if stop is None:
        stop = start
    if stop == start:
        return np.array([start])
    if step is None:
        step = stop - start
    return np.arange(start, stop + step/2, step)
