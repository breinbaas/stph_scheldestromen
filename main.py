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
from settings import SLOOT_1A_OFFSET

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

# bereken enkel de scenarios waar de dijkpaal hm groter is dan deze waarde
DIJKPAAL_LIMIT_LEFT = 404
# bereken enkel de scenarios waar de dijkpaal hm kleiner is dan deze waarde
DIJKPAAL_LIMIT_RIGHT = 490


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
boundary_mode = BoundaryMode.PLRIGHT
polderlevel_mode = PolderLevelMode.FIRST_LAYER_BOTTOM
k_zand = 6  # m/day
anisotropy_factor = 10  # H:V (V=H/anisotropy_factor)


inputdata = InputData.from_pickle(
    PATH_INPUT_FILES,
    TOETSING_PICKLE,
    WBI_LOG_PICKLE,
    boundary_mode=boundary_mode,
    polderlevel_mode=polderlevel_mode,
)

filename_log = f"{PATH_OUTPUT_FILES}/log_{BOUNDARY_MODE_NAMES[boundary_mode]}_{POLDERLEVEL_MODE_NAMES[polderlevel_mode]}_k{k_zand:0.3f}_a{anisotropy_factor}.txt"
f_log = open(filename_log, "w")

filename_output = f"{PATH_OUTPUT_FILES}/result_{BOUNDARY_MODE_NAMES[boundary_mode]}_{POLDERLEVEL_MODE_NAMES[polderlevel_mode]}_k{k_zand:0.3f}_a{anisotropy_factor}.csv"
f_output = open(filename_output, "w")
f_output.write(
    "scenario [-],boundary_mode [-],polderlevel_mode [-],k_zand [m/day],calculation_time [s],pipe_length [m]\n"
)
f_log.close()
f_output.close()

for scenario in inputdata.scenarios:
    if (
        scenario.dijkpaal < DIJKPAAL_LIMIT_LEFT
        or scenario.dijkpaal > DIJKPAAL_LIMIT_RIGHT
    ):
        continue
    try:
        scenario.logfile = f"{PATH_OUTPUT_FILES}/{scenario.name}.{BOUNDARY_MODE_NAMES[boundary_mode]}_{POLDERLEVEL_MODE_NAMES[polderlevel_mode]}_k{k_zand:0.3f}_a{anisotropy_factor}.log.txt"  # For debugging
        dm = scenario.to_flat_dgeoflow_model(
            sloot_1a_offset=SLOOT_1A_OFFSET,
            plot_file=f"{PATH_OUTPUT_FILES}/{scenario.name}.{BOUNDARY_MODE_NAMES[boundary_mode]}_{POLDERLEVEL_MODE_NAMES[polderlevel_mode]}_k{k_zand:0.3f}_a{anisotropy_factor}.png",
            k_zand=k_zand,
            anisotropy_factor=anisotropy_factor,
        )
        dm.serialize(
            Path(PATH_OUTPUT_FILES)
            / f"{scenario.name}.{BOUNDARY_MODE_NAMES[boundary_mode]}_{POLDERLEVEL_MODE_NAMES[polderlevel_mode]}_k{k_zand:0.3f}_a{anisotropy_factor}.flat.flox"
        )
        start_time = time.time()
        dm.execute()
        f_output = open(filename_output, "a+")
        f_output.write(
            f"{scenario.name},{BOUNDARY_MODE_NAMES[boundary_mode]},{POLDERLEVEL_MODE_NAMES[polderlevel_mode]},{k_zand:0.3f},{(time.time() - start_time):.0f},{dm.output.PipeLength:.2f}\n"
        )
        f_output.close()
    except Exception as e:
        f_log = open(filename_log, "a+")
        f_log.write(f"Cannot handle scenario '{scenario.name}', got error '{e}'\n")
        f_log.close()
