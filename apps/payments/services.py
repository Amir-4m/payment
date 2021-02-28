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
    TOKEN_URL = "https://pardakht.cafebazaar.ir/devapi/v2/auth/token/"
    VERIFY_URL = "https://pardakht.cafebazaar.ir/devapi/v2/api/"

    def get_access_token(self, service_gateway, redirect_url):
        cache = caches['payments']
        _access_token_key = f'bazaar_access_code_{service_gateway.id}'

        sg_properties = service_gateway.properties

        access_code = cache.get(_access_token_key)
        if access_code is None:
            token_data = sg_properties.get('token_data') or {}
            refresh_token = token_data.get('refresh_token')
            if refresh_token:
                data = {
                    "grant_type": "refresh_token",
                    "refresh_token": refresh_token,
                    "client_id": sg_properties.get('client_id'),
                    "client_secret": sg_properties.get('client_secret'),
                }

            else:
                data = {
                    "grant_type": "authorization_code",
                    "code": sg_properties.get('auth_code'),
                    "client_id": sg_properties.get('client_id'),
                    "client_secret": sg_properties.get('client_secret'),
                    "redirect_uri": redirect_url,
                }

            _r = requests.post(self.TOKEN_URL, data=data)
            logger.info(f'getting bazaar token, response status, {_r.status_code} response body,: {_r.text}, data: {data}')
            try:
                _r.raise_for_status()
            except requests.exceptions.HTTPError:
                token_data = {}
            else:
                token_data = _r.json()
                access_code = token_data['access_token']
                cache.set(_access_token_key, access_code, token_data.get('expires_in', 3600000))

            sg_properties.update({'token_data': token_data})

            service_gateway.properties = sg_properties
            service_gateway.save()

        return access_code

    def verify_purchase(self, order, purchase_token, redirect_url):
        purchase_verified = False
        package_name = order.properties.get('package_name')
        product_id = order.properties.get('sku')
        iab_api_path = "validate/{}/inapp/{}/purchases/{}/".format(
            package_name,
            product_id,
            purchase_token
        )
        iab_url = "{}{}".format(self.VERIFY_URL, iab_api_path)
        try:
            access_token = self.get_access_token(order.service_gateway, redirect_url)
            headers = {'Authorization': access_token}
            response = requests.get(iab_url, headers=headers)
            order.log = response.json()
            response.raise_for_status()
            purchase_verified = True
        except requests.exceptions.HTTPError as e:
            logger.warning(f"bazaar purchase not verified for order {order.id} with status: {e.response.status_code}, response : {e.response.text}")
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
