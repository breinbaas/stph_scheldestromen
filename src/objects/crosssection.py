from pydantic import BaseModel
from typing import List
from enum import IntEnum


class CrosssectionPointType(IntEnum):
    MV_BINNEN = 0
    SLOOT_1A = 1  # linksboven
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
    x: float
    z: float
    point_type: CrosssectionPointType


class Crosssection(BaseModel):
    points: List[CrosssectionPoint] = []

    @classmethod
    def from_points(cls, points: List[CrosssectionPoint]):
        return Crosssection(points=points)

    @property
    def left(self):
        return min([p.x for p in self.points])

    @property
    def right(self):
        return max([p.x for p in self.points])

    @property
    def width(self):
        return self.right - self.left

    @property
    def top(self):
        return max([p.z for p in self.points])

    @property
    def bottom(self):
        return min([p.z for p in self.points])
