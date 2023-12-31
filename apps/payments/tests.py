# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import json
import logging
from urllib.parse import urlencode

from django.http import QueryDict
from django.test import TestCase
from django.utils.encoding import force_text
from django.urls import reverse
from django.test.client import RequestFactory

from rest_framework import status
from rest_framework.exceptions import ValidationError as RestValidationError
from django.core.exceptions import ValidationError

from rest_framework.test import APITestCase, APIClient
from mock import patch

from apps.payments.api.serializers import OrderSerializer, PurchaseSerializer, VerifySerializer
from apps.payments.models import Order, ServiceGateway
from apps.services.models import Service


class PaymentBaseAPITestCase(APITestCase):
    fixtures = ['payment', 'service']

    def setUp(self):
        self.service = Service.objects.first()
        self.client = APIClient()
        self.request = RequestFactory()
        self.request.auth = {'service': self.service}
        self.client.credentials(HTTP_AUTHORIZATION='Token ' + str(self.service.secret_key))
        logging.disable(logging.CRITICAL)

    def tearDown(self):
        logging.disable(logging.NOTSET)


class GatewayAPITestCase(PaymentBaseAPITestCase):

    def test_get_gateway(self):
        url = reverse('servicegateway-list')
        response = self.client.get(url, format='application/json')
        response_data = json.loads(force_text(response.content))

        gw = self.service.service_gateways.first()
        expected_data = {
            'id': gw.id,
            'display_name': gw.display_name,
            'code': gw.code,
            'image_url': 'http://testserver' + gw.image.url
        }

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn(expected_data, response_data)


class BazaarViewTestCase(TestCase):
    view_name = 'bazaar-token'

    def test_get(self):
        url = reverse(self.view_name, kwargs={'gateway_id': 4})
        response = self.client.get(url)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.content, b'')


class GetBankViewTestCase(TestCase):
    fixtures = ['payment', 'service']
    view_name = 'bank-gateway'

    def test_get_invalid_params(self):
        url = reverse(self.view_name, kwargs={'order_id': 5})
        response = self.client.get(url)

        self.assertEqual(response.status_code, 404)

    def test_get_invalid_order(self):
        url = reverse(self.view_name, kwargs={'order_id': 55})
        params = {
            'order': 123,
        }
        response = self.client.get(url, data=params)

        self.assertEqual(response.status_code, 404)

    def test_get_valid_params(self):
        order = Order.objects.get(service_reference='1')
        url = reverse(self.view_name, kwargs={'order_id': order.id})
        params = {
            'order': order.id,
        }

        html = f"""
        <input type="hidden" name="ResNum" value="{order.transaction_id}"/>
        <input type="hidden" name="MID" value="{order.service_gateway.properties['merchant_id']}"/>
        <input type="hidden" name="RedirectURL" value="http://testserver/payments/verify/SAMAN/"/>
        <input type="hidden" name="Amount" value="{order.price * 10}"/>
        <input type="hidden" name="CellNumber" value=""/>
        <input type="hidden" name="language" value="fa"/>
        

        """

        response = self.client.get(url, data=params)
        self.assertEqual(response.status_code, 200)
        self.assertInHTML(html, response.content.decode())


class VerifyViewTestCase(TestCase):
    fixtures = ['payment', 'service']
    view_name = 'verify-payment'

    def test_post_no_transaction_id(self):
        url = reverse(self.view_name, kwargs={'gateway_code': ServiceGateway.FUNCTION_SAMAN})
        response = self.client.post(url)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.content, b'')

    def test_post_invalid_order(self):
        url = reverse(self.view_name, kwargs={'gateway_code': ServiceGateway.FUNCTION_SAMAN})
        response = self.client.post(url + '?transaction_id=cd61b980-649c-42fb-877f-0614054f56b6')

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.content, b'')

    def test_post_order_paid_not_none(self):
        url = reverse(self.view_name, kwargs={'gateway_code': ServiceGateway.FUNCTION_SAMAN})
        response = self.client.post(url + '?transaction_id=cd61b980-6c3c-42fb-877f-0614054f56b6')

        self.assertEqual(response.status_code, 404)

    def test_post_order_invalid_gateway(self):
        url = reverse(self.view_name, kwargs={'gateway_code': ServiceGateway.FUNCTION_SAMAN})
        response = self.client.post(url + '?transaction_id=cd61b980-6c5c-42fb-877f-0614054f56b6')

        self.assertEqual(response.status_code, 302)

    def test_post_invalid_uuid_form(self):
        url = reverse(self.view_name, kwargs={'gateway_code': ServiceGateway.FUNCTION_SAMAN})
        response = self.client.post(url + '?transaction_id=test')

        self.assertEqual(response.status_code, 400)

    @patch('apps.payments.services.SamanService.verify_saman')
    def test_post_valid_order(self, mock_method):
        mock_method.return_value = True
        order = Order.objects.get(transaction_id='cd61b980-6c9c-42fb-877f-0614054f56b6')
        url = reverse(self.view_name, kwargs={'gateway_code': order.service_gateway.code})
        response = self.client.post(url + f'?transaction_id={order.transaction_id}')
        order.refresh_from_db()
        params = {
            'purchase_verified': True,
            'transaction_id': order.transaction_id,
            'refNum': order.properties.get("RefNum") or order.reference_id
        }

        self.assertEqual(response.status_code, 302)
        self.assertRedirects(
            response,
            order.properties.get('redirect_url') + '?' + urlencode(params),
            fetch_redirect_response=False
        )
        mock_method.assert_called_once_with(
            order=order, data=QueryDict()
        )


