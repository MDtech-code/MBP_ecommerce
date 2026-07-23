# apps/payments/gateways/registry.py
from __future__ import annotations

"""
Gateway registry — maps gateway name strings to client classes.

Adding a new gateway:
    1. Create apps/payments/gateways/newgateway.py
       implementing BaseGatewayClient.
    2. Add one line to GATEWAY_REGISTRY below.
    3. Add gateway credentials to settings.
    4. Zero changes to PaymentService, views, or tasks.

Removing a gateway:
    1. Remove the registry line.
    2. Delete the gateway file.
    3. Zero changes elsewhere.

get_gateway_client() instantiates the client on every call —
no singleton state. Gateway clients are stateless except for
reading credentials from settings in __init__.

Only ONLINE gateways are in this registry.
COD is handled entirely by the logistics workflow — never
routed through PaymentService.initiate_payment().
"""

import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from apps.payments.gateways.base import BaseGatewayClient

from apps.payments.gateways.jazzcash  import JazzCashGatewayClient
from apps.payments.gateways.easypaisa import EasypaisaGatewayClient
from apps.payments.gateways.safepay   import SafepayGatewayClient

logger = logging.getLogger("apps.payments")

# Maps PaymentTransaction.Gateway string values to client classes.
# Keys must match PaymentTransaction.Gateway choice values exactly.
GATEWAY_REGISTRY: dict[str, type["BaseGatewayClient"]] = {
    "jazzcash":  JazzCashGatewayClient,
    "easypaisa": EasypaisaGatewayClient,
    "safepay":   SafepayGatewayClient,
}

# Gateways that are valid for online payment initiation.
# COD and RAAST are excluded — they are not customer-initiated
# online payment flows handled by PaymentService.
ONLINE_GATEWAYS: frozenset[str] = frozenset(GATEWAY_REGISTRY.keys())


def get_gateway_client(gateway_name: str) -> "BaseGatewayClient | None":
    """
    Return an instantiated gateway client for the given gateway name.

    Returns None if the gateway is not in the registry —
    caller is responsible for raising DomainError.

    Args:
        gateway_name: PaymentTransaction.Gateway string value.

    Returns:
        Instantiated BaseGatewayClient subclass, or None.
    """
    client_class = GATEWAY_REGISTRY.get(gateway_name)
    if client_class is None:
        logger.warning(
            "get_gateway_client: unknown gateway '%s' — "
            "not in GATEWAY_REGISTRY.",
            gateway_name,
        )
        return None

    return client_class()