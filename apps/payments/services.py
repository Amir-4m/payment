import json
import logging

import requests
import zeep
from datetime import datetime
from django.core.cache import caches

from zeep.cache import InMemoryCache
from zeep.transports import Transport

logger = logging.getLogger(__name__)


class BazaarService(object):
    @staticmethod
    def get_access_token(service_gateway):
        cache = caches['payments']
        endpoint = 'https://pardakht.cafebazaar.ir/devapi/v2/auth/token/'
        _token_key = 'bazaar_token_{service_gateway.id}'
        _access_token_key = 'bazaar_access_code_{service_gateway.id}'

        access_code = cache.get(_access_token_key)
        if access_code is None:
            refresh_token = cache.get(_token_key).get('refresh_token')
            if refresh_token:
                data = {
                    "grant_type": "refresh_token",
                    "refresh_token": refresh_token,
                    "client_id": service_gateway.properties.get('client_id'),
                    "client_secret": service_gateway.properties.get('client_secret'),
                }

            else:
                data = {
                    "grant_type": "authorization_code",
                    "code": service_gateway.properties.get('auth_code'),
                    "client_id": service_gateway.properties.get('client_id'),
                    "client_secret": service_gateway.properties.get('client_secret')
                    "redirect_uri": service_gateway.properties.get('redirect_uri'),
                }

            _r = requests.post(endpoint, data=data)
            logger.info(f'getting bazaar token, response status, {_r.status_code} response body,: {_r.text}, data: {data}')
            try:
                _r.raise_for_status()
            except requests.HTTPError:
                cache.delete(_token_key)
                raise

            res = _r.json()
            access_code = res.get('access_token')

            cache.set(_access_token_key, access_code, res.get('expires_in', 3600000))
            # This cache should never be expired
            cache.set(_token_key, res, None)

        return access_code

    @staticmethod
    def verify_purchase(order, purchase_token):
        purchase_verified = False
        package_name = order.properties.get('package_name')
        product_id = order.properties.get('sku')
        iab_base_api = "https://pardakht.cafebazaar.ir/devapi/v2/api"
        iab_api_path = "validate/{}/inapp/{}/purchases/{}/".format(
            package_name,
            product_id,
            purchase_token
        )
        iab_url = "{}/{}".format(iab_base_api, iab_api_path)
        try:
            access_token = BazaarService.get_access_token(order.service_gateway)
            headers = {'Authorization': access_token}
            response = requests.get(iab_url, headers=headers)
            order.log = response.json()
            if response.status_code == 200:
                purchase_verified = True
            else:
                logger.warning(f"bazaar purchase were not verified for order {order.id} with response : {response.text}")
        except Exception as e:
            logger.error(f"bazaar purchase verification got error for order {order.id}: {e}")

        order.is_paid = purchase_verified
        order.reference_id = purchase_token
        order.save()
        return purchase_verified


class SamanService:
    transport = Transport(cache=InMemoryCache())

    def verify_saman(self, order, data):
        reference_id = data.get("RefNum", "")
        order.log = json.dumps(data)
        purchase_verified = False
        if data.get("State", "") != "OK":
            order.properties.update({"result_code": data.get("State", "")})

        else:
            order.properties.update(
                {
                    "result_code": data.get("State", ""),
                    "user_reference": data.get("TRACENO", "")

                }
            )

            try:
                wsdl = order.service_gateway.properties.get('verify_url')
                mid = order.service_gateway.properties.get('merchant_id')
                client = zeep.Client(wsdl=wsdl, transport=self.transport)
                res = client.service.verifyTransaction(str(reference_id), str(mid))
                if int(res) == order.price * 10:
                    logger.info(f'payment verified for order {order.id}: {int(res)}')
                    purchase_verified = True
                logger.warning(f'payment was not verified for order {order.id} due to : {int(res)} ')
            except Exception as e:
                logger.error(str(e))
        order.is_paid = purchase_verified
        order.reference_id = reference_id
        order.save()
        logger.info(f'verifing order {order.id} done with status :{purchase_verified}')
        return purchase_verified


class MellatService:
    transport = Transport(cache=InMemoryCache())

    def request_mellat(self, order):
        try:
            wsdl = order.service_gateway.properties.get('request_url')
            terminal_id = order.service_gateway.properties.get('merchant_id')
            username = order.service_gateway.properties.get('username')
            password = order.service_gateway.properties.get('password')
            order_id = order.updated_time.strftime('%Y%m%d%H%M')
            amount = order.price * 10
            local_date = datetime.now().strftime("%Y%m%d")
            local_time = datetime.now().strftime("%H%M%S")
            ref_id = order.transaction_id
            callback_url = order.properties['redirect_url']
            payer_id = order.service.id
            client = zeep.Client(wsdl=wsdl, transport=self.transport)
            res = client.service.bpPayRequest(
                terminal_id, str(username), str(password),
                order_id, amount, local_date,
                local_time, str(ref_id), callback_url, payer_id
            )

            if res.split(',')[0] == '0':
                order.properties['hash_code'] = res.split(',')[1]
                order.save()
                return order.properties['hash_code']
            return None
        except Exception as e:
            logger.error(str(e))

    def verify_mellat(self, order, data):
        reference_id = data.get("RefNum", "")
        order.log = json.dumps(data)
        purchase_verified = False
        try:
            wsdl = order.service_gateway.properties.get('verify_url')
            mid = order.service_gateway.properties.get('merchant_id')
            username = order.service_gateway.properties.get('username')
            password = order.service_gateway.properties.get('password')
            client = zeep.Client(wsdl=wsdl, transport=self.transport)
            res = client.service.verifyTransaction(mid, str(username), str(password), 11, 10)
            if int(res) == order.price * 10:
                purchase_verified = True
        except Exception as e:
            logger.error(str(e))