class OrderAPITestCase(PaymentBaseAPITestCase):

    def test_post_order_valid_data(self):
        url = reverse('order-list')
        data = {
            'gateway': ServiceGateway.objects.filter(service=self.service).first().id,
            'service_reference': 'hello',
            'price': 1000,
            'redirect_url': 'http://www.test.com'
        }
        response = self.client.post(url, data=data, format='json')
        response_data = json.loads(force_text(response.content))
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(
            Order.objects.filter(
                price=data['price'],
                service=self.service,
                service_reference='hello').exists()
        )

    def test_post_order_invalid_gateway(self):
        url = reverse('order-list')
        data = {
            'service_gateway': ServiceGateway.objects.get(id=4).id,
            'price': 1000,
        }
        response = self.client.post(url, data=data, format='json')

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertRaisesMessage(
            ValidationError,
            "Service gateway does not exists!",
        )

    def test_post_order_unavailable_gateway(self):
        url = reverse('order-list')
        data = {
            'service_gateway': ServiceGateway.objects.get(id=2).id,
            'price': 1000,
        }
        response = self.client.post(url, data=data, format='json')

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertRaisesMessage(
            ValidationError,
            "Gateway is not available!",
        )


class OrderModelTestCase(PaymentBaseAPITestCase):
    def test_order_properties(self):
        instance = Order(
            service_gateway_id=1,
            price=1000,
            properties={'redirect_url': 'www.rdu.com'}
        )
        self.assertIsNone(instance.clean())
        self.assertIsNotNone(instance.properties)

    def test_order_properties_none(self):
        instance = Order(
            service_gateway_id=1,
            price=1000,
        )
        self.assertRaisesMessage(
            ValidationError,
            "redirect_url should be provided in gateway properties!",
            instance.clean
        )


class OrderSerializerTestCase(PaymentBaseAPITestCase):

    def test_validate_gateway(self):
        data = {
            'gateway': ServiceGateway.objects.first(),
            'price': 1000,
            'service_reference': 'hello'
        }
        serializer = OrderSerializer(data=data, context={'request': self.request})

        self.assertEqual(serializer.validate_gateway(data['gateway']), data['gateway'])

    def test_validate_gateway_invalid_data(self):
        data = {
            'gateway': ServiceGateway.objects.last(),
            'price': 1000,
            'service_reference': 'hello'
        }
        serializer = OrderSerializer(data=data, context={'request': self.request})

        self.assertRaisesMessage(
            RestValidationError,
            'service and gateway does not match!',
            serializer.validate_gateway,
            obj=data['gateway']
        )

    def test_validate(self):
        data = {
            'gateway': ServiceGateway.objects.last(),
            'price': 1000,
            'service_reference': 'hello'
        }

        serializer = OrderSerializer(data=data, context={'request': self.request})

        self.assertEqual(serializer.validate(data), data)

    def test_validate_invalid_data(self):
        data = {
            'gateway': ServiceGateway.objects.first(),
            'price': 1000,
            'service_reference': 'testref'
        }

        serializer = OrderSerializer(data=data, context={'request': self.request})

        self.assertRaisesMessage(
            RestValidationError,
            'Order with this service and service reference has been paid already!',
            serializer.validate,
            data
        )


