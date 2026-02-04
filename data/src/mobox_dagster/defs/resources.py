"""Resource definitions for the mobox Dagster project."""
from dagster import EnvVar
from dagster_weaviate import LocalConfig, WeaviateResource


def weaviate_resource() -> WeaviateResource:
    """Function to create WeaviateResource from environment variables."""
    weaviate_host = EnvVar("WEAVIATE_HOST").get_value(default="weaviate")
    weaviate_port = int(EnvVar("WEAVIATE_PORT").get_value(default="9000"))
    weaviate_grpc_port = int(EnvVar("WEAVIATE_GRPC_PORT").get_value(default="50051"))
    return WeaviateResource(
        connection_config=LocalConfig(
            host=weaviate_host,
            port=weaviate_port,
            grpc_port=weaviate_grpc_port,
        )
    )