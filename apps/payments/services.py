import json
import logging
import os

import requests
import zeep
from datetime import datetime
from django.core.cache import caches
from django.conf import settings

from zeep.cache import InMemoryCache
from zeep.transports import Transport

logger = logging.getLogger(__name__)


class BazaarService(object):
    @staticmethod
    def get_access_token(gateway):
        cache = caches['payments']
        access_code = cache.get('bazaar_access_code')
        endpoint = 'https://pardakht.cafebazaar.ir/devapi/v2/auth/token/'
        if access_code is None and cache.get('bazaar_token') is None:
            data = {
                "grant_type": "authorization_code",
                "code": gateway.properties.get('auth_code'),
                "redirect_uri": gateway.properties.get('redirect_uri'),
                "client_id": gateway.properties.get('client_id'),
                "client_secret": gateway.properties.get('client_secret')
            }
            response = requests.post(endpoint, data=data)
            logger.info(f'getting bazaar token: {response.text}')
            response.raise_for_status()
            res_json = response.json()
            access_code = res_json.get('access_token')
            cache.set('bazaar_access_code', access_code)
            logger.info('set bazzar access code was successful')
            cache.set('bazaar_token', json.dumps(res_json), 60 * 60 * 3600)
            return access_code
        elif access_code is None and cache.get('bazaar_token') is not None:
            refresh_token = json.loads(cache.get('bazaar_token')).get('refresh_token')
            data = {
                "grant_type": "refresh_token",
                "client_id": gateway.properties.get('client_id'),
                "client_secret": gateway.properties.get('client_secret'),
                "refresh_token": refresh_token
            }
            response = requests.post(endpoint, data=data)
            res_json = response.json()
            access_code = res_json.get('access_token')
            cache.set('bazaar_access_code', access_code)
            logger.info('refreshed bazzar access code was successful')
            return access_code
        else:
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
                logger.warning(
                    f"bazaar purchase were not verified for order {order.id} with response : {response.text}")
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
                wsdl = order.service_gateway.saman_verify_url
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

    def request_mellat(self, order, callback_url):
        try:
            wsdl = order.service_gateway.mellat_wsdl
            terminal_id = order.service_gateway.properties.get('merchant_id')
            username = order.service_gateway.properties.get('username')
            password = order.service_gateway.properties.get('password')
            order_id = order.updated_time.strftime('%y%m%d%H%M%S')
            amount = order.price * 10
            local_date = datetime.now().strftime("%Y%m%d")
            local_time = datetime.now().strftime("%H%M%S")
            ref_id = order.transaction_id
            callback_url = callback_url
            payer_id = order.service.id
            order.properties['order_id'] = order_id
            client = zeep.Client(wsdl=wsdl, transport=self.transport)
            res = client.service.bpPayRequest(
                terminal_id, str(username), str(password),
                order_id, amount, local_date,
                local_time, str(ref_id), callback_url, payer_id
            )
            if res.split(',')[0] == '0':
                order.reference_id = res.split(',')[1]
        except Exception as e:
            logger.error(str(e))

        order.save()
        return order.reference_id

    def verify_mellat(self, order, data):
        reference_id = data.get("SaleReferenceId", "")
        order.log = json.dumps(data)
        purchase_verified = False
        try:
            if int(data['ResCode']) == 0 and int(data['FinalAmount']) == order.price * 10:
                wsdl = order.service_gateway.mellat_wsdl
                terminal_id = order.service_gateway.properties.get('merchant_id')
                username = order.service_gateway.properties.get('username')
                password = order.service_gateway.properties.get('password')
                order_id = data.get('SaleOrderId')
                client = zeep.Client(wsdl=wsdl, transport=self.transport)
                res = client.service.bpVerifyRequest(
                    terminal_id, str(username), str(password),
                    order_id, order.properties['order_id'], reference_id
                )
                logger.info(f'verifying payment {order.transaction_id} result: {res}')
                if int(res) == 0:
                    res_settle = client.service.bpSettleRequest(
                        terminal_id, str(username), str(password),
                        order_id, order.properties['order_id'], reference_id
                    )
                    logger.info(f'settling payment {order.transaction_id} result: {res}')
                    if int(res_settle) == 0:
                        logger.info(f'order {order.transaction_id} settle payment done. {res_settle}')
                        purchase_verified = True

            else:
                logger.warning(f'transaction is not valid for order {order.transaction_id}')

        except Exception as e:
            logger.error(str(e))

        order.is_paid = purchase_verified
        order.properties['SaleReferenceId'] = reference_id
        order.save()
        logger.info(f'verifing order {order.id} done with status :{purchase_verified}')
