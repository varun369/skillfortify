"""Semantic Kernel plugin loaded from an OpenAPI specification.

Fixture exercises detection of add_plugin_from_openapi calls and
kernel.add_plugin registrations with external spec references.
"""

from semantic_kernel import Kernel
from semantic_kernel.connectors.openapi_plugin import OpenAPIPlugin

kernel = Kernel()

# Register an OpenAPI-based plugin from a local spec file.
kernel.add_plugin_from_openapi(
    "pet_store",
    "https://petstore.swagger.io/v2/swagger.json",
)

# Register another OpenAPI plugin from a local YAML file.
kernel.add_plugin_from_openapi("payments", "openapi/payments.yaml")
