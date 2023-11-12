from objects.crosssection import CrosssectionPointType

BOTTOM_OFFSET = 10.0  # if we have no bottom on the soilprofile we use the top of the deepest layer minus this offset
LIMIT_LEFT = -50.0  # limit the crosssection to the given value on the left side
LIMIT_RIGHT = 50.0  # limit the crosssection to the given value on the right side

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

SOILCOLORS = {
    "AA": "#b5aeae",
    "AV": "#b5aeae",
    "BV": "#996d22",
    "CK": "#a2e69c",
    "CK14": "#a2e69c",
    "CK16": "#5db854",
    "CK18": "#17800e",
    "CZ": "#1df00a",
    "DK": "#73c99a",
    "DK14": "#73c99a",
    "DK16": "#38ab6c",
    "DK18": "#098742",
    "DZ": "#07e86c",
    "HV": "#c29904",
    "Kla": "#1b6936",
    "PL": "#eaff00",
    "PLa": "#eaff00",
    "ZA": "#d8e35f",
    "ZAa": "#d8e35f",
}
