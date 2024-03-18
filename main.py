import pandas as pd
from pathlib import Path
from pydantic import BaseModel
from typing import List
import time


from objects.soillayer import SoilLayer
from objects.soilprofile import SoilProfile
from objects.scenario import Scenario
from settings import *

# DRY_RUN can be used to quickly generate the calculations for debugging purposes
# set to False to automatically calculate the generated calculations
DRY_RUN = True


class InputData(BaseModel):
    scenarios: List[Scenario] = []

    @classmethod
    def from_pickle(
        cls,
        pickle_path,
        pickle_file,
        dsoil_pickle_file,
    ) -> "InputData":
        logfile = open(f"{PATH_OUTPUT_FILES}/input_parsing.log", "w")
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
                    )
                )
            except Exception as e:
                logfile.write(f"Skipping row {i} because of error {e}\\n")

        logfile.close()
        return result


k_sand = 6  # m/day
anisotropy_factor = 2  # H:V (V=H/anisotropy_factor)
sealevel_rise = 0.0
use_surface_boundary = True

inputdata = InputData.from_pickle(
    PATH_INPUT_FILES,
    TOETSING_PICKLE,
    WBI_LOG_PICKLE,
)

# eerste batch tussen 368-390
inputdata.scenarios = [
    i for i in inputdata.scenarios if i.dijkpaal >= 368 and i.dijkpaal <= 390
]


f_results = open(Path(PATH_OUTPUT_FILES) / "result.csv", "w")
for scenario in inputdata.scenarios:
    log, dm = scenario.to_dgeoflow_model(
        k_sand=k_sand,
        anisotropy_factor=anisotropy_factor,
        sealevel_rise=sealevel_rise,
        use_surface_boundary=use_surface_boundary,
    )

    with open(Path(PATH_OUTPUT_FILES) / f"{scenario.name}.log", "w") as f:
        f.write("\n".join(log))

    if dm is None:
        f_results.write(f"No model could be created for scenario '{scenario.name}'\n")
        continue

    dm.serialize(Path(PATH_OUTPUT_FILES) / f"{scenario.name}.flox")

    if not DRY_RUN:
        start_time = time.time()
        dm.execute()
        end_time = time.time()

        try:
            f_results.write(
                f"Scenario '{scenario.name}': calculation took {(time.time() - start_time):.0f}s, pipe length = {dm.output.PipeLength}m\n"
            )

        except Exception as e:
            f_results.write(
                f"Scenario '{scenario.name}' has no result, got message '{e}'\n"
            )

f_results.close()
