from objects.crosssection import CrosssectionPointType

# the path to the pickle files
PATH_INPUT_FILES = (
    "C:\\Users\\brein\\Documents\\Klanten\\Scheldestromen\\ZakVanBeveland\\input"
)
# the path for temporary output files
PATH_OUTPUT_FILES = (
    "C:\\Users\\brein\\Documents\\Klanten\\Scheldestromen\\ZakVanBeveland\\output"
)
# the pickle file with scenarion info
# TOETSING_PICKLE = "wbi_log_toetsing_rvw_2024_relevant.pkl"
TOETSING_PICKLE = "wbi_log_toetsing_rvw_2024_relevant.pkl"
# the pickle file with soil information
WBI_LOG_PICKLE = "wbi_log.pkl"

# als debug == True dan gebruiken we enkel dp 467 en 314 als test
DEBUG = True

# mogelijke extra opzet t.g.v. zeespiegelstijging, deze wordt 1 op 1 doorgegeven aan de linker en rechter rand boundaries
SEA_LEVEL_RISE_OFFSET = 0.5

# default waarden voor getijdenzand en pleistoceen
K_GETIJDEZAND = 6
K_PLEISTOCEEN = 13

# breedte van de boundary voor het polderniveau (met of zonder de 0.3d regel)
POLDER_BOUNDARY_WIDTH = 1.0

# dijkpalen waartussen getijdenzand moet worden aangenomen voor aquifer
# let op pleistoceen heeft altijd K_PLEISTOCEEN
GETIJDEZAND_TUSSEN_DIJKPALEN = [(292, 484), (512, 519)]

BOTTOM_OFFSET = 10.0  # if we have no bottom on the soilprofile we use the top of the deepest layer minus this offset
LIMIT_LEFT = -50.0  # limit the crosssection to the given value on the left side
LIMIT_RIGHT = 100.0  # limit the crosssection to the given value on the right side
DITCH_BOUNDARY_OFFSET = 1.0  # distance from sloot_1c point to the start of the boundary for the phreatic level
DEFAULT_D70 = 100  # in um (micrometers = mm * 1000)
MIN_MESH_SIZE = 2  # in m

# de volgende grondsoorten krijgen de eigenschappen van zand
SOILS_WITH_K_ZAND = [
    "AA",
    "DZ",
    "PL",
    "PLa",
    "ZA",
    "ZAa",
    "CZ",
]  # these soils will get the k_zand instead of the parameters in the settings
RIGHT_SIDE_BOUNDARY_OFFSET = (
    3  # the right boundary will have the level of the left side minus this offset
)
SLOOT_1A_OFFSET = 40  # the length of the geometry from the sloot1a point (rightmost ditch point) to the right
PIPE_MESH_SIZE = 0.5

DICT_POINT_IDS = {
    "MV_bin": CrosssectionPointType.MV_BINNEN,
    "Sloot_1a": CrosssectionPointType.SLOOT_1A,
    "Sloot_1c": CrosssectionPointType.SLOOT_1C,
    "Sloot_1d": CrosssectionPointType.SLOOT_1D,
    "Sloot_1b": CrosssectionPointType.SLOOT_1B,
    "Weg_1": CrosssectionPointType.WEG_1,
    "Teen_1": CrosssectionPointType.TEEN_1,
    "Berm_1a": CrosssectionPointType.BERM_1A,
    "Berm_1b": CrosssectionPointType.BERM_1B,
    "Kruin_1": CrosssectionPointType.KRUIN_1,
    "Kruin_2": CrosssectionPointType.KRUIN_2,
    "Berm_2a": CrosssectionPointType.BERM_2A,
    "Berm_2b": CrosssectionPointType.BERM_2B,
    "Teen_2": CrosssectionPointType.TEEN_2,
    "Weg_2": CrosssectionPointType.WEG_2,
    "Sloot_2": CrosssectionPointType.SLOOT_2,
    "MV_bui": CrosssectionPointType.MV_BUITEN,
}

PROFIEL_IDS = (  # NOTE this is nasty way to use () but this happens due to an error in black formatting
    [
        "MV_bin",
        "Sloot_1a",
        "Sloot_1c",
        "Sloot_1d",
        "Sloot_1b",
        "Weg_1",
        "Teen_1",
        "Berm_1a",
        "Berm_1b",
        "Kruin_1",
        "Kruin_2",
        "Berm_2a",
        "Berm_2b",
        "Teen_2",
        "Weg_2",
        "Sloot_2",
        "MV_bui",
    ],
)

# note that the parameters can be overridden if you add the soil code to the SOILS_WITH_K_ZAND list
SOILPARAMETERS = {
    "AA": {
        "k_hor": 5,
        "k_ver": 5,
        "color": "#b5aeae",
    },
    "AV": {
        "k_hor": 1e-3,
        "k_ver": 1e-3,
        "color": "#b5aeae",
    },
    "BV": {
        "k_hor": 1e-3,
        "k_ver": 1e-3,
        "color": "#996d22",
    },
    "CK": {
        "k_hor": 1e-3,
        "k_ver": 1e-3,
        "color": "#a2e69c",
    },
    "CK14": {
        "k_hor": 1e-3,
        "k_ver": 1e-3,
        "color": "#a2e69c",
    },
    "CK16": {
        "k_hor": 1e-3,
        "k_ver": 1e-3,
        "color": "#38ab6c",
    },
    "CK18": {
        "k_hor": 1e-3,
        "k_ver": 1e-3,
        "color": "#1df00a",
    },
    "CZ": {
        "k_hor": 1e-2,
        "k_ver": 1e-2,
        "color": "#b5aeae",
    },
    "DK": {
        "k_hor": 1e-3,
        "k_ver": 1e-3,
        "color": "#73c99a",
    },
    "DK14": {
        "k_hor": 1e-3,
        "k_ver": 1e-3,
        "color": "#73c99a",
    },
    "DK16": {
        "k_hor": 1e-3,
        "k_ver": 1e-3,
        "color": "#098742",
    },
    "DK18": {
        "k_hor": 1e-3,
        "k_ver": 1e-3,
        "color": "#b5aeae",
    },
    "DZ": {
        "k_hor": 5,
        "k_ver": 5,
        "color": "#07e86c",
    },
    "HV": {
        "k_hor": 1e-3,
        "k_ver": 1e-3,
        "color": "#c29904",
    },
    "Kla": {
        "k_hor": 1e-2,
        "k_ver": 1e-2,
        "color": "#1b6936",
    },
    "PL": {
        "k_hor": 2,
        "k_ver": 2,
        "color": "#eaff00",
    },
    "PLa": {
        "k_hor": 2,
        "k_ver": 2,
        "color": "#eaff00",
    },
    "ZA": {
        "k_hor": 2,
        "k_ver": 2,
        "color": "#d8e35f",
    },
    "ZAa": {
        "k_hor": 2,
        "k_ver": 2,
        "color": "#d8e35f",
    },
}
