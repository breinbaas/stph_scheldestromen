from pydantic import BaseModel
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.pyplot import Figure
import matplotlib.patches as patches
from shapely.geometry import Polygon, MultiPolygon
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
    ANISOTROPY_FACTOR,
    RIGHT_SIDE_BOUNDARY_OFFSET,
)
from helpers import get_name_from_point_type, get_soil_parameters


class BoundaryMode(IntEnum):
    """This enum is used to select the prefered boundary conditions

    PLTOP
    1. the riverlevel is placed on the left side of the geometry, head=waterstand_bij_norm
    2. the polder level is placed at the line at sloot_1c and sloot_1d at the top of the aquifer, head=max_zp_wp
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
    bovengrens_slootpeil: float
    ondergrens_slootpeil: float
    slootpeil: float
    waterstand_bij_norm: float
    boundary_mode: BoundaryMode = BoundaryMode.PLTOP
    polderlevel_mode: PolderLevelMode = PolderLevelMode.DITCH_BOTTOM
    logfile: str = ""  # if set then this will be used to store the log information

    @classmethod
    def from_dataframe_row(
        cls,
        name,
        row: pd.Series,
        soilprofile: SoilProfile,
        boundary_mode: BoundaryMode = BoundaryMode.PLTOP,
        polderlevel_mode: PolderLevelMode = PolderLevelMode.DITCH_BOTTOM,
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
        crosssection.limit_left(LIMIT_LEFT)
        crosssection.limit_right(LIMIT_RIGHT)

        result = Scenario(
            name=name,
            crosssection=crosssection,
            boundary_mode=boundary_mode,
            polderlevel_mode=polderlevel_mode,
            # intredepunt=float(row["xintredepunt"]),
            # uittredepunt=float(row["uittredepunt"]),
            soilprofile=soilprofile,
            slootnummer=str(row["slootnummer"]),
            max_zp_wp=float(row["max_zp_wp_mnap"]),
            bovengrens_slootpeil=float(row["bovengrens_slootpeil_mnap"]),
            ondergrens_slootpeil=float(row["ondergrens_slootpeil_mnap"]),
            slootpeil=float(row["slootpeil_mnap"]),
            waterstand_bij_norm=float(row["waterstand_bij_norm_mnap"]),
        )

        return result

    @property
    def dijkpaal(self) -> int:
        return int(self.name[1:].split("_")[0]) / 100

    def to_flat_dgeoflow_model(
        self, sloot_1a_offset: float, k_zand: float, plot_file: str = ""
    ) -> DGeoFlowModel:
        """Convert the scenario to a DGeoFlow model where we limit the top of the geometry at the uittredepunt

        If plot_file is not "" this will also create a plot on the given location / name for debugging purposes

        Returns:
            DGeoFlowModel: The DGeoFlow model
        """
        m = DGeoFlowModel()

        log = []
        log.append(f"Handling scenario '{self.name}'")
        log.append("-" * 80)
        log.append("Input parameters:")
        log.append("-" * 80)
        log.append(f"Waterstand bij norm: {self.waterstand_bij_norm}")
        log.append(f"Polderpeil: {self.max_zp_wp}")
        log.append(f"Gekozen boundary mode: {BOUNDARY_MODE_NAMES[self.boundary_mode]}")
        log.append(
            f"Gekozen polderpeil mode: {POLDERLEVEL_MODE_NAMES[self.polderlevel_mode]}"
        )
        log.append(
            f"Geometrie afkappen op / doortrekken tot {sloot_1a_offset}m van het sloot_1a punt"
        )
        log.append("-" * 80)
        log.append("Grondlagen:")
        log.append("-" * 80)
        for sl in self.soilprofile.soillayers:
            if sl.aquifer_number == sl.is_aquifer:
                log.append(
                    f"van {sl.top:.2f} tot {sl.bottom:.2f} grondsoort '{sl.soil_name}' AQUIFER"
                )
            else:
                log.append(
                    f"van {sl.top:.2f} tot {sl.bottom:.2f} grondsoort '{sl.soil_name}'"
                )
        log.append("-" * 80)

        # write soiltypes
        log.append("Grondsoorten:")
        log.append("-" * 80)
        for code, params in SOILPARAMETERS.items():
            if code in SOILS_WITH_K_ZAND:  # override these soil properties with k_zand
                k_hor = k_zand
                k_ver = k_zand / ANISOTROPY_FACTOR
            else:
                k_hor = params["k_hor"] / ANISOTROPY_FACTOR
                k_ver = params["k_ver"]

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
        log.append("-" * 80)

        # we need sloot 1d and 1c to define our polder level boundary
        sloot_1d = self.crosssection.get_point_by_point_type(
            CrosssectionPointType.SLOOT_1D
        )
        sloot_1c = self.crosssection.get_point_by_point_type(
            CrosssectionPointType.SLOOT_1C
        )

        # we need sloot 1a to define the height of the phreatic level boundary
        # and the start of the phreatic level boundary
        sloot_1a = self.crosssection.get_point_by_point_type(
            CrosssectionPointType.SLOOT_1A
        )
        if sloot_1d is None or sloot_1c is None or sloot_1a is None:
            raise ValueError(
                f"No ditch found, cannot set the polder level and start phreatic boundary."
            )

        # it is also possible that all sloot points have the same x coordinate
        # that is the same as not having a ditch
        if sloot_1c.x == sloot_1d.x:
            raise ValueError(
                f"No ditch found, point sloot_1c and sloot_1d share the same x coordinate."
            )
        if sloot_1c.x == sloot_1a.x:
            raise ValueError(
                f"No ditch found, point sloot_1c and sloot_1a share the same x coordinate."
            )

        # cut off the geometry at the given value
        geometry_limit_right = sloot_1a.x + sloot_1a_offset
        # if geometry_limit_right > self.crosssection.right:
        #     raise ValueError(
        #         f"Trying to cut off the geometry at x={geometry_limit_right} which is beyond the right limit {self.crosssection.right}."
        #     )

        if plot_file != "":
            fig, ax = self.plot(right_limit=geometry_limit_right)

        if sloot_1a.x + DITCH_BOUNDARY_OFFSET > geometry_limit_right:
            raise ValueError(
                f"The offset right of the sloot_1a is too large, the boundary exceeds the model limit."
            )

        # we cut our gemeotry off at the z value of insteek (sloot_1d) or point binnen (mv_binnen)
        log.append(f"Afkappen profiel op onderzijde sloot ({sloot_1d.z})")
        self.soilprofile.cut_top_at_z(sloot_1d.z)

        x1 = self.crosssection.left
        x2 = geometry_limit_right
        boundary_added = False
        soillayer_for_pipe_settings = self.soilprofile.get_first_acquifer_below(
            sloot_1d.z
        )
        point_pipe_start = None
        point_pipe_end = Point(x=self.crosssection.left, z=-9999)
        for layer in self.soilprofile.soillayers:
            points = [
                Point(x=p[0], z=p[1])
                for p in zip(
                    [x1, x2, x2, x1],
                    [layer.top, layer.top, layer.bottom, layer.bottom],
                )
            ]  # 0 = topleft, 1 = topright, 2 = bottomright, 3 = bottomleft

            if layer == soillayer_for_pipe_settings:
                # we need to add the points for the pipe settings
                point_pipe_start = Point(x=sloot_1d.x, z=layer.top)
                point_pipe_end.z = layer.top
                points.insert(1, point_pipe_start)

            if not boundary_added:
                # first layer so add the points to enable the selection of the boundaries
                if self.polderlevel_mode == PolderLevelMode.DITCH_BOTTOM:
                    # one at sloot_1d, one at sloot_1c for polder level
                    # and one at sloot_1c + DITCH_BOUNDARY_OFFSET for the phreatic level
                    boundary_pp_start = Point(x=sloot_1d.x, z=layer.top)
                    boundary_pp_end = Point(x=sloot_1c.x, z=layer.top)
                    boundary_pl_start = Point(
                        x=sloot_1a.x + DITCH_BOUNDARY_OFFSET, z=layer.top
                    )
                    # insert those points
                    points = (
                        [points[0]]
                        + [boundary_pp_start, boundary_pp_end, boundary_pl_start]
                        + points[1:]
                    )
                    boundary_added = True
                elif self.polderlevel_mode == PolderLevelMode.FIRST_LAYER_BOTTOM:
                    # one at x = sloot_1d, one at x = sloot_1c at bottom of the first layer
                    # and one at sloot_1c + DITCH_BOUNDARY_OFFSET on surface for the phreatic level
                    boundary_pp_start = Point(x=sloot_1d.x, z=layer.bottom)
                    boundary_pp_end = Point(x=sloot_1c.x, z=layer.bottom)
                    boundary_pl_start = Point(
                        x=sloot_1a.x + DITCH_BOUNDARY_OFFSET, z=layer.top
                    )
                    # insert those points
                    points = (
                        [points[0], boundary_pl_start]
                        + points[1:3]
                        + [boundary_pp_end, boundary_pp_start]
                        + [points[-1]]
                    )
                    boundary_added = True
                else:
                    raise ValueError(
                        f"Scenario with invalid polderlevel mode '{self.polderlevel_mode}'"
                    )
            layer_id = m.add_layer(
                points=points, soil_code=layer.short_name, label=layer.soil_name
            )
            # set the mesh to at least 2m but preferably the half of the height of the layer
            mesh_size = round(min(layer.height / 2.0, MIN_MESH_SIZE), 2)
            m.add_meshproperties(element_size=mesh_size, layer_id=layer_id)
            log.append(f"Mesh size voor laag {layer.short_name}: {mesh_size:.2f}")

        # add the river level boundary
        points_river_level = []
        for z in self.soilprofile.get_soillayer_z_coordinates():
            points_river_level.append(Point(x=self.crosssection.left, z=z))

        m.add_boundary_condition(
            points=points_river_level,
            head_level=self.waterstand_bij_norm,
            label="river level at norm",
        )

        if plot_file != "":
            zs = self.soilprofile.get_soillayer_z_coordinates()
            xs = [self.crosssection.left] * len(zs)
            ax.plot(xs, zs, "b", linewidth=5)
            ax.text(
                xs[0] - 2.0,
                zs[0] + 0.5,
                f"head = {self.waterstand_bij_norm}",
                rotation=90,
                color="b",
            )

        # add the polder level boundary
        m.add_boundary_condition(
            points=[boundary_pp_start, boundary_pp_end],
            head_level=self.max_zp_wp,
            label="polder level",
        )

        if plot_file != "":
            ax.plot(
                [boundary_pp_start.x, boundary_pp_end.x],
                [boundary_pp_start.z, boundary_pp_end.z],
                "b",
                linewidth=5,
            )
            ax.text(
                boundary_pp_start.x,
                boundary_pp_start.z + 0.5,
                f"head = {self.max_zp_wp}",
                rotation=90,
                color="b",
            )

        # add the phreatic level boundary
        if self.boundary_mode == BoundaryMode.PLTOP:
            boundary_pl_points = [boundary_pl_start, Point(x=x2, z=boundary_pl_start.z)]
        elif self.boundary_mode == BoundaryMode.PLTOP_AND_RIGHT:
            boundary_pl_points = [boundary_pl_start, Point(x=x2, z=boundary_pl_start.z)]
            for z in self.soilprofile.get_soillayer_z_coordinates()[::-1]:
                boundary_pl_points.append(Point(x=x2, z=z))
        elif self.boundary_mode == BoundaryMode.PLRIGHT:
            boundary_pl_points = [
                Point(x=x2, z=z)
                for z in self.soilprofile.get_soillayer_z_coordinates()[::-1]
            ]
        else:
            raise ValueError(f"Unhandled boundary mode '{self.boundary_mode}'")

        if self.boundary_mode in [BoundaryMode.PLTOP, BoundaryMode.PLTOP_AND_RIGHT]:
            m.add_boundary_condition(
                points=boundary_pl_points,
                head_level=sloot_1a.z,
                label="phreatic level",
            )
            if self.boundary_mode == BoundaryMode.PLTOP:
                log.append(
                    f"De head voor de pl lijn ligt op het niveau {sloot_1d.z:.2f}m en aan de bovenzijde van de geometrie"
                )
            else:
                log.append(
                    f"De head voor de pl lijn ligt op het niveau {sloot_1d.z:.2f}m en aan de boven- en rechterzijde van de geometrie"
                )
        else:
            m.add_boundary_condition(
                points=boundary_pl_points,
                head_level=self.waterstand_bij_norm - RIGHT_SIDE_BOUNDARY_OFFSET,
                label="phreatic level",
            )
            log.append(
                f"De head voor de pl lijn ligt op {RIGHT_SIDE_BOUNDARY_OFFSET:.1f}m onder de waterstand bij de norm aan de rechterzijde van de geometrie."
            )

        if plot_file != "":
            ax.plot(
                [p.x for p in boundary_pl_points],
                [p.z for p in boundary_pl_points],
                "b",
                linewidth=5,
            )
            if self.boundary_mode in [BoundaryMode.PLTOP, BoundaryMode.PLTOP_AND_RIGHT]:
                ax.text(
                    boundary_pl_start.x,
                    boundary_pl_start.z + 0.5,
                    f"head = {sloot_1a.z}",
                    color="b",
                )
            elif self.boundary_mode == BoundaryMode.PLRIGHT:
                ax.text(
                    x2 + 0.5,
                    zs[0] + 0.5,
                    f"head = {(self.waterstand_bij_norm - RIGHT_SIDE_BOUNDARY_OFFSET):.3f}",
                    rotation=90,
                    color="b",
                )

        # pipe trajectory
        if point_pipe_start is None:
            raise ValueError(
                f"No pipe start found, this should be the first layer under the z coordinate of point sloot_1d."
            )

        log.append(
            f"Startpunt van de pipe ligt op ({point_pipe_start.x:.2f}, {point_pipe_start.z:.2f})"
        )
        log.append(
            f"Eindpunt van de pipe ligt op ({point_pipe_end.x:.2f}, {point_pipe_end.z:.2f})"
        )
        log.append(f"D70 = {DEFAULT_D70}um (={DEFAULT_D70/1000}mm)")

        # set calculation settings
        m.set_calculation_type(calculation_type=CalculationTypeEnum.PIPE_LENGTH)
        m.set_pipe_trajectory(
            pipe_trajectory=PipeTrajectory(
                Label="Pipe",
                D70=DEFAULT_D70 / 1000,  # um to mm
                ErosionDirection=ErosionDirectionEnum.RIGHT_TO_LEFT,
                ElementSize=1.0,
                Points=[
                    PersistablePoint(X=point_pipe_start.x, Z=point_pipe_start.z),
                    PersistablePoint(X=point_pipe_end.x, Z=point_pipe_end.z),
                ],
            )
        )
        if plot_file != "":
            ax.plot(
                [point_pipe_start.x, point_pipe_end.x],
                [point_pipe_start.z, point_pipe_end.z],
                "k--",
                linewidth=5,
            )
            ax.text(point_pipe_end.x, point_pipe_end.z, "pipe")

        if plot_file != "":
            fig.savefig(plot_file)

        if self.logfile != "":
            f_log = open(self.logfile, "w")
            for line in log:
                f_log.write(line + "\n")
            f_log.close()

        return m

    def to_dgeoflow_model(self) -> DGeoFlowModel:
        """not implemented

        the idea is to generate the complete levee model instead of cutting
        of the geometry at the ditch bottom. Part of the code is done but
        so far we decided to go with the simple model
        """
        raise NotImplementedError
        m = DGeoFlowModel()

        # soiltypes
        for code, params in SOILPARAMETERS.items():
            m.add_soil(
                Soil(
                    name=code,
                    code=code,
                    storage_parameters=StorageParameters(
                        vertical_permeability=params["k_ver"],
                        horizontal_permeability=params["k_hor"],
                    ),
                    color=Color(params["color"].replace("#", "")),
                )
            )

        # create a polygon from the crosssection
        crs_pts = [(p.x, p.z) for p in self.crosssection.points]
        crs_pts.append([self.crosssection.right, self.soilprofile.bottom])
        crs_pts.append([self.crosssection.left, self.soilprofile.bottom])

        pg_crosssection = Polygon(crs_pts)

        for layer in self.soilprofile.soillayers:
            # create the rectangle
            x1 = self.crosssection.left
            x2 = self.crosssection.right
            z1 = layer.top
            z2 = layer.bottom

            # create a shapely polygon out of this
            pg_layer = Polygon([(x1, z1), (x2, z1), (x2, z2), (x1, z2)])

            intersections = pg_layer.intersection(pg_crosssection)

            polygons = []

            if type(intersections) == Polygon:
                polygons = [intersections]
            elif type(intersections) == MultiPolygon:
                polygons = list(intersections.geoms)
            else:
                raise ValueError(
                    f"Unhandled intersectsion type '{type(intersections)}'"
                )

            for pg in polygons:
                if not pg.is_empty:
                    if is_ccw(pg):  # check if clockwise
                        pg = pg.reverse()
                    points = [Point(x=p[0], z=p[1]) for p in pg.boundary.coords][:-1]
                    m.add_layer(
                        points=points, soil_code=layer.short_name, label=layer.soil_name
                    )

        return m

    def plot(
        self,
        right_limit: float,
        filename: str = "",
        width: float = 20.0,
        height: float = 12.0,
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
                    f"AQ: {sl.soil_name} (k;hor={soilparams['k_hor']}, k;ver={soilparams['k_ver']})",
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
                    f"{sl.soil_name} (k;hor={soilparams['k_hor']}, k;ver={soilparams['k_ver']})",
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

        ax.set_ylim(self.soilprofile.bottom, self.crosssection.top + 10.0)

        if filename == "":  # return the figure so more stuff can be added
            return fig, ax

        fig.savefig(filename)
