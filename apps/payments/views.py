import json
from urllib.parse import urlencode

from django.db import transaction
from django.http import HttpResponse, JsonResponse
from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse
from django.utils.decorators import method_decorator
from django.utils.encoding import force_text
from django.views.decorators.csrf import csrf_exempt
from django.views.generic import View

from .models import Order, Gateway
from .services import SamanService, BazaarService


def bazaar_token_view(request, *args, **kwargs):
    return HttpResponse()


class BankView(View):
    @method_decorator(csrf_exempt)
    def dispatch(self, request, *args, **kwargs):
        return super(BankView, self).dispatch(request, *args, **kwargs)

    def get(self, request):
        """
        check id and gateway and redirect user to related paying method
        """
        # check and validate parameters
        if not ('service_reference' in request.GET or 'gateway' in request.GET or 'service' in request.GET):
            return HttpResponse("")

        gateway = get_object_or_404(
            Gateway,
            id=request.GET['gateway'],
            services__secret_key=request.GET['service'],
            is_enable=True,
            properties__merchant_id__isnull=False,
            properties__gateway_url__isnull=False,
            properties__verify_url__isnull=False)

        payment = get_object_or_404(
            Order,
            service_reference=request.GET['service_reference'],
            gateway=gateway,
            service__secret_key=request.GET['service'],
            is_paid=None,
            properties__redirect_url__isnull=False
        )

        return render_bank_page(
            request,
            payment.invoice_number,
            gateway.properties.get('gateway_url'),
            gateway.properties.get('merchant_id'),
            payment.price,
            service_logo=payment.service.logo,
            service_color=payment.service.color,
            service_name=payment.service.name,
            ResNum1='fastcharge',
        )

    @transaction.atomic
    def post(self, request):
        """
        this method use for bank response posts
        """
        purchase_verified = False
        data = request.POST
        invoice_number = data.get("ResNum") or request.GET.get('invoice_number')

        if not invoice_number:
            return JsonResponse({'payment_status': purchase_verified, 'data': data})
        # check and validate parameters
        try:
            payment = Order.objects.select_related(
                'service',
                'gateway'
            ).select_for_update().get(
                invoice_number=invoice_number
            )

        except Order.DoesNotExist:
            return HttpResponse("")

        if payment.is_paid is None and payment.gateway.code == Gateway.FUNCTION_SAMAN:
            purchase_verified = SamanService().verify_saman(
                order=payment,
                data=data
            )
        else:
            purchase_verified = payment.is_paid
        params = {
            'purchase_verified': purchase_verified,
            'service_reference': payment.service_reference,
            'refNum': data.get("RefNum")
        }
        return redirect(payment.properties.get('redirect_url') + '?' + urlencode(params))


class BazaarView(View):
    @method_decorator(csrf_exempt)
    def dispatch(self, request, *args, **kwargs):
        return super(BazaarView, self).dispatch(request, *args, **kwargs)

    @transaction.atomic
    def post(self, request):
        """
        this method use for bank response posts
        """
        try:
            data = json.loads(force_text(request.body))
            service_reference = data.get('service_reference')
        except Exception:
            return JsonResponse({'error': 'json decode error occurred!'})

        if not service_reference:
            return JsonResponse({'error': 'service_reference is required!'})
        if not data.get('purchase_token'):
            return JsonResponse({'error': "purchase_token is required!"})
        # check and validate parameters
        try:
            payment = Order.objects.select_related(
                'service',
                'gateway'
            ).select_for_update().get(
                service_reference=service_reference
            )

        except Order.DoesNotExist:
            return HttpResponse("")

        if payment.is_paid is None and payment.gateway.code == Gateway.FUNCTION_BAZAAR:

            purchase_verified = BazaarService.verify_purchase(
                order=payment,
                purchase_token=data.get('purchase_token')
            )
        else:
            purchase_verified = payment.is_paid

        params = {
            'purchase_verified': purchase_verified,
            'refrence_num': payment.service_reference
        }

        return JsonResponse(params)


def render_bank_page(
        request, invoice_id, request_url,
        merchant_id, amount, phone_number='',
        service_logo=None, service_color=None, service_name=None, **kwargs
):
    """
    send parameters to a template ... template contain a form include these parameters
    this form automatically submit to bank url
    """
    render_context = {
        'service_logo': service_logo,
        'service_color': service_color,
        'service_name': service_name,
        "invoice_id": invoice_id,
        "request_url": request_url,
        "merchant_id": merchant_id,
        "redirect_url": request.build_absolute_uri(reverse('bank-gateway')),
        "amount": amount * 10,
        "extra_data": kwargs,
    }
    return render(request, 'payments/pay.html', context=render_context)
