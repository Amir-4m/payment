from drf_yasg import openapi

ORDER_POST_DOCS = openapi.Schema(
    type=openapi.TYPE_OBJECT,
    required=['price', 'service_reference', 'is_paid', 'properties__redirect_url'],
    properties={
        'price': openapi.Schema(
            type=openapi.TYPE_INTEGER,
            description='price of the order.'
        ),
        'service_reference': openapi.Schema(
            type=openapi.TYPE_STRING,
            description='an string which refer to the order of service.'
        ),
        'is_paid': openapi.Schema(
            type=openapi.TYPE_BOOLEAN,
            description='payment status of the order'
        ),
        'properties:{redirect_url}': openapi.Schema(
            type=openapi.TYPE_STRING,
            description='url of a view from service, for redirecting bank payment result to service.',
        ),

    }
)
ORDER_POST_DOCS_RESPONSE = openapi.Schema(
    type=openapi.TYPE_OBJECT,
    properties={
        'gateway': openapi.Schema(
            type=openapi.TYPE_INTEGER,
            description='id of the active chosen gateway for this order'

        ),
        'price': openapi.Schema(
            type=openapi.TYPE_INTEGER,
            description='price of the order.'
        ),
        'service_reference': openapi.Schema(
            type=openapi.TYPE_STRING,
            description='an string which refer to the order of service.'
        ),
        'is_paid': openapi.Schema(
            type=openapi.TYPE_BOOLEAN,
            description='payment status of the order'
        ),
        'gateways': openapi.Schema(
            type=openapi.TYPE_ARRAY,
            description='list of available gateways',
            items=openapi.Schema(type=openapi.TYPE_OBJECT)
        ),

    }
)

PURCHASE_GATEWAY_DOCS = openapi.Schema(
    type=openapi.TYPE_OBJECT,
    required=['gateway', 'order'],
    properties={
        'gateway': openapi.Schema(
            type=openapi.TYPE_INTEGER,
            description='id of the gateway, chosen for the payment.',
        ),
        'order': openapi.Schema(
            type=openapi.TYPE_STRING,
            description='service_reference value that generated for the order.'
        ),

    }
)
PURCHASE_GATEWAY_DOCS_RESPONSE = openapi.Schema(
    type=openapi.TYPE_OBJECT,
    properties={
        'gateway_url (if gateway is a type of bank)': openapi.Schema(
            type=openapi.TYPE_STRING,
        ),

    }
)

PURCHASE_VERIFY_DOCS = openapi.Schema(
    type=openapi.TYPE_OBJECT,
    required=['order', 'order'],
    properties={
        'purchase_token': openapi.Schema(
            type=openapi.TYPE_INTEGER,
            description='purchase_token of the package (required if gateway in bazaar)',
        ),
        'order': openapi.Schema(
            type=openapi.TYPE_STRING,
            description='service_reference value that generated for the order.'
        ),

    }
)

PURCHASE_VERIFY_DOCS_RESPONSE = openapi.Schema(
    type=openapi.TYPE_OBJECT,
    properties={
        'purchase_verified': openapi.Schema(
            type=openapi.TYPE_BOOLEAN,
        ),

    }
)
