import pandas as pd
import os
from pathlib import Path
from dotenv import load_dotenv
from pydantic import BaseModel
from typing import List


from objects.soillayer import SoilLayer
from objects.soilprofile import SoilProfile
from objects.scenario import Scenario

load_dotenv()

# change the .env settings to choose
# the correct path and input pickle (complete / relevant)
PATH_INPUT_FILES = os.environ.get(
    "PATH_INPUT_FILES"
)  # the path to the pickle files read from .env
PATH_OUTPUT_FILES = os.environ.get(
    "PATH_OUTPUT_FILES"
)  # the path for temporary output files
TOETSING_PICKLE = os.environ.get(
    "TOETSING_PICKLE"
)  # the pickle file with scenarion info
WBI_LOG_PICKLE = os.environ.get(
    "WBI_LOG_PICKLE"
)  # the pickle file with soil information


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
    scenario.plot(f"{PATH_OUTPUT_FILES}/{scenario.name}.png")
    dm = scenario.to_dgeoflow_model()
    dm.serialize(Path(PATH_OUTPUT_FILES) / f"{scenario.name}.flox")
    break
