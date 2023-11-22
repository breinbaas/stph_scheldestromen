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

from objects.crosssection import Crosssection, CrosssectionPoint, CrosssectionPointType
from objects.soilprofile import SoilProfile
from settings import (
    PROFIEL_IDS,
    DICT_POINT_IDS,
    LIMIT_LEFT,
    LIMIT_RIGHT,
    SOILPARAMETERS,
    DITCH_BOUNDARY_OFFSET,
)


class Scenario(BaseModel):
    name: str
    crosssection: Crosssection
    # intredepunt: float
    # uittredepunt: float
    soilprofile: SoilProfile
    slootnummer: str
    max_zp_wp: float
    bovengrens_slootpeil: float
    ondergrens_slootpeil: float
    slootpeil: float
    waterstand_bij_norm: float

    @classmethod
    def from_dataframe_row(
        cls, name, row: pd.Series, soilprofile: SoilProfile
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

    def to_flat_dgeoflow_model(self) -> DGeoFlowModel:
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

        if sloot_1a.x + DITCH_BOUNDARY_OFFSET > self.crosssection.right:
            raise ValueError(
                f"The offset right of the sloot_1a is too large, the boundary exceeds the model limit."
            )

        # we cut our gemeotry off at the z value of insteek (sloot_1d) or point binnen (mv_binnen)
        self.soilprofile.cut_top_at_z(sloot_1d.z)

        x1 = self.crosssection.left
        x2 = self.crosssection.right
        boundary_added = False
        for layer in self.soilprofile.soillayers:
            points = [
                Point(x=p[0], z=p[1])
                for p in zip(
                    [x1, x2, x2, x1],
                    [layer.top, layer.top, layer.bottom, layer.bottom],
                )
            ]
            if not boundary_added:
                # first layer so add the points to enable the selection of the boundaries
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
            m.add_layer(
                points=points, soil_code=layer.short_name, label=layer.soil_name
            )

        # add the river level boundary
        points_river_level = []
        for layer in self.soilprofile.soillayers:
            points_river_level.append(Point(x=self.crosssection.left, z=layer.top))

        m.add_boundary_condition(
            points=points_river_level[::-1],
            head_level=self.waterstand_bij_norm,
            label="river level at norm",
        )

        # add the polder level boundary
        m.add_boundary_condition(
            points=[boundary_pp_start, boundary_pp_end],
            head_level=self.max_zp_wp,
            label="polder level",
        )

        # add the phreatic level boundary
        m.add_boundary_condition(
            points=[boundary_pl_start, Point(x=x2, z=boundary_pl_start.z)],
            head_level=sloot_1a.z,
            label="phreatic level",
        )

        return m

    def to_dgeoflow_model(self) -> DGeoFlowModel:
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

    def plot(self, filename: str, width: float = 10.0, height: float = 6.0):
        fig = Figure(figsize=(width, height))
        ax = fig.add_subplot()

        # grondlagen
        for sl in self.soilprofile.soillayers:
            # aquifer krijgt hatching
            if sl == self.soilprofile.aquifer:
                ax.add_patch(
                    patches.Rectangle(
                        (self.crosssection.left, sl.bottom),
                        self.crosssection.width,
                        sl.height,
                        facecolor=sl.color,
                        # hatch="///",
                        edgecolor="black",
                        hatch="//",
                    )
                )
                ax.text(self.crosssection.left, sl.bottom + 0.1, f"AQ: {sl.soil_name}")
            else:
                ax.add_patch(
                    patches.Rectangle(
                        (self.crosssection.left, sl.bottom),
                        self.crosssection.width,
                        sl.height,
                        color=sl.color,
                    )
                )
                ax.text(self.crosssection.left, sl.bottom + 0.1, sl.soil_name)

        # dwarsprofiel
        ax.plot(
            [p.x for p in self.crosssection.points],
            [p.z for p in self.crosssection.points],
            "k",
        )

        ax.set_ylim(self.soilprofile.bottom, self.crosssection.top)
        fig.savefig(filename)
