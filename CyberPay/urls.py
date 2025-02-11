"""
URL configuration for CyberPay project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.1/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path
from cyberpayment import views

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', views.ipay, name="home"),
    # path('pay', views.send_mpesa_request, name="ipay"),
    path('payment-status/', views.payment_status, name='payment_status'),
    path('payment-callback/', views.payment_callback, name='payment_callback'),
    path('check-payment-status/', views.check_payment_status, name='check_payment_status'),
    path('callback/',views.mpesa_callback, name='mpesa_callback'),
    path('v1', views.dashboard, name="dashboard")
]
