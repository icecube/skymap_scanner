from typing import List, Tuple
from icecube import dataclasses


def get_splinempe_position_variations(
    direction: Tuple[float, float],
    v_ax: List[int] = [-40.0, 40.0],
    r_ax: List[int] = [150.0],
    ang_steps=3,
):
    """[Given a vertex and a direction it returns some vertex seeds to perform a SplineMPE fit
        these vertexes are by default 7, one is the initial one, the othes 6 are chosen along
        a cylinder with characteristics specified by v_ax and r_ax and ang_steps]

    Args:
        vert_mid ([I3Position]): The initial vertex
        direc ([]): The direction in the sky
        v_ax ([list of floats], optional): the list of steps along the direction to do to find
                                            the vertexes
        r_ax ([list of floats], optional): the list of radius of the cylinders used to find the
                                            vertexes
        ang_steps([int], optional): the number of seeds to be taken on each basis of a cylinder

    Returns:
        pos_seeds ([list of I3Position]): the list of vertex seeds
    """

    vert_u = I3Units.m

    theta, phi = direc
    
    # define angular steps
    ang_ax = np.linspace(0, 2.0 * np.pi, ang_steps + 1)[:-1]

    # angular separation between seeds
    dang = (ang_ax[1] - ang_ax[0]) / 2.0

    v_dir, dir1, dir2 = get_orthonormal_basis(theta, phi)

    pos_seeds = [] # empty list, the starting vertix is implicit

    for i, vi in enumerate(v_ax): # step along axis

        v = vi * v_dir 

        for j, r in enumerate(r_ax): # step along radius

            for ang in ang_ax: #  step around anlge

                d1 = r * np.cos(ang + (i + j) * dang) * dir1
                d2 = r * np.sin(ang + (i + j) * dang) * dir2

                x = v[0] + d1[0] + d2[0]
                y = v[1] + d1[1] + d2[1]
                z = v[2] + d1[2] + d2[2]

                pos = dataclasses.I3Position(
                    x * vert_u,
                    y * vert_u,
                    z * vert_u,
                )

                pos_seeds.append(pos)

    return pos_seeds

def get_orthonormal_basis(theta, phi):
        """Given a direction in the sky it returns a 3D orthonormal basis 

        Args:
            theta ([float]): Theta angle
            phi ([float]): Phi angle

        Returns:
            v_dir ([numpy array of floats]): the vector along the direction
            dir1 ([numpy array of floats]): one of the two vectors orthogonal to the direction
            dir2 ([numpy array of floats]): the other vector orthogonal to the direction
        """

        # unit vector along direction defined by theta, phi
        v_dir = np.array([np.cos(phi) * np.sin(theta), np.sin(phi) * np.sin(theta), np.cos(theta)])

        # first orthonormal vector, from theta => theta - pi/2
        dir1 = np.array(
            [
                np.cos(phi) * np.sin(theta - np.pi / 2.0),
                np.sin(phi) * np.sin(theta - np.pi / 2.0),
                np.cos(theta - np.pi / 2.0),
            ]
        )

        # second orthonormal vector
        dir2 = np.cross(v_dir, dir1)

        return v_dir, dir1, dir2