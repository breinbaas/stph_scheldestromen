import pandas as pd
import os
from pathlib import Path
from dotenv import load_dotenv
from pydantic import BaseModel
from typing import List
from enum import IntEnum
import matplotlib.pyplot as plt
from matplotlib.pyplot import Figure
import matplotlib.patches as patches
import math

load_dotenv()

# change the .env settings to choose
# the correct path and input pickle (complete / relevant)
PATH_INPUT_FILES = os.environ.get(
    "PATH_INPUT_FILES"
)  # the path to the pickle files read from .env
TOETSING_PICKLE = os.environ.get(
    "TOETSING_PICKLE"
)  # the pickle file with scenarion info
WBI_LOG_PICKLE = os.environ.get(
    "WBI_LOG_PICKLE"
)  # the pickle file with soil information
BOTTOM_OFFSET = 10.0  # if we have no bottom on the soilprofile we use the top of the deepest layer minus this offset


class CrosssectionPointType(IntEnum):
    MV_BINNEN = 0
    SLOOT_1A = 1  # linksboven
    SLOOT_1C = 2  # linksonder
    SLOOT_1D = 3  # rechtsonder
    SLOOT_1B = 4  # rechtsboven
    WEG_1 = 5
    TEEN_1 = 6
    BERM_1A = 7
    BERM_1B = 8
    KRUIN_1 = 9
    KRUIN_2 = 10
    BERM_2A = 11
    BERM_2B = 12
    TEEN_2 = 13
    WEG_2 = 14
    SLOOT_2 = 15
    MV_BUITEN = 16


DICT_POINT_IDS = {
    "MV_bin": CrosssectionPointType.MV_BINNEN,
    "Sloot_1a": CrosssectionPointType.SLOOT_1A,
    "Sloot_1c": CrosssectionPointType.SLOOT_1C,
    "Sloot_1d": CrosssectionPointType.SLOOT_1D,
    "Sloot_1b": CrosssectionPointType.SLOOT_1B,
    "Weg_1": CrosssectionPointType.WEG_1,
    "Teen_1": CrosssectionPointType.TEEN_1,
    "Berm_1a": CrosssectionPointType.BERM_1A,
    "Berm_1b": CrosssectionPointType.BERM_1B,
    "Kruin_1": CrosssectionPointType.KRUIN_1,
    "Kruin_2": CrosssectionPointType.KRUIN_2,
    "Berm_2a": CrosssectionPointType.BERM_2A,
    "Berm_2b": CrosssectionPointType.BERM_2B,
    "Teen_2": CrosssectionPointType.TEEN_2,
    "Weg_2": CrosssectionPointType.WEG_2,
    "Sloot_2": CrosssectionPointType.SLOOT_2,
    "MV_bui": CrosssectionPointType.MV_BUITEN,
}

PROFIEL_IDS = (  # NOTE this is nasty way to use () but this happens due to an error in black formatting
    [
        "MV_bin",
        "Sloot_1a",
        "Sloot_1c",
        "Sloot_1d",
        "Sloot_1b",
        "Weg_1",
        "Teen_1",
        "Berm_1a",
        "Berm_1b",
        "Kruin_1",
        "Kruin_2",
        "Berm_2a",
        "Berm_2b",
        "Teen_2",
        "Weg_2",
        "Sloot_2",
        "MV_bui",
    ],
)


class CrosssectionPoint(BaseModel):
    x: float
    z: float
    point_type: CrosssectionPointType


class Crosssection(BaseModel):
    points: List[CrosssectionPoint] = []

    @classmethod
    def from_points(cls, points: List[CrosssectionPoint]):
        return Crosssection(points=points)

    @property
    def left(self):
        return min([p.x for p in self.points])

    @property
    def right(self):
        return max([p.x for p in self.points])

    @property
    def width(self):
        return self.right - self.left

    @property
    def top(self):
        return max([p.z for p in self.points])

    @property
    def bottom(self):
        return min([p.z for p in self.points])


class SoilLayer(BaseModel):
    soil_name: str
    top: float
    bottom: float
    is_aquifer: int
    aquifer_number: int  # daar waar aquifer_number == is_aquifer = laag waar pipe op mag treden

    @property
    def height(self):
        return self.top - self.bottom

    @classmethod
    def from_dataframe_row(cls, row: pd.Series) -> "SoilProfile":
        top = float(row["top_level"])
        bottom = float(row["botm_level"])

        if math.isnan(bottom):
            bottom = top - BOTTOM_OFFSET

        return SoilLayer(
            soil_name=row["soil_name"],
            is_aquifer=int(row["is_aquifer"]),
            top=top,
            bottom=bottom,
            aquifer_number=int(row["aq_nr"]),
        )


class SoilProfile(BaseModel):
    id: int
    soillayers: List[SoilLayer] = []

    @property
    def top(self):
        if len(self.soillayers) == 0:
            raise ValueError("Trying to get top of a soilprofile with no soillayers")
        return self.soillayers[0].top

    @property
    def bottom(self):
        if len(self.soillayers) == 0:
            raise ValueError("Trying to get bottom of a soilprofile with no soillayers")

        return self.soillayers[-1].bottom


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


class InputData(BaseModel):
    scenarios: List[Scenario] = []

    @classmethod
    def from_pickle(cls, pickle_path, pickle_file, dsoil_pickle_file) -> "InputData":
        result = InputData()

        # scenario info
        df = pd.read_pickle(Path(pickle_path) / pickle_file)

        # convert soil info to soilprofiles
        soilprofiles = []
        df_soil = pd.read_pickle(Path(pickle_path) / dsoil_pickle_file)
        df_soil = df_soil["dsoil"]

        for profile_id in df_soil["profile"].unique():
            soilprofile = SoilProfile(id=profile_id)
            selection = df_soil[df_soil["profile"] == profile_id]
            for _, row in selection.iterrows():
                soilprofile.soillayers.append(SoilLayer.from_dataframe_row(row))
            soilprofiles.append(soilprofile)

        # we need to correct one error
        df.rename(columns={"xMVB_bui": "xMV_bui"}, inplace=True)

        # this makes it easier to parse the points
        df.columns = [s.lower() for s in df.columns]

        for i, row in df.iterrows():
            try:
                # find the soilprofile that goes with the scenario
                soilprofile = None
                for sp in soilprofiles:
                    if sp.id == row["ondergrond"]:
                        soilprofile = sp
                        break

                if soilprofile is None:
                    raise ValueError(f"Could not find soilprofile with id={id}")

                result.scenarios.append(
                    Scenario.from_dataframe_row(i, row, soilprofile)
                )
            except Exception as e:
                raise e

        return result


inputdata = InputData.from_pickle(PATH_INPUT_FILES, TOETSING_PICKLE, WBI_LOG_PICKLE)
for scenario in inputdata.scenarios:
    scenario.plot(f"./tmp/{scenario.name}.png")
    break
