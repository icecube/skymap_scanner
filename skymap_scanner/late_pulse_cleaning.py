import numpy as np

from I3Tray import I3Units
from icecube import dataclasses

from copy import deepcopy

# code extracted from python/prepare_frames.py

def _weighted_quantile_arg(values, weights, q=0.5):
    indices = np.argsort(values)
    sorted_indices = np.arange(len(values))[indices]
    medianidx = (weights[indices].cumsum() / weights[indices].sum()).searchsorted(q)
    if (0 <= medianidx) and (medianidx < len(values)):
        return sorted_indices[medianidx]
    else:
        return np.nan


def weighted_quantile(values, weights, q=0.5):
    if len(values) != len(weights):
        raise ValueError("shape of `values` and `weights` don't match!")
    index = _weighted_quantile_arg(values, weights, q=q)
    if not np.isnan(index):
        return values[index]
    else:
        return np.nan


def weighted_median(values, weights):
    return weighted_quantile(values, weights, q=0.5)


def LatePulseCleaning(frame, Pulses, Residual=3e3 * I3Units.ns):
    pulses = dataclasses.I3RecoPulseSeriesMap.from_frame(frame, Pulses)
    mask = dataclasses.I3RecoPulseSeriesMapMask(frame, Pulses)
    counter, charge = 0, 0
    qtot = 0
    times = dataclasses.I3TimeWindowSeriesMap()
    for omkey, ps in pulses.items():
        if len(ps) < 2:
            if len(ps) == 1:
                qtot += ps[0].charge
            continue
        ts = np.asarray([p.time for p in ps])
        cs = np.asarray([p.charge for p in ps])
        median = weighted_median(ts, cs)
        qtot += cs.sum()
        for p in ps:
            if p.time >= (median + Residual):
                if omkey not in times:
                    ts = dataclasses.I3TimeWindowSeries()
                    ts.append(
                        dataclasses.I3TimeWindow(median + Residual, np.inf)
                    )  # this defines the **excluded** time window
                    times[omkey] = ts
                mask.set(omkey, p, False)
                counter += 1
                charge += p.charge
    frame[Pulses + "LatePulseCleaned"] = mask
    frame[Pulses + "LatePulseCleanedTimeWindows"] = times
    frame[Pulses + "LatePulseCleanedTimeRange"] = deepcopy(
        frame[Pulses + "TimeRange"]
    )  # this is not strictly true?
