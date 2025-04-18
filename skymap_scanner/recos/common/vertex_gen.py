from typing import Tuple

import numpy as np

from icecube import dataclasses  # type: ignore[import]
from icecube.icetray import I3Units  # type: ignore[import]


class VertexGenerator:
    def __init__(self):
        pass

    @staticmethod
    def point():
        return [dataclasses.I3Position(0.0, 0.0, 0.0)]

    @staticmethod
    def octahedron(radius: float):
        return [
            dataclasses.I3Position(0.0, 0.0, 0.0),
            dataclasses.I3Position(-radius, 0.0, 0.0),
            dataclasses.I3Position(radius, 0.0, 0.0),
            dataclasses.I3Position(0.0, -radius, 0.0),
            dataclasses.I3Position(0.0, radius, 0.0),
            dataclasses.I3Position(0.0, 0.0, -radius),
            dataclasses.I3Position(0.0, 0.0, radius),
        ]

    @staticmethod
    def cylinder(
        v_ax: Tuple[float, float] = (-40.0, 40.0),
        r_ax: Tuple[float] = (150.0,),
        ang_steps=3,
    ):
        vert_u = I3Units.m

        # define angular steps
        ang_ax = np.linspace(0, 2.0 * np.pi, ang_steps + 1)[:-1]

        # angular separation between seeds
        dang = (ang_ax[1] - ang_ax[0]) / 2.0

        pos_seeds = [dataclasses.I3Position(0.0, 0.0, 0.0)]

        for i, vi in enumerate(v_ax):  # step along axis
            for j, r in enumerate(r_ax):  # step along radius
                for ang in ang_ax:  # step around anlge
                    x = r * np.cos(ang + (i + j) * dang)
                    y = r * np.sin(ang + (i + j) * dang)
                    z = vi

                    pos = dataclasses.I3Position(
                        x * vert_u,
                        y * vert_u,
                        z * vert_u,
                    )

                    pos_seeds.append(pos)

        return pos_seeds

    @staticmethod
    def mini_test(variation_distance):
        """Simple two-variations config for testing purposes.
        It does not have a physical motivation.
        """
        return [
            dataclasses.I3Position(0.0, 0.0, 0.0),
            dataclasses.I3Position(-variation_distance, 0.0, 0.0),
        ]
