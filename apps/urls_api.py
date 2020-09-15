from django.urls import path, include

urlpatterns = [
    path('payment/', include("apps.payments.api.urls")),
]
