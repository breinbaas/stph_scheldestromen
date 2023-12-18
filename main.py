import pandas as pd
from pathlib import Path
from pydantic import BaseModel
from typing import List
import time
from matplotlib.pyplot import Figure


from objects.soillayer import SoilLayer
from objects.soilprofile import SoilProfile
from objects.scenario import (
    Scenario,
    BoundaryMode,
    PolderLevelMode,
    BOUNDARY_MODE_NAMES,
    POLDERLEVEL_MODE_NAMES,
)
from settings import SLOOT_1A_OFFSET, LIMIT_RIGHT


# the path to the pickle files
PATH_INPUT_FILES="C:\\Users\\brein\\Development\\stph_scheldestromen\\data\\input"
# the path for temporary output files
PATH_OUTPUT_FILES="C:\\Users\\brein\\Development\\stph_scheldestromen\\data\\output"
# the pickle file with scenarion info
TOETSING_PICKLE="wbi_log_toetsing_relevant.pkl"
# the pickle file with soil information
WBI_LOG_PICKLE="wbi_log.pkl"

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
        logfile = open(f"{PATH_OUTPUT_FILES}/input_parsing.log", 'w')
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
                logfile.write(f"Skipping row {i} because of error {e}\n")

        logfile.close()
        return result


# choices, choices...
boundary_mode = BoundaryMode.PLRIGHT
polderlevel_mode = PolderLevelMode.FIRST_LAYER_BOTTOM
# k_zand = 6  # m/day
# anisotropy_factor = 2  # H:V (V=H/anisotropy_factor)


inputdata = InputData.from_pickle(
    PATH_INPUT_FILES,
    TOETSING_PICKLE,
    WBI_LOG_PICKLE,
    boundary_mode=boundary_mode,
    polderlevel_mode=polderlevel_mode,
)

fig = Figure(figsize=(10, 6))
ax = fig.add_subplot()
for k_zand in [6, 13]:
    for anisotropy_factor in [2, 10]:
        scenario_names = []
        pipe_lengths = []

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

                scenario_names.append(scenario.name)
                pipe_lengths.append(dm.output.PipeLength)
            except Exception as e:
                # plot so we can see what might have gone wrong with this geometry
                scenario.plot(
                    LIMIT_RIGHT, 
                    k_zand, 
                    anisotropy_factor, 
                    f"{PATH_OUTPUT_FILES}/DEBUG_{scenario.name}.png",
                    error_message=f"{e}"
                )
                f_log = open(filename_log, "a+")
                f_log.write(
                    f"Cannot handle scenario '{scenario.name}', got error '{e}'\n"
                )
                f_log.close()

        # NOTE this is hard coded so if you change the k_zand or anisotropy settings you might want to adjust the next code
        c = "r" if k_zand == 13 else "b"
        ls = "-" if anisotropy_factor == 13 else "--"

        ax.plot(
            scenario_names,
            pipe_lengths,
            label=f"k:{k_zand} a:{anisotropy_factor}",
            c=c,
            ls=ls,
        )

ax.grid(True)
ax.legend()
ax.set_title("Berekeningen ronde 4")

fig.savefig(f"{PATH_OUTPUT_FILES}/result.png")
