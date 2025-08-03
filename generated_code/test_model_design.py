from model_design import build_model

def test_build_model():
    """Test model building."""
    try:
        model = build_model((10, 1))
        assert model is not None
        assert len(model.layers) > 0
    except Exception:
        pytest.fail("Model could not be built.")
python
