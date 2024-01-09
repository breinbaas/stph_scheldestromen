from pydantic import BaseModel
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.pyplot import Figure
import matplotlib.patches as patches
from shapely.geometry import Polygon, MultiPolygon, LineString
from shapely import is_ccw
from geolib.models.dgeoflow import DGeoFlowModel
from geolib.soils.soil import Soil, StorageParameters
from geolib.geometry.one import Point
from geolib.soils.soil_utils import Color
from geolib.models.dgeoflow.internal import (
    PipeTrajectory,
    ErosionDirectionEnum,
    PersistablePoint,
)
from geolib.models.dgeoflow.internal import CalculationTypeEnum
from copy import deepcopy
from enum import IntEnum
from typing import Tuple, List, Optional, Union
from pathlib import Path

from objects.soillayer import SoilLayer

from objects.crosssection import Crosssection, CrosssectionPoint, CrosssectionPointType
from objects.soilprofile import SoilProfile
from settings import (
    PROFIEL_IDS,
    DICT_POINT_IDS,
    LIMIT_LEFT,
    LIMIT_RIGHT,
    SOILPARAMETERS,
    DITCH_BOUNDARY_OFFSET,
    DEFAULT_D70,
    MIN_MESH_SIZE,
    SOILS_WITH_K_ZAND,
    RIGHT_SIDE_BOUNDARY_OFFSET,
    PIPE_MESH_SIZE,
    SLOOT_1A_OFFSET,
)
from helpers import get_name_from_point_type, get_soil_parameters, calc_regression


class SoilPolygon:
    def __init__(self, points: List[Tuple[float, float]], soillayer: SoilLayer):
        self.polygon = Polygon(points)
        self.soillayer = soillayer


class BoundaryMode(IntEnum):
    """This enum is used to select the prefered boundary conditions

    PLTOP
    1. the riverlevel is placed on the left side of the geometry, head=sth_intredepunt
    2. the polder level is placed at the line at sloot_1c and sloot_1d at the top of the aquifer, head=gehanteerd polderpeil incl 0.3 regel voor opbarsten
    3. the phreatic level is placed at sloot1c.x + an offset (DITCH_BOUNDARY_OFFSET in the settings) at the surface, head=sloot_1a.z


    PLTOP_AND_RIGHT
    this is equal to PLTOP but the right side of the geometry is also set as a boundary with head=sloot_1a.z

    PLRIGHT
    this will only put the right side of the geometry on a level based on an offset of the left boundary
    """

    PLTOP = 0
    PLTOP_AND_RIGHT = 1
    PLRIGHT = 2


BOUNDARY_MODE_NAMES = {
    BoundaryMode.PLTOP: "pltop",
    BoundaryMode.PLTOP_AND_RIGHT: "pltopandright",
    BoundaryMode.PLRIGHT: "plright",
}


class PolderLevelMode(IntEnum):
    """This enum is used to select the location of the boundary for the polder level

    DITCH_BOTTOM
    the boundary is put on the ditch bottom

    FIRST_LAYER_BOTTOM
    the boundary is put on the bottom of the first layer
    (since we use a flat geometry this is the bottom of the layer below the ditch bottom)
    """

    DITCH_BOTTOM = 0
    FIRST_LAYER_BOTTOM = 1


POLDERLEVEL_MODE_NAMES = {
    PolderLevelMode.DITCH_BOTTOM: "ditch_bottom",
    PolderLevelMode.FIRST_LAYER_BOTTOM: "layer_bottom",
}


