import pandas as pd
import os
from pathlib import Path
from dotenv import load_dotenv
from pydantic import BaseModel
from typing import List
import time


from objects.soillayer import SoilLayer
from objects.soilprofile import SoilProfile
from objects.scenario import (
    Scenario,
    BoundaryMode,
    PolderLevelMode,
    BOUNDARY_MODE_NAMES,
    POLDERLEVEL_MODE_NAMES,
)

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
    def from_pickle(
        cls,
        pickle_path,
        pickle_file,
        dsoil_pickle_file,
        boundary_mode: BoundaryMode = BoundaryMode.PLTOP,
        polderlevel_mode: PolderLevelMode = PolderLevelMode.DITCH_BOTTOM,
    ) -> "InputData":
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
                    Scenario.from_dataframe_row(
                        i,
                        row,
                        soilprofile,
                        boundary_mode=boundary_mode,
                        polderlevel_mode=polderlevel_mode,
                    )
                )
            except Exception as e:
                raise e

        return result


# choices, choices...
boundary_mode = PolderLevelMode.FIRST_LAYER_BOTTOM
polderlevel_mode = BoundaryMode.PLTOP_AND_RIGHT
sloot_1a_offset = (
    40  # breedte in de geometrie die meegenomen wordt naast het sloot_1a punt
)
k_zand = 0.864  # standaard waarden -> 0.864, 2, 4, 10 m/dag voor grondsoortnamen ["PL", "PLa", "ZA", "ZAa"]

# TODO > DZ en AA staat vast op 5m/dag -> ok?

inputdata = InputData.from_pickle(
    PATH_INPUT_FILES,
    TOETSING_PICKLE,
    WBI_LOG_PICKLE,
    boundary_mode=boundary_mode,
    polderlevel_mode=polderlevel_mode,
)

f_log = open("data/output/log.txt", "w")
f_output = open(
    f"data/output/result_{BOUNDARY_MODE_NAMES[boundary_mode]}_{POLDERLEVEL_MODE_NAMES[polderlevel_mode]}_{k_zand:0.3f}.csv",
    "w",
)
f_output.write(
    "scenario [-],boundary_mode [-],polderlevel_mode [-],k_zand [m/day],calculation_time [s],pipe_length [m]\n"
)

for scenario in inputdata.scenarios:
    try:
        scenario.logfile = f"{PATH_OUTPUT_FILES}/{scenario.name}.{BOUNDARY_MODE_NAMES[boundary_mode]}.{POLDERLEVEL_MODE_NAMES[polderlevel_mode]}.log.txt"  # For debugging
        dm = scenario.to_flat_dgeoflow_model(
            sloot_1a_offset=sloot_1a_offset,
            plot_file=f"{PATH_OUTPUT_FILES}/{scenario.name}.{BOUNDARY_MODE_NAMES[boundary_mode]}.{POLDERLEVEL_MODE_NAMES[polderlevel_mode]}.png",
            k_zand=k_zand,
        )
        dm.serialize(
            Path(PATH_OUTPUT_FILES)
            / f"{scenario.name}.{BOUNDARY_MODE_NAMES[boundary_mode]}.{POLDERLEVEL_MODE_NAMES[polderlevel_mode]}.flat.flox"
        )
        start_time = time.time()
        dm.execute()
        f_output.write(
            f"{scenario.name},{BOUNDARY_MODE_NAMES[boundary_mode]},{POLDERLEVEL_MODE_NAMES[polderlevel_mode]},{k_zand:0.3f},{(time.time() - start_time):.0f},{dm.output.PipeLength:.2f}\n"
        )
    except Exception as e:
        f_log.write(f"Cannot handle scenario '{scenario.name}', got error '{e}'\n")

f_output.close()
