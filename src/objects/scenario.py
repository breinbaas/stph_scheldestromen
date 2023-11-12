from pydantic import BaseModel
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.pyplot import Figure
import matplotlib.patches as patches

from objects.crosssection import Crosssection, CrosssectionPoint
from objects.soilprofile import SoilProfile
from settings import PROFIEL_IDS, DICT_POINT_IDS


class Scenario(BaseModel):
    name: str
    crosssection: Crosssection
    uittredepunt: float
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

        result = Scenario(
            name=name,
            crosssection=Crosssection.from_points(points=dppoints),
            uittredepunt=float(row["uittredepunt"]),
            soilprofile=soilprofile,
            slootnummer=str(row["slootnummer"]),
            max_zp_wp=float(row["max_zp_wp_mnap"]),
            bovengrens_slootpeil=float(row["bovengrens_slootpeil_mnap"]),
            ondergrens_slootpeil=float(row["ondergrens_slootpeil_mnap"]),
            slootpeil=float(row["slootpeil_mnap"]),
            waterstand_bij_norm=float(row["waterstand_bij_norm_mnap"]),
        )

        return result

    def plot(self, filename: str, width: float = 10.0, height: float = 6.0):
        fig = Figure(figsize=(width, height))
        ax = fig.add_subplot()

        for sl in self.soilprofile.soillayers:
            ax.add_patch(
                patches.Rectangle(
                    (self.crosssection.left, sl.bottom),
                    self.crosssection.width,
                    sl.height,
                    fill=None,
                    # hatch="///",
                )
            )
            ax.text(self.crosssection.left, sl.bottom + 0.1, sl.soil_name)

        ax.plot(
            [p.x for p in self.crosssection.points],
            [p.z for p in self.crosssection.points],
        )

        ax.set_ylim(self.soilprofile.bottom, self.crosssection.top)
        fig.savefig(filename)
