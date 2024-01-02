from pydantic import BaseModel
from typing import List, Tuple

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

    def get_first_acquifer_below(self, z: float):
        for soillayer in self.soillayers:
            if soillayer.top < z and soillayer.soil_name.find("_Aq") > -1:
                return soillayer
        return None

    def get_soillayer_z_coordinates(self) -> List[float]:
        """Get the z coordinates soillayers from bottom to top

        Returns:
            List[float]: z coordinates of the soillyers from bottom to top
        """
        result = [l.bottom for l in self.soillayers[::-1]]
        if len(self.soillayers) > 0:
            result.append(self.soillayers[0].top)
        return result

    def get_sth_intredepunt_zs(self) -> List[float]:
        """Get the points for the left boundary (str intredepunt)

        Dit geeft de punten van onder naar boven van de linkerzijde
        van de geometrie van de bodem van het model tot de bovenzijde
        van de aquifer

        Returns:
            List[float]: Punten van de linker randvoorwaarde van laag naar hoog
        """
        zs = []
        for l in self.soillayers[::-1]:
            zs.append(l.bottom)
            if l == self.aquifer:
                zs.append(l.top)
                return zs

    def cut_top_at_z(self, z: float):
        """Remove all soillayers above z and limit the top of the soilprofile to z

        Args:
            z (float): The new top of the soilprofile
        """
        result = []
        for sl in self.soillayers:
            if sl.top <= z:
                result.append(sl)
            elif sl.bottom >= z:
                continue
            else:
                result.append(
                    SoilLayer(
                        soil_name=sl.soil_name,
                        top=z,
                        bottom=sl.bottom,
                        is_aquifer=sl.is_aquifer,
                        aquifer_number=sl.aquifer_number,
                    )
                )
        self.soillayers = result
