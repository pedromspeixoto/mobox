from dagster import Definitions, load_assets_from_modules

from mobox_dagster.defs.resources import weaviate_resource
from mobox_dagster.defs import assets

# Load all assets from the assets module
all_assets = load_assets_from_modules([assets])

defs = Definitions(
    assets=all_assets,
    resources={
        "weaviate": weaviate_resource(),
    },
)
