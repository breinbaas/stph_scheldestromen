from pydantic import BaseModel
import pandas as pd
import math

from settings import BOTTOM_OFFSET, SOILCOLORS


class SoilLayer(BaseModel):
    soil_name: str
    top: float
    bottom: float
    is_aquifer: int
    aquifer_number: int  # daar waar aquifer_number == is_aquifer = laag waar pipe op mag treden

    @property
    def height(self):
        return self.top - self.bottom

    @property
    def color(self):
        if self.soil_name.find("_"):
            sn = self.soil_name.split("_")[0]
        else:
            sn = self.soil_name

        if not sn in SOILCOLORS.keys():
            print(f"No color set for soilname '{self.soil_name}', defaulting to grey.")
            return "#b5aeae"
        else:
            return SOILCOLORS[sn]

    @classmethod
    def from_dataframe_row(cls, row: pd.Series) -> "SoilLayer":
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