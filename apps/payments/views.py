from django.db import transaction
from django.http import HttpResponse, JsonResponse
from django.shortcuts import render
from django.urls import reverse
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
from django.views.generic import View

from .models import ServiceGateway, Order, Gateway
from .services import SamanService, BazaarService


def bazaar_token_view(request, *args, **kwargs):
    return HttpResponse()


class PayView(View):
    @method_decorator(csrf_exempt)
    def dispatch(self, request, *args, **kwargs):
        return super(PayView, self).dispatch(request, *args, **kwargs)

    def get(self, request):
        """
        check id and gateway and redirect user to related paying method
        """
        # check and validate parameters
        if not ('invoice_number' in request.GET or 'gateway' in request.GET or 'service' in request.GET):
            return HttpResponse("")

        try:
            service_gateway = ServiceGateway.objects.select_related('gateway').get(
                gateway=request.GET['gateway'],
                service__uuid=request.GET['service'],
                is_enable=True,
                gateway__properties__merchant_id__isnull=False,
                gateway__properties__gateway_url__isnull=False,
                gateway__properties__verify_url__isnull=False
            )
        except ServiceGateway.DoesNotExist:
            return HttpResponse("")

        try:
            payment = Order.objects.get(
                invoice_number=request.GET['invoice_number'],
                service_gateway=service_gateway,
                is_paid=None
            )
        except Order.DoesNotExist:
            return HttpResponse("")

        return render_bank_page(
            request,
            payment.invoice_number,
            service_gateway.gateway.properties.get('gateway_url'),
            service_gateway.gateway.properties.get('merchant_id'),
            payment.price,
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
                'service_gateway',
                'service_gateway__gateway'
            ).select_for_update().get(
                invoice_number=invoice_number
            )
        except Order.DoesNotExist:
            pass
        except Exception as e:
            pass
        else:
            # !!! Very important to check none so if a payment has been verified before don't do it again
            if payment.is_paid is None and payment.service_gateway.gateway.code == Gateway.FUNCTION_SAMAN:
                purchase_verified = SamanService().verify_saman(
                    payment,
                    data

                )
            elif payment.is_paid is None and payment.service_gateway.gateway.code == Gateway.FUNCTION_BAZAAR:
                if not data.get('purchase_token'):
                    return JsonResponse({'error': "purchase_token is required!"})
                purchase_verified = BazaarService.verify_purchase(
                    payment,
                    data.get('purchase_token')
                )

        return JsonResponse({'payment_status': purchase_verified, 'data': data})


def render_bank_page(
        request, invoice_id, request_url,
        merchant_id, amount, phone_number='', **kwargs
):
    """
    send parameters to a template ... template contain a form include these parameters
    this form automatically submit to bank url
    """
    render_context = {
        "invoice_id": invoice_id,
        "request_url": request_url,
        "merchant_id": merchant_id,
        "redirect_url": request.build_absolute_uri(reverse('payment-gateway')),
        "amount": amount * 10,
        "extra_data": kwargs,
    }
    return render(request, 'payments/pay.html', context=render_context)
