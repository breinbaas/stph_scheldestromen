from pydantic import BaseModel
import pandas as pd
import math
from typing import Dict

from settings import BOTTOM_OFFSET, SOILPARAMETERS


class SoilLayer(BaseModel):
    """Een grondlaag inclusief alle benodigde eigenschappen"""

    soil_name: str
    top: float
    bottom: float
    is_aquifer: int
    aquifer_number: (
        int  # daar waar aquifer_number == is_aquifer = laag waar pipe op mag treden
    )

    @property
    def height(self) -> float:
        """De hoogte van de grondlaag

        Returns:
            float: hoogte van de grondlaag
        """
        return self.top - self.bottom

    @property
    def short_name(self) -> str:
        """This will remove everything after the first _"""
        if self.soil_name.find("_"):
            return self.soil_name.split("_")[0]
        else:
            return self.soil_name

    @property
    def color(self) -> str:
        """De kleur van de grondlaag in de hexadecimale vorm van #RRGGBB

        Returns:
            str: kleur van de grondlaag
        """

        if not self.short_name in SOILPARAMETERS.keys():
            print(f"No color set for soilname '{self.soil_name}', defaulting to grey.")
            return "#b5aeae"
        else:
            return SOILPARAMETERS[self.short_name]["color"]

    @property
    def params(self) -> Dict:
        """De parameters van de grondlaag

        Returns:
            Dict: dictionary met doorlatendheden k_hor en k_ver
        """
        if not self.short_name in SOILPARAMETERS.keys():
            raise ValueError(
                f"No parameters set for soilname '{self.soil_name}', raising exception."
            )
        else:
            return {
                "k_hor": SOILPARAMETERS[self.short_name]["k_hor"],
                "k_ver": SOILPARAMETERS[self.short_name]["k_ver"],
            }

    @classmethod
    def from_dataframe_row(cls, row: pd.Series) -> "SoilLayer":
        """Genereer een grondlaag op basis van een rij uit een dataframe

        Args:
            row (pd.Series): de rij uit het dataframe

        Returns:
            SoilLayer: De gegenereerde grondlaag
        """
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
