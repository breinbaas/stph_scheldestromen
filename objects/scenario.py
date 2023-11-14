from pydantic import BaseModel
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.pyplot import Figure
import matplotlib.patches as patches
from shapely.geometry import Polygon, MultiPolygon

from objects.crosssection import Crosssection, CrosssectionPoint
from objects.soilprofile import SoilProfile
from settings import PROFIEL_IDS, DICT_POINT_IDS, LIMIT_LEFT, LIMIT_RIGHT
from geolib.models.dgeoflow import DGeoFlowModel
from geolib.soils.soil import Soil, StorageParameters
from geolib.geometry.one import Point


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

    def to_dgeoflow_model(self) -> DGeoFlowModel:
        m = DGeoFlowModel()

        # soiltypes
        m.add_soil(
            Soil(
                name="TestGrondsoort",
                code="CodeGrondsoort",
                storage_parameters=StorageParameters(
                    vertical_permeability=0.1, horizontal_permeability=0.1
                ),
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

            # subtract the layer from the crosssections_polygon
            ##diff = pg_crosssection.difference(pg_layer)
            #
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
                    points = [Point(x=p[0], z=p[1]) for p in pg.boundary.coords][:-1]
                    m.add_layer(points=points, soil_code="CodeGrondsoort", label="Test")

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
