"""
Based on `cloud_tools/perform_scan.py`
"""

import numpy
from icecube import dataclasses
from icecube import VHESelfVeto
from I3Tray import I3Units


def get_reco_losses_inside(p_frame):
    if "MillipedeStarting2ndPass" not in p_frame:
        p_frame[
            "MillipedeStarting2ndPass_totalRecoLossesInside"
        ] = dataclasses.I3Double(numpy.nan)
        p_frame["MillipedeStarting2ndPass_totalRecoLossesTotal"] = dataclasses.I3Double(
            numpy.nan
        )
        return
    recoParticle = p_frame["MillipedeStarting2ndPass"]

    if "MillipedeStarting2ndPassParams" not in p_frame:
        p_frame[
            "MillipedeStarting2ndPass_totalRecoLossesInside"
        ] = dataclasses.I3Double(numpy.nan)
        p_frame["MillipedeStarting2ndPass_totalRecoLossesTotal"] = dataclasses.I3Double(
            numpy.nan
        )
        return

    def getRecoLosses(vecParticles):
        losses = []
        for p in vecParticles:
            if not p.is_cascade:
                continue
            if p.energy == 0.0:
                continue
            losses.append([p.time, p.energy])
        return losses

    recoLosses = getRecoLosses(p_frame["MillipedeStarting2ndPassParams"])

    intersectionPoints = VHESelfVeto.IntersectionsWithInstrumentedVolume(
        p_frame["I3Geometry"], recoParticle
    )
    intersectionTimes = []
    for intersectionPoint in intersectionPoints:
        vecX = intersectionPoint.x - recoParticle.pos.x
        vecY = intersectionPoint.y - recoParticle.pos.y
        vecZ = intersectionPoint.z - recoParticle.pos.z

        prod = (
            vecX * recoParticle.dir.x
            + vecY * recoParticle.dir.y
            + vecZ * recoParticle.dir.z
        )
        dist = numpy.sqrt(vecX**2 + vecY**2 + vecZ**2)
        if prod < 0.0:
            dist *= -1.0
        intersectionTimes.append(dist / dataclasses.I3Constants.c + recoParticle.time)

    entryTime = None
    exitTime = None
    intersectionTimes = sorted(intersectionTimes)
    if len(intersectionTimes) == 0:
        p_frame[
            "MillipedeStarting2ndPass_totalRecoLossesInside"
        ] = dataclasses.I3Double(0.0)

        totalRecoLosses = 0.0
        for entry in recoLosses:
            totalRecoLosses += entry[1]
        p_frame["MillipedeStarting2ndPass_totalRecoLossesTotal"] = dataclasses.I3Double(
            totalRecoLosses
        )
        return

    entryTime = intersectionTimes[0] - 60.0 * I3Units.m / dataclasses.I3Constants.c
    intersectionTimes = intersectionTimes[1:]
    exitTime = intersectionTimes[-1] + 60.0 * I3Units.m / dataclasses.I3Constants.c
    intersectionTimes = intersectionTimes[:-1]

    totalRecoLosses = 0.0
    totalRecoLossesInside = 0.0
    for entry in recoLosses:
        totalRecoLosses += entry[1]
        if entryTime is not None and entry[0] < entryTime:
            continue
        if exitTime is not None and entry[0] > exitTime:
            continue
        totalRecoLossesInside += entry[1]

    p_frame["MillipedeStarting2ndPass_totalRecoLossesInside"] = dataclasses.I3Double(
        totalRecoLossesInside
    )
    p_frame["MillipedeStarting2ndPass_totalRecoLossesTotal"] = dataclasses.I3Double(
        totalRecoLosses
    )
