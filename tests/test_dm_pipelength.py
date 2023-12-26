from geolib.models.dgeoflow import DGeoFlowModel
from pathlib import Path
import pytest


def test_pipe_length_from_model():
    dm = DGeoFlowModel()
    dm.parse(Path("tests/testdata/test_pipelength.flox"))
    assert 11.48 == pytest.approx(dm.output.PipeLength, 0.01)
