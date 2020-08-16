import json
import logging
import zeep

from zeep.cache import InMemoryCache
from zeep.transports import Transport

errors = logging.getLogger('errors')


class SamanService:
    transport = Transport(cache=InMemoryCache())

    def verify_saman(self, order, data):
        reference_id = data.get("RefNum", "")
        order.log = json.dumps(data)
        properties_data = json.loads(order.properties)
        purchase_verified = False

        if data.get("State", "") != "OK":
            properties_data.update({"result_code": data.get("State", "")})

        else:
            properties_data.update(
                {
                    "result_code": data.get("State", ""),
                    "user_reference": data.get("TRACENO", "")

                }
            )

            try:
                wsdl = order.service_gateway.gateway.properties.get('verify_url'),
                mid = order.service_gateway.gateway.properties.get('merchant_id'),
                client = zeep.Client(wsdl=wsdl, transport=self.transport)
                res = client.service.verifyTransaction(str(reference_id), str(mid))
                if int(res) == order.price * 10:
                    purchase_verified = True
            except Exception as e:
                errors.error(str(e))
        order.properties = properties_data
        order.is_paid = purchase_verified
        order.reference_id = reference_id
        order.save()
        return purchase_verified
