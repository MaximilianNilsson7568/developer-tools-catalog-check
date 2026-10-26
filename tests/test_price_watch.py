from src.price_watch import CatalogCheck, should_publish


def test_incomplete_or_higher_observation_stays_quiet():
    assert should_publish(CatalogCheck("alpha", None, 20.0)) is False
    assert should_publish(CatalogCheck("beta", 20.0, 20.0)) is False
    assert should_publish(CatalogCheck("gamma", 19.5, 20.0)) is True
