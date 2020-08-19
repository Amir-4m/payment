# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import json
import logging

from django.http import QueryDict
from django.test import TestCase
from django.utils.encoding import force_text
from django.urls import reverse
from django.test.client import RequestFactory

from rest_framework import status
from rest_framework.exceptions import ValidationError
from django.core.exceptions import ValidationError

from rest_framework.test import APITestCase, APIClient
from mock import patch

from apps.payments.models import Gateway, Order
from apps.services.models import Service

from .services import SamanService


class PaymentBaseAPITestCase(APITestCase):
    fixtures = ['payment', 'service']

    def setUp(self):
        self.service = Service.objects.first()
        self.client = APIClient()
        self.request = RequestFactory()
        self.client.credentials(HTTP_AUTHORIZATION='Token ' + str(self.service.uuid))
        logging.disable(logging.CRITICAL)

    def tearDown(self):
        logging.disable(logging.NOTSET)


class GatewayAPIAPITestCase(PaymentBaseAPITestCase):

    def test_get_gateway(self):
        url = reverse('gateway-list')
        response = self.client.get(url, format='application/json')
        response_data = json.loads(force_text(response.content))

        gw = self.service.gateways.first()
        expected_data = {'id': gw.id, 'display_name': gw.display_name, 'image_url': gw.image.url}

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn(expected_data, response_data)


class GatewayModelAPITestCase(PaymentBaseAPITestCase):

    def test_gateway_bank_properties(self):
        instance = Gateway(
            display_name='test',
            title='test',
            code=Gateway.FUNCTION_SAMAN,
            properties={
                "verify_url": "test.com",
                "gateway_url": "test.com/verify/",
                "merchant_id": "1234"
            }
        )

        self.assertIsNone(instance.clean())

    def test_gateway_bank_invalid_properties(self):
        instance = Gateway(
            display_name='test',
            title='test',
            code=Gateway.FUNCTION_SAMAN,
            properties={
                "not": "test.com",
                "valid": "test.com/verify/",
                "keys": "1234"
            }
        )

        self.assertRaisesMessage(
            ValidationError,
            "verify_url should be provided in gateway properties!",
            instance.clean

        )

    def test_gateway_psp__properties(self):
        instance = Gateway(
            display_name='test',
            title='test',
            code=Gateway.FUNCTION_BAZAAR,
            properties={
                "auth_code": "test.com",
                "client_id": "12345",
                "redirect_uri": "1234",
                "client_secret": '12345'
            }
        )

        self.assertIsNone(instance.clean())

    def test_gateway_psp_invalid_properties(self):
        instance = Gateway(
            display_name='test',
            title='test',
            code=Gateway.FUNCTION_BAZAAR,
            properties={
                "not": "test.com",
                "valid": "test.com/verify/",
                "keys": "1234"
            }
        )

        self.assertRaisesMessage(
            ValidationError,
            "auth_code should be provided in gateway properties!",
            instance.clean

        )


class BazaarViewTestCase(TestCase):
    view_name = 'bazaar-token'

    def test_get(self):
        url = reverse(self.view_name)
        response = self.client.get(url)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.content, b'')


