from settings import DICT_POINT_IDS, SOILPARAMETERS


def get_name_from_point_type(point_type):
    for k, v in DICT_POINT_IDS.items():
        if v == point_type:
            return k


def get_soil_parameters(soilname):
    for k, v in SOILPARAMETERS.items():
        if k == soilname:
            return v
