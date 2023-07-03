import copy
import numpy
from typing import Final, Union

from I3Tray import I3Units  # type: ignore[import]
from icecube import dataclasses  # type: ignore[import]


def mask_deepcore(frame, origpulses: str, maskedpulses: str):
    """Masks DeepCore pulses by selecting string numbers."""
    FIRST_DEEPCORE_STRING: Final[int] = 79
    frame[maskedpulses] = dataclasses.I3RecoPulseSeriesMapMask(
        frame,
        origpulses,
        lambda omkey, index, pulse: omkey.string < FIRST_DEEPCORE_STRING,
    )


def _weighted_quantile_arg(values, weights, q=0.5):
    indices = numpy.argsort(values)
    sorted_indices = numpy.arange(len(values))[indices]
    medianidx = (weights[indices].cumsum() / weights[indices].sum()).searchsorted(q)
    if (0 <= medianidx) and (medianidx < len(values)):
        return sorted_indices[medianidx]
    else:
        return numpy.nan


def weighted_quantile(values, weights, q=0.5):
    if len(values) != len(weights):
        raise ValueError("shape of `values` and `weights` don't match!")
    index = _weighted_quantile_arg(values, weights, q=q)
    if not numpy.isnan(index):
        return values[index]
    else:
        return numpy.nan


def weighted_median(values, weights):
    return weighted_quantile(values, weights, q=0.5)


def late_pulse_cleaning(
    frame,
    input_pulses_name,  # : str,
    output_pulses_name,  #:  str,
    orig_pulses_name,  #: Union[str, None] = None,
    Residual=3e3 * I3Units.ns,
):
    # input_pulses_name can specify a masked hit series that does not carry the TimeRange key
    # in such case, the TimeRange key will be retrieved from orig_pulses_name
    if orig_pulses_name is None:
        orig_pulses_name = input_pulses_name

    pulses = dataclasses.I3RecoPulseSeriesMap.from_frame(frame, input_pulses_name)
    mask = dataclasses.I3RecoPulseSeriesMapMask(frame, input_pulses_name)
    counter, charge = 0, 0
    qtot = 0
    times = dataclasses.I3TimeWindowSeriesMap()
    for omkey, ps in pulses.items():
        if len(ps) < 2:
            if len(ps) == 1:
                qtot += ps[0].charge
            continue
        ts = numpy.asarray([p.time for p in ps])
        cs = numpy.asarray([p.charge for p in ps])
        median = weighted_median(ts, cs)
        qtot += cs.sum()
        for p in ps:
            if p.time >= (median + Residual):
                if omkey not in times:
                    ts = dataclasses.I3TimeWindowSeries()
                    ts.append(
                        dataclasses.I3TimeWindow(median + Residual, numpy.inf)
                    )  # this defines the **excluded** time window
                    times[omkey] = ts
                mask.set(omkey, p, False)
                counter += 1
                charge += p.charge
    frame[output_pulses_name] = mask
    frame[output_pulses_name + "TimeWindows"] = times

    frame[output_pulses_name + "TimeRange"] = copy.deepcopy(
        frame[orig_pulses_name + "TimeRange"]
    )


def LatePulseCleaning(
    frame,
    input_pulses_name,
    output_pulses_name,
    orig_pulses_name,
    Residual=1.5e3 * I3Units.ns,
):
    pulses = dataclasses.I3RecoPulseSeriesMap.from_frame(frame, input_pulses_name)
    mask = dataclasses.I3RecoPulseSeriesMapMask(frame, input_pulses_name)
    counter, charge = 0, 0
    qtot = 0
    times = dataclasses.I3TimeWindowSeriesMap()
    for omkey, ps in pulses.items():
        if len(ps) < 2:
            if len(ps) == 1:
                qtot += ps[0].charge
            continue
        ts = numpy.asarray([p.time for p in ps])
        cs = numpy.asarray([p.charge for p in ps])
        median = weighted_median(ts, cs)
        qtot += cs.sum()
        for p in ps:
            if p.time >= (median + Residual):
                if omkey not in times:
                    ts = dataclasses.I3TimeWindowSeries()
                    ts.append(
                        dataclasses.I3TimeWindow(median + Residual, numpy.inf)
                    )  # this defines the **excluded** time window
                    times[omkey] = ts
                mask.set(omkey, p, False)
                counter += 1
                charge += p.charge
    frame[output_pulses_name] = mask
    frame[output_pulses_name + "TimeWindows"] = times
    frame[output_pulses_name + "TimeRange"] = copy.deepcopy(
        frame[orig_pulses_name + "TimeRange"]
    )
