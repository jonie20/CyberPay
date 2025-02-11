from django.shortcuts import render
from django.http import JsonResponse
from django.http import HttpResponse
import requests
import json

from . credentials import MpesaAccessToken, LipanaMpesaPpassword

from cyberpayment.models import Payment, Transaction


# Create your views here.
def dashboard(request):
    return render(request, 'admin/index.html')

def ipay(request):
    
    if request.method == "POST":
        phone = request.POST['phone']
        access_token = MpesaAccessToken.validated_mpesa_access_token
        api_url = "https://sandbox.safaricom.co.ke/mpesa/stkpush/v1/processrequest"
        headers = {"Authorization": "Bearer %s" % access_token}

        stk_request_payload = {
            "BusinessShortCode": LipanaMpesaPpassword.Business_short_code,
            "Password": LipanaMpesaPpassword.decode_password,
            "Timestamp": LipanaMpesaPpassword.lipa_time,
            "TransactionType": "CustomerPayBillOnline",
            "Amount": 1,
            "PartyA": phone,
            "PartyB": LipanaMpesaPpassword.Business_short_code,
            "PhoneNumber": phone,
            "CallBackURL": "https://sandbox.safaricom.co.ke/mpesa/",
            "AccountReference": "Johnstone Kipkosgei Cheruiyot",
            "TransactionDesc": "Web development Charges..."
        }

        response = requests.post(api_url, json=stk_request_payload, headers=headers)
        return HttpResponse("STK Push request sent successfully!")
        
    return render(request, 'user/index.html')

    
def mpesa_callback(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body.decode('utf-8'))

            # Validate the callback URL signature (if applicable)
            # ... (Implement signature validation based on M-Pesa documentation)

            # Extract relevant data from the callback 
            merchant_request_id = data.get('MerchantRequestID')
            checkout_request_id = data.get('CheckoutRequestID')
            result_code = data.get('ResultCode')
            result_description = data.get('ResultDesc')
            amount = data.get('Amount') 

            # Update payment status in your database
            # ... (Logic to update payment status in your models)

            if result_code == '0':
                # Payment successful
                return JsonResponse({'status': 'success', 'message': 'Payment received successfully'})
            else:
                # Payment failed
                return JsonResponse({'status': 'error', 'message': 'Payment failed: ' + result_description})

        except Exception as e:
            return JsonResponse({'status': 'error', 'message': 'Error processing callback: ' + str(e)})

    return JsonResponse({'status': 'error', 'message': 'Invalid request method'})