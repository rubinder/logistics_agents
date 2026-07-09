import logistics_agents


def test_package_exposes_version():
    assert isinstance(logistics_agents.__version__, str)
    assert logistics_agents.__version__