class PaymentViewTestCase(TestCase):
    fixtures = ['payment', 'service']
    view_name = 'payment-gateway'

    def test_get_invalid_params(self):
        url = reverse(self.view_name)
        response = self.client.get(url)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.content, b'')

    def test_get_invalid_gateway(self):
        url = reverse(self.view_name)
        params = {
            'invoice_number': 'test',
            'gateway': 5,
            'service': '0178f792-10e2-42ff-9d00-9e906893d2aa'
        }
        response = self.client.get(url, data=params)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.content, b'')

    def test_get_invalid_order(self):
        url = reverse(self.view_name)
        params = {
            'invoice_number': '0178f792-10e2-42ff-9d00-9e906893d2aa',
            'gateway': 1,
            'service': '0178f792-10e2-42ff-9d00-9e906893d2aa'
        }
        response = self.client.get(url, data=params)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.content, b'')

    def test_get_valid_params(self):
        url = reverse(self.view_name)
        gateway = Gateway.objects.get(id=1)
        order = Order.objects.get(invoice_number='cd61b980-6c9c-42fb-877f-0614054f56b6')
        service = Service.objects.first()
        params = {
            'invoice_number': order.invoice_number,
            'gateway': gateway.id,
            'service': service.uuid
        }

        html = f"""
        <input type="hidden" name="MID" value="{gateway.properties['merchant_id']}"/>
        <input type="hidden" name="ResNum" value="{order.invoice_number}"/>
        <input type="hidden" name="Amount" value="{order.price * 10}"/>
        <input type="hidden" name="AdditionalData1" value=""/>
        <input type="hidden" name="RedirectURL" value="http://testserver/payments/gateway/"/>
        <input type="hidden" name="CellNumber" value=""/>
        <input type="hidden" name="language" value="fa"/>
        <input type="hidden" name="ResNum1" value="fastcharge"/>
        

        """

        response = self.client.get(url, data=params)
        self.assertEqual(response.status_code, 200)
        self.assertInHTML(html, response.content.decode())

    def test_post_invalid_params(self):
        url = reverse(self.view_name)
        response = self.client.post(url)
        response_data = json.loads(force_text(response.content))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response_data, {'payment_status': False, 'data': {}})

    def test_post_invalid_order(self):
        url = reverse(self.view_name)
        response = self.client.post(url + '?invoice_number=cd61b980-649c-42fb-877f-0614054f56b6')
        response_data = json.loads(force_text(response.content))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response_data, {'payment_status': False, 'data': {}})

    def test_post_invalid_uuid_form(self):
        url = reverse(self.view_name)
        response = self.client.post(url + '?invoice_number=test')
        response_data = json.loads(force_text(response.content))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response_data, {'payment_status': False, 'data': {}})

    @patch('apps.payments.services.SamanService.verify_saman')
    def test_post_valid_order(self, mock_method):
        mock_method.return_value = True
        url = reverse(self.view_name)
        order = Order.objects.get(invoice_number='cd61b980-6c9c-42fb-877f-0614054f56b6')
        response = self.client.post(url + f'?invoice_number={order.invoice_number}')
        response_data = json.loads(force_text(response.content))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response_data, {'payment_status': True, 'data': {}})
        mock_method.assert_called_once_with(
            order=order, data=QueryDict()
        )

    def test_post_valid_order_psp_invalid_token(self, ):
        url = reverse(self.view_name)
        order = Order.objects.get(invoice_number='21877ef0-47fe-4cc7-8057-83fc0ee73416')
        response = self.client.post(url + f'?invoice_number={order.invoice_number}', data={})
        response_data = json.loads(force_text(response.content))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response_data, {'error': "purchase_token is required!"})

    @patch('apps.payments.services.BazaarService.verify_purchase')
    def test_post_valid_order_psp(self, mock_method):
        mock_method.return_value = True
        url = reverse(self.view_name)
        order = Order.objects.get(invoice_number='21877ef0-47fe-4cc7-8057-83fc0ee73416')
        response = self.client.post(url + f'?invoice_number={order.invoice_number}', data={'purchase_token': '1'})
        response_data = json.loads(force_text(response.content))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response_data, {'payment_status': True, 'data': {'purchase_token': '1'}})
        mock_method.assert_called_once_with(
            order=order, purchase_token='1'
        )

    def test_post_valid_order_invalid_gateway(self):
        url = reverse(self.view_name)
        order = Order.objects.get(invoice_number='21477ef0-47fe-4cc7-8057-83fc0ee73416')
        response = self.client.post(url + f'?invoice_number={order.invoice_number}', data={})
        response_data = json.loads(force_text(response.content))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response_data, {'payment_status': True, 'data': {}})


class OrderAPIAPITestCase(PaymentBaseAPITestCase):

    def test_post_order_valid_data(self):
        url = reverse('order-list')
        data = {
            'service_gateway': Gateway.objects.filter(services=self.service).first().id,
            'price': 1000,
        }
        response = self.client.post(url, data=data, format='json')
        response_data = json.loads(force_text(response.content))

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(
            Order.objects.filter(invoice_number=response_data['invoice_number'], price=data['price']).exists()
        )

    def test_post_order_invalid_gateway(self):
        url = reverse('order-list')
        data = {
            'service_gateway': Gateway.objects.get(id=4).id,
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
            'service_gateway': Gateway.objects.get(id=2).id,
            'price': 1000,
        }
        response = self.client.post(url, data=data, format='json')

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertRaisesMessage(
            ValidationError,
            "Gateway is not available!",
        )


class OrderModelCaseAPI(PaymentBaseAPITestCase):
    def test_order_properties(self):
        instance = Order(
            service_gateway_id=1,
            price=1000,
        )
        self.assertIsNone(instance.clean())
        self.assertIsNotNone(instance.properties)

    def test_order_properties_none(self):
        instance = Order(
            service_gateway_id=1,
            price=1000,
            properties=None
        )
        self.assertIsNone(instance.clean())
        self.assertIsNotNone(instance.properties)
