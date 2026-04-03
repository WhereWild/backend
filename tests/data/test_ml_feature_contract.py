from scripts.machine_learning.feature_contract import classify_catalog_layer_group


def test_classify_catalog_layer_group_uses_catalog_categories_directly() -> None:
    assert classify_catalog_layer_group(layer_id="clt", category_name="bioclimate") == "bioclimate"
    assert classify_catalog_layer_group(layer_id="lithology", category_name="landclass") == "landclass"
    assert classify_catalog_layer_group(layer_id="landform", category_name="terrain") == "terrain"
    assert classify_catalog_layer_group(layer_id="bio_1", category_name="bioclimate") == "bioclimate"
    assert classify_catalog_layer_group(layer_id="landcover", category_name="landclass") == "landclass"
    assert classify_catalog_layer_group(layer_id="temperature_2m", category_name="temporal") == "temporal"