class Scenario(BaseModel):
    name: str
    crosssection: Crosssection
    soilprofile: SoilProfile
    slootnummer: str
    max_zp_wp: float
    gehanteerd_polderpeil: float
    bovengrens_slootpeil: float
    ondergrens_slootpeil: float
    slootpeil: float
    waterstand_bij_norm: float

    x_intredepunt: float = 0.0
    x_uittredepunt: float = 0.0
    sth_intredepunt: float = 0.0
    sth_uittredepunt: float = 0.0

    @classmethod
    def from_dataframe_row(
        cls,
        name,
        row: pd.Series,
        soilprofile: SoilProfile,
    ) -> "Scenario":
        # NOTE because of the black formatting error we need to use PROFIEL_IDS[0]
        pointtypes = [DICT_POINT_IDS[id] for id in PROFIEL_IDS[0]]
        xpoints = [row[f"x{id.lower()}"] for id in PROFIEL_IDS[0]]
        ypoints = [row[f"y{id.lower()}"] for id in PROFIEL_IDS[0]]

        dppoints = []
        for i in range(len(xpoints)):
            dppoints.append(
                CrosssectionPoint(x=xpoints[i], z=ypoints[i], point_type=pointtypes[i])
            )

        crosssection = Crosssection.from_points(points=dppoints)
        crosssection.mirror()

        x_in = -1.0 * float(
            row["intredepunt_for"]
        )  # gespiegelde geometrie dus interedepunt * -1
        crosssection.limit_left(x_in)
        crosssection.limit_right(LIMIT_RIGHT)

        # the soilprofile also needs to know the aquifer number so assign it here
        soilprofile.aquifer_number = row["aquifer"]

        result = Scenario(
            name=name,
            crosssection=crosssection,
            soilprofile=soilprofile,
            slootnummer=str(row["slootnummer"]),
            max_zp_wp=float(row["max_zp_wp_mnap"]),
            gehanteerd_polderpeil=float(row["gehanteerd_polderpeil_mnap"]),
            bovengrens_slootpeil=float(row["bovengrens_slootpeil_mnap"]),
            ondergrens_slootpeil=float(row["ondergrens_slootpeil_mnap"]),
            slootpeil=float(row["slootpeil_mnap"]),
            waterstand_bij_norm=float(row["waterstand_bij_norm_mnap"]),
            x_intredepunt=-1 * float(row["intredepunt_for"]),
            x_uittredepunt=-1 * float(row["uittredepunt_for"]),
            sth_intredepunt=float(row["stijghoogte_intredepunt_mnap"]),
            sth_uittredepunt=float(row["stijghoogte_uittredepunt_mnap"]),
        )

        return result

    @property
    def dijkpaal(self) -> int:
        return int(self.name[1:].split("_")[0]) / 100

    def to_dgeoflow_model(
        self,
        k_sand: float,
        anisotropy_factor: float,
        sealevel_rise: float = 0.0,
        use_surface_boundary: bool = True,
    ) -> Union[List[str], DGeoFlowModel]:
        log = []

        # INPUT CHECK
        # We need points SLOOT_1B, SLOOT_1C and SLOOT_1D for our definitions
        # of some boundaries and the pipe start and we need these points
        # to be different

        ditch_bottom_left = self.crosssection.get_point_by_point_type(
            CrosssectionPointType.SLOOT_1D
        )
        ditch_bottom_right = self.crosssection.get_point_by_point_type(
            CrosssectionPointType.SLOOT_1C
        )
        ditch_top_right = self.crosssection.get_point_by_point_type(
            CrosssectionPointType.SLOOT_1A
        )
        ditch_top_left = self.crosssection.get_point_by_point_type(
            CrosssectionPointType.SLOOT_1B
        )

        if (
            ditch_bottom_left.x >= ditch_bottom_right.x
            or ditch_bottom_right.x >= ditch_top_right.x
        ):
            log.append(
                f"Invalid ditch coordinates, either the left side of the bottom of the ditch ({ditch_bottom_left.x:.2f}) is equal to or greater than the right side of the bottom of the ditch ({ditch_bottom_right.x:.2f}) or the latter is equal to or greater than the right side of the top of the ditch ({ditch_top_right.x:.2f})"
            )
            return log, None

        m = DGeoFlowModel()
        # VOEG GRONDSOORTEN TOE
        for code, params in SOILPARAMETERS.items():
            if code in SOILS_WITH_K_ZAND:  # override these soil properties with k_sand
                k_hor = k_sand
                k_ver = k_sand / anisotropy_factor
            else:
                k_hor = params["k_hor"]
                k_ver = params["k_ver"] / anisotropy_factor

            m.add_soil(
                Soil(
                    name=code,
                    code=code,
                    storage_parameters=StorageParameters(
                        vertical_permeability=k_ver,
                        horizontal_permeability=k_hor,
                    ),
                    color=Color(params["color"].replace("#", "")),
                )
            )
            log.append(f"Adding soil '{code}', k_ver={k_ver}, k_hor={k_hor}")

        # LINKER LIMIET VAN HET MODEL
        left_limit = self.x_intredepunt

        # RECHTER LIMIET VAN HET MODEL
        sloot_1a = self.crosssection.get_point_by_point_type(
            CrosssectionPointType.SLOOT_1A
        )
        if sloot_1a is None:
            raise ValueError(
                f"Geen punt gevonden voor bovenzijde sloot aan de polderzijde. Deze is nodig om de rechtergrens van de geometrie te bepalen."
            )

        right_limit = sloot_1a.x + SLOOT_1A_OFFSET

        # BEPERK HET DWARSPROFIEL TOT DEZE LIMIETEN
        self.crosssection.limit_left(left_limit)
        self.crosssection.limit_right(right_limit)

        # CREEER DE GRONDLAGEN
        # add all soilayers
        soil_polygons = []
        for layer in self.soilprofile.soillayers:
            points = (
                (left_limit, layer.top),
                (right_limit, layer.top),
                (right_limit, layer.bottom),
                (left_limit, layer.bottom),
            )
            soil_polygons.append(SoilPolygon(points, layer))

        # create the polygon of the crosssection
        points = [(p.x, p.z) for p in self.crosssection.points] + [
            (right_limit, self.soilprofile.bottom),
            (left_limit, self.soilprofile.bottom),
        ]
        crs_polygon = Polygon(points)

        # subtract the crosssection polygon from the other layers
        # we also need to keep track of the point for the start of the pipe
        pipe_start = None

        for spg in soil_polygons:
            newpgs = spg.polygon.intersection(crs_polygon)

            if not type(newpgs) in [Polygon, MultiPolygon]:
                raise ValueError(
                    f"Unexpected polygon shape '{type(newpgs)}' during the creation of the geometry."
                )

            if type(newpgs) == Polygon:
                geoms = [newpgs]
            else:
                geoms = newpgs.geoms

            for geom in geoms:
                if geom.is_empty:
                    if is_ccw(geom):
                        geom = geom.reverse()
                points = [Point(x=p[0], z=p[1]) for p in geom.boundary.coords][:-1]

                # if we are dealing with the aquifer we need to add a point at x=ditch_bottom_left and z=top layer

                # TODO
                # maak de breedte max 1m (en bij voorkeur, voeg nog wat extra punten toe om het in stapjes
                # van een meter te verbreden)
                if spg.soillayer == self.soilprofile.aquifer:
                    # two scenarios
                    # scenario 1: the top of the aquifer is on or above the ditch bottom
                    if spg.soillayer.top > ditch_bottom_left.z:
                        pipe_start = sorted(points, key=lambda p: p.x)[-1]
                        topline = LineString(
                            [
                                (left_limit, spg.soillayer.top),
                                (right_limit, spg.soillayer.top),
                            ]
                        )
                        ditchline = LineString(
                            [
                                (ditch_top_left.x, ditch_top_left.z),
                                (ditch_bottom_left.x, ditch_bottom_left.z),
                            ]
                        )
                        try:
                            intersections = topline.intersection(ditchline)
                            pipe_start = Point(x=intersections.x, z=intersections.y)
                        except Exception as e:
                            log.append(
                                "Error trying to find an intersection between the top of the aquifer and the left slope of the ditch, check the input!"
                            )
                            return log, None
                    else:
                        # scenario 2: the top of the aquifer is below the ditch bottom:
                        for i in range(len(points) + 1):
                            p1 = points[i]

                            if i == len(points) - 1:
                                p2 = points[0]
                            else:
                                p2 = points[i + 1]

                            # we could already have the point available if it is on one of the points on the layer
                            if (
                                p1.x == ditch_bottom_left.x
                                or p2.x == ditch_bottom_left.x
                            ):
                                break  # the point is already defined

                            # if not we need to make sure we are dealing with the top of the layer
                            # since we are going cw we should just check if the points x coords are increasing
                            # if so we can check if our point is in between these points
                            if (
                                p1.x < p2.x
                                and p1.x < ditch_bottom_left.x
                                and ditch_bottom_left.x < p2.x
                            ):
                                z = p1.z + (ditch_bottom_left.x - p1.x) * (
                                    p2.z - p1.z
                                ) / (p2.x - p1.x)
                                pipe_start = Point(x=ditch_bottom_left.x, z=z)
                                points.insert(i + 1, pipe_start)
                                break

                m.add_layer(
                    points=points,
                    soil_code=spg.soillayer.short_name,
                    label=spg.soillayer.soil_name,
                )

        # STIJGHOOGTE INTREDEPUNT
        sth_intredepunt = self.sth_intredepunt + sealevel_rise
        points_phi_ws = [
            Point(x=self.crosssection.left, z=z)
            for z in self.soilprofile.get_sth_intredepunt_zs()
        ]

        m.add_boundary_condition(
            points=points_phi_ws,
            head_level=sth_intredepunt,
            label="phi_ws",
        )

        # STIJGHOOGTE RECHTER RAND GEOMETRIE
        sth_uittredepunt = self.sth_uittredepunt
        dx = self.x_uittredepunt - self.x_intredepunt
        sth_right_boundary = calc_regression(
            [0.1, dx],
            [sth_intredepunt, sth_uittredepunt],
            self.crosssection.right - self.x_intredepunt,
        )[1]

        points_phi_hinter = [
            Point(x=self.crosssection.right, z=z)
            for z in self.soilprofile.get_sth_intredepunt_zs()[::-1]
        ]

        m.add_boundary_condition(
            points=points_phi_hinter,
            head_level=sth_right_boundary,
            label="phi_hinter",
        )

        # STIJGHOOGTE SLOOTBODEM
        # check if we need to use the 0.3d rule
        # polderpeil + 0.3 * (slootbodem - bovenzijde piping laag)
        # we willen geen negatieve waarden
        d_03 = max(ditch_bottom_left.z - self.soilprofile.aquifer.top, 0.0)

        # head level according to 0.3d rule
        phi_level_03d = self.gehanteerd_polderpeil + 0.3 * d_03

        if d_03 > 0:
            msg_03d = "(0.3d rule applied) "
            phi_polder = phi_level_03d
            log.append(
                f"0.3d regel toegepast voor het potentiaal op de slootbodem {self.gehanteerd_polderpeil:.2f}+0.3*({ditch_bottom_left.z:.2f}-{self.soilprofile.aquifer.top:.2f})={phi_level_03d:.2f}"
            )
        else:
            phi_polder = self.gehanteerd_polderpeil
            log.append(
                f"WARNING Geen 0.3d regel toegepast, head level gelijk gesteld aan gehanteerd polderpeil, dit is nog niet correct!"
            )

        # add the polder level boundary
        m.add_boundary_condition(
            points=[ditch_bottom_left, ditch_bottom_right],
            head_level=phi_polder,
            label="polder",
        )

        if use_surface_boundary:
            m.add_boundary_condition(
                points=[
                    Point(x=ditch_top_right.x, z=ditch_top_right.z),
                    Point(x=right_limit, z=ditch_top_right.z),
                ],  # NOTE this will lead to errors if the surface is not flat but here we know the surface is flat
                head_level=ditch_top_right.z,
                label="water surface",
            )

        # add the pipe
        m.set_calculation_type(calculation_type=CalculationTypeEnum.PIPE_LENGTH)
        m.set_pipe_trajectory(
            pipe_trajectory=PipeTrajectory(
                Label="Pipe",
                D70=DEFAULT_D70 / 1000,  # um to mm
                ErosionDirection=ErosionDirectionEnum.RIGHT_TO_LEFT,
                ElementSize=PIPE_MESH_SIZE,
                Points=[
                    PersistablePoint(X=pipe_start.x, Z=self.soilprofile.aquifer.top),
                    PersistablePoint(X=left_limit, Z=self.soilprofile.aquifer.top),
                ],
            )
        )

        return log, m

    def plot(
        self,
        right_limit: float,
        k_zand: float,
        anisotropy_factor: float,
        filename: str = "",
        width: float = 20.0,
        height: float = 12.0,
        error_message: str = "",
    ):
        """Generate a plot of the model

        If filename is "" then the figure will be returned else the plot will
        be save to the given filename

        Args:
            right_limit (float): the rightmost x coordinate of the geometry
            filename (str, optional): The name of the file. Defaults to "". If not set this function will return the figure
            width (float, optional): width of the plot. Defaults to 20.0.
            height (float, optional): height of the plot. Defaults to 12.0.
        """
        fig = Figure(figsize=(width, height))
        ax = fig.add_subplot()

        width = right_limit - self.crosssection.left

        # grondlagen
        for sl in self.soilprofile.soillayers:
            # we want to show the k values
            soilparams = get_soil_parameters(sl.short_name)

            if (
                sl.short_name in SOILS_WITH_K_ZAND
            ):  # override these soil properties with k_zand
                k_hor = k_zand
                k_ver = k_zand / anisotropy_factor
            else:
                k_hor = soilparams["k_hor"]
                k_ver = soilparams["k_ver"] / anisotropy_factor

            # aquifer krijgt hatching
            if sl == self.soilprofile.aquifer:
                ax.add_patch(
                    patches.Rectangle(
                        (self.crosssection.left, sl.bottom),
                        width,
                        sl.height,
                        facecolor=sl.color,
                        # hatch="///",
                        edgecolor="black",
                        hatch="//",
                    )
                )
                ax.text(
                    self.crosssection.left,
                    sl.bottom + 0.1,
                    f"AQ: {sl.soil_name} (k;hor={k_hor:.3f}, k;ver={k_ver:.3f})",
                )
            else:
                ax.add_patch(
                    patches.Rectangle(
                        (self.crosssection.left, sl.bottom),
                        width,
                        sl.height,
                        color=sl.color,
                    )
                )
                ax.text(
                    self.crosssection.left,
                    sl.bottom + 0.1,
                    f"{sl.soil_name} (k;hor={k_hor:.3f}, k;ver={k_ver:.3f})",
                )

        # dwarsprofiel
        ax.plot(
            [p.x for p in self.crosssection.points],
            [p.z for p in self.crosssection.points],
            "k",
        )

        # karakteristieke punten
        for point in self.crosssection.points:
            ax.plot([point.x, point.x], [point.z, self.crosssection.top + 2.0], "k--")
            ax.text(
                point.x,
                self.crosssection.top + 3.0,
                get_name_from_point_type(point.point_type),
                rotation=90,
            )

        if error_message != "":
            ax.text(
                self.crosssection.left + 2.0, self.crosssection.top + 8.0, error_message
            )

        ax.set_ylim(self.soilprofile.bottom, self.crosssection.top + 10.0)

        if filename == "":  # return the figure so more stuff can be added
            return fig, ax

        fig.savefig(filename)
