from pydantic import BaseModel
from typing import List

from objects.soillayer import SoilLayer


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

    @property
    def aquifer(self):
        for l in self.soillayers:
            if l.is_aquifer == l.aquifer_number:
                return l
        return None
