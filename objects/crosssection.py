from pydantic import BaseModel
from typing import List, Optional
from enum import IntEnum


class CrosssectionPointType(IntEnum):
    """Class die het type van een karakteristiek punt op een dwarsprofiel aangeeft"""

    NONE = -1
    MV_BINNEN = 0
    SLOOT_1A = 1  # linksboven # INSTEEK (bovenkant sloot)
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


class CrosssectionPoint(BaseModel):
    """Punt op het dwarsprofiel"""

    x: float
    z: float
    point_type: CrosssectionPointType


class Crosssection(BaseModel):
    """Deze class bevat alle benodigde dwarsprofiel informatie inclusief
    functies en eigenschappen om informatie uit het profiel op te halen
    """

    points: List[CrosssectionPoint] = []

    @classmethod
    def from_points(cls, points: List[CrosssectionPoint]) -> "Crosssection":
        """Genereer een dwarsprofiel op basis van een lijst met punten

        Args:
            points (List[CrosssectionPoint]): De punten die het profiel vormen

        Returns:
            Crosssection: Geeft een dwarsprofiel class terug
        """
        return Crosssection(points=points)

    @property
    def left(self) -> CrosssectionPoint:
        """Het meest linkse punt op het profiel

        Returns:
            CrosssectionPoint: het linker punt op het profiel
        """
        return min([p.x for p in self.points])

    @property
    def right(self) -> CrosssectionPoint:
        """Het meest rechtse punt op het profiel

        Returns:
            CrosssectionPoint: het rechter punt op het profiel
        """
        return max([p.x for p in self.points])

    @property
    def width(self) -> float:
        """De breedte van het profiel

        Returns:
            float: breedte van het profiel
        """
        return self.right - self.left

    @property
    def top(self) -> float:
        """Het hoogste punt op het profiel

        Returns:
            float: hoogste punt op het profiel
        """
        return max([p.z for p in self.points])

    @property
    def bottom(self) -> float:
        """Het laagste punt op het profiel

        Returns:
            float: het laagste punt op het profiel
        """

        return min([p.z for p in self.points])

    def mirror(self):
        """Spiegel het profiel"""
        self.points = [
            CrosssectionPoint(x=-1 * p.x, z=p.z, point_type=p.point_type)
            for p in self.points
        ][::-1]

    def limit_left(self, left: float) -> None:
        """Breek het profiel aan de linkerzijde af op het gegeven punt

        Args:
            left (float): het linkerpunt vanaf waar het profiel afgebroken moet worden
        """
        new_points = []
        for i in range(1, len(self.points)):
            p1 = self.points[i - 1]
            p2 = self.points[i]
            if p2.x < left:
                continue
            elif p1.x < left and p2.x > left:
                x = left
                z = p1.z + (left - p1.x) / (p2.x - p1.x) * (p2.z - p1.z)
                new_points.append(
                    CrosssectionPoint(
                        x=x, z=z, point_type=CrosssectionPointType.MV_BUITEN
                    )
                )
            else:
                if i == 1:
                    new_points.append(self.points[i - 1])
                new_points.append(self.points[i])
        self.points = new_points
        self.points[0].point_type = (
            CrosssectionPointType.MV_BUITEN
        )  # just to be sure if a point is exaclty on x_left

    def limit_right(self, right: float) -> None:
        """Breek het profiel aan de rechterzijde af op het gegeven punt

        Args:
            right (float): het rechterpunt vanaf waar het profiel afgebroken moet worden
        """
        new_points = []
        for i in range(1, len(self.points)):
            p1 = self.points[i - 1]
            p2 = self.points[i]
            if p1.x < right and p2.x > right:
                x = right
                z = p1.z + (right - p1.x) / (p2.x - p1.x) * (p2.z - p1.z)
                new_points.append(
                    CrosssectionPoint(
                        x=x, z=z, point_type=CrosssectionPointType.MV_BINNEN
                    )
                )
                break
            else:
                if i == 1:
                    new_points.append(self.points[i - 1])
                new_points.append(self.points[i])
        self.points = new_points
        self.points[0].point_type = (
            CrosssectionPointType.MV_BINNEN
        )  # just to be sure if a point is exaclty on x_right

    def get_point_by_point_type(
        self, point_type: CrosssectionPointType
    ) -> Optional[CrosssectionPoint]:
        """Get the point on the crosssections that represents the given point type

        Args:
            point_type (CrosssectionPointType): The point type to look for

        Returns:
            CrosssectionPoint: The point or None if not found
        """
        for p in self.points:
            if p.point_type == point_type:
                return p

        return None