class PurchaseAPITestCase(PaymentBaseAPITestCase):
    def test_gateway_bank(self):
        url = reverse('purchase-gateway')
        data = {
            'gateway': ServiceGateway.objects.filter(service=self.service).first().id,
            'order': Order.objects.first().id,
        }
        response = self.client.post(url, data=data, format='json')
        response_data = json.loads(force_text(response.content))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            response_data,
            {'gateway_url': f'http://testserver/payments/gateway-bank/{data["order"]}/'}
        )

    def test_gateway_psp(self):
        url = reverse('purchase-gateway')
        data = {
            'gateway': ServiceGateway.objects.filter(service=self.service, id=3).first().id,
            'order': Order.objects.get(id=2).id,
        }
        response = self.client.post(url, data=data, format='json')
        response_data = json.loads(force_text(response.content))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            response_data,
            {'order': data['order'], 'gateway': data['gateway']}
        )

    @patch('apps.payments.services.BazaarService.verify_purchase')
    def test_verify(self, mock_method):
        mock_method.return_value = False
        url = reverse('purchase-verify')
        order = Order.objects.get(id=2)
        data = {
            'purchase_token': self.id(),
            'order': order.id,
        }
        response = self.client.post(url, data=data, format='json')
        response_data = json.loads(force_text(response.content))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            response_data,
            {'purchase_verified': False}
        )
        mock_method.assert_called_once_with(
            order=Order.objects.get(id=data['order']),
            purchase_token=self.id(),
            redirect_url=f'http://testserver/payments/bazaar-token/{order.service_gateway.id}/'
        )


class PurchaseSerializerTestCase(PaymentBaseAPITestCase):
    def test_validate_gateway(self):
        data = {
            'gateway': ServiceGateway.objects.first(),
            'order': Order.objects.first()
        }
        serializer = PurchaseSerializer(data=data, context={'request': self.request})

        self.assertEqual(serializer.validate_gateway(data['gateway']), data['gateway'])

    def test_validate_gateway_invalid_data(self):
        data = {
            'gateway': ServiceGateway.objects.last(),
            'order': Order.objects.last()
        }
        serializer = PurchaseSerializer(data=data, context={'request': self.request})

        self.assertRaisesMessage(
            RestValidationError,
            'service and gateway does not match!',
            serializer.validate_gateway,
            obj=data['gateway']
        )

    def test_validate_order(self):
        order = Order.objects.first()
        data = {
            'gateway': ServiceGateway.objects.first(),
            'order': order.service_reference
        }
        serializer = PurchaseSerializer(data=data, context={'request': self.request})

        self.assertEqual(serializer.validate_order(data['order']), order)

    def test_validate_order_invalid_data(self):
        data = {
            'gateway': ServiceGateway.objects.first(),
            'order': Order.objects.get(pk=4).service_reference
        }
        serializer = PurchaseSerializer(data=data, context={'request': self.request})

        self.assertRaisesMessage(
            RestValidationError,
            'order and service does not match!',
            serializer.validate_order,
            value=data['order']
        )

    def test_validate(self):
        data = {
            'gateway': ServiceGateway.objects.first(),
            'order': Order.objects.first()
        }
        serializer = PurchaseSerializer(data=data, context={'request': self.request})

        self.assertEqual(serializer.validate(data), data)


class VerifySerializerTestCase(PaymentBaseAPITestCase):
    def test_validate_order(self):
        data = {
            'purchase_token': self.id(),
            'order': Order.objects.get(id=2).service_reference
        }
        serializer = VerifySerializer(data=data, context={'request': self.request})

        self.assertEqual(serializer.validate_order(data['order']), Order.objects.get(id=2))

    def test_validate_order_invalid_service(self):
        data = {
            'purchase_token': self.id(),
            'order': Order.objects.get(id=4).service_reference
        }
        serializer = VerifySerializer(data=data, context={'request': self.request})

        self.assertRaisesMessage(
            RestValidationError,
            'order and service does not match!',
            serializer.validate_order,
            value=data['order']
        )

    def test_validate_order_invalid_gateway(self):
        data = {
            'purchase_token': self.id(),
            'order': Order.objects.first().service_reference
        }
        serializer = VerifySerializer(data=data, context={'request': self.request})

        self.assertRaisesMessage(
            RestValidationError,
            'invalid gateway!',
            serializer.validate_order,
            value=data['order']
        )
