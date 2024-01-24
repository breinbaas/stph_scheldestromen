import numpy as np

from settings import DICT_POINT_IDS, SOILPARAMETERS


def get_name_from_point_type(point_type):
    for k, v in DICT_POINT_IDS.items():
        if v == point_type:
            return k


def get_soil_parameters(soilname):
    for k, v in SOILPARAMETERS.items():
        if k == soilname:
            return v


def calc_regression(x_data, y_data, x_interp):
    """Calculate regression from x and y dataset."""

    # fit
    LinRegCoef = np.polyfit(np.log(np.asarray(x_data)), y_data, 1)
    # interpolatie plot
    x_fit = np.asarray([x_data[1], x_interp])
    y_fit = np.log(x_fit) * LinRegCoef[0] + LinRegCoef[1]

    return LinRegCoef, y_fit[-1]
