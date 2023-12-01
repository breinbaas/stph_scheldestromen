from copy import deepcopy

from objects.soilprofile import SoilProfile
from objects.soillayer import SoilLayer


def test_get_left_boundary_z_coordinates():
    sp = SoilProfile(
        id=-1,
        soillayers=[
            SoilLayer(
                soil_name="A", top=2.0, bottom=0.0, is_aquifer=-1, aquifer_number=-1
            ),
            SoilLayer(
                soil_name="B", top=0.0, bottom=-5.0, is_aquifer=-1, aquifer_number=-1
            ),
            SoilLayer(
                soil_name="C", top=-5.0, bottom=-10.0, is_aquifer=-1, aquifer_number=-1
            ),
        ],
    )

    assert sp.get_soillayer_z_coordinates() == [-10.0, -5.0, 0.0, 2.0]


def test_cut_top_at_z():
    sp = SoilProfile(
        id=-1,
        soillayers=[
            SoilLayer(
                soil_name="A", top=2.0, bottom=0.0, is_aquifer=-1, aquifer_number=-1
            ),
            SoilLayer(
                soil_name="B", top=0.0, bottom=-5.0, is_aquifer=-1, aquifer_number=-1
            ),
            SoilLayer(
                soil_name="C", top=-5.0, bottom=-10.0, is_aquifer=-1, aquifer_number=-1
            ),
        ],
    )

    # test cut at top line
    sp_1 = deepcopy(sp)
    sp_1.cut_top_at_z(0.0)
    assert sp_1 == SoilProfile(
        id=-1,
        soillayers=[
            SoilLayer(
                soil_name="B", top=0.0, bottom=-5.0, is_aquifer=-1, aquifer_number=-1
            ),
            SoilLayer(
                soil_name="C", top=-5.0, bottom=-10.0, is_aquifer=-1, aquifer_number=-1
            ),
        ],
    )

    # test cut in middle of layer
    sp_2 = deepcopy(sp)
    sp_2.cut_top_at_z(-1.0)
    assert sp_2 == SoilProfile(
        id=-1,
        soillayers=[
            SoilLayer(
                soil_name="B", top=-1.0, bottom=-5.0, is_aquifer=-1, aquifer_number=-1
            ),
            SoilLayer(
                soil_name="C", top=-5.0, bottom=-10.0, is_aquifer=-1, aquifer_number=-1
            ),
        ],
    )

    # test cut above top
    sp_3 = deepcopy(sp)
    sp_3.cut_top_at_z(5.0)
    assert sp_3 == sp

    # test cut below bottom
    sp_4 = deepcopy(sp)
    sp_4.cut_top_at_z(-15.0)
    assert len(sp_4.soillayers) == 0
