from django.urls import path
from .views import bazaar_token_view, GetBankView, VerifyView

urlpatterns = [
    path('bazaar-token/', bazaar_token_view, name='bazaar-token'),
    path('gateway-bank/<int:order_id>/', GetBankView.as_view(), name='bank-gateway'),
    path('verify/', VerifyView.as_view(), name='verify-payment'),

]
