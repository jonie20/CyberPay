from django.shortcuts import render,redirect
from django.views.decorators.csrf import csrf_exempt
from django.http import JsonResponse
from django.http import HttpResponse
import requests
import json
import logging
logger = logging.getLogger(__name__)

from . credentials import MpesaAccessToken, LipanaMpesaPpassword

from cyberpayment.models import Payment, Transaction


# Create your views here.
def dashboard(request):
    return render(request, 'v1/index.html')

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
            "CallBackURL": "https://ed78-102-68-77-175.ngrok-free.app/callback",
            "AccountReference": "CyberPay payment",
            "TransactionDesc": "Web development Charges..."
        }

        response = requests.post(api_url, json=stk_request_payload, headers=headers)
        
        if response.status_code == 200:
            return redirect('payment_status')  # Redirect to waiting page
        else:
            return HttpResponse("Error processing payment request", status=500)
        
        
    return render(request, 'user/index.html')



@csrf_exempt
def callback(request):
    logger.info(f"Received request: {request.method}, Body: {request.body}")

    if request.method == 'GET':
        return JsonResponse({'message': 'MPesa callback endpoint active'}, status=200)

    if request.method == 'POST':
        try:
            # Check if the request body is empty
            if not request.body:
                logger.error("Received empty request body")
                return JsonResponse({'error': 'Empty request body'}, status=400)

            # Parse the JSON data
            resp = json.loads(request.body.decode('utf-8'))
            logger.info(f"Parsed JSON: {resp}")

            data = resp.get('Body', {}).get('stkCallback', {})
            if data.get("ResultCode") == 0:
                m_id = data.get("MerchantRequestID")
                c_id = data.get("CheckoutRequestID")
                code = ""

                for item in data.get("CallbackMetadata", {}).get("Item", []):
                    if item["Name"] == "MpesaReceiptNumber":
                        code = item["Value"]

                from .models import Transaction
                transaction = Transaction.objects.get(merchant_request_id=m_id, checkout_request_id=c_id)
                transaction.code = code
                transaction.status = "COMPLETED"
                transaction.save()

            return HttpResponse("OK")

        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON data received: {e}")
            return JsonResponse({'error': 'Invalid JSON data'}, status=400)

    return JsonResponse({'error': 'Invalid request method'}, status=405)
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

def payment_callback(request):
    if request.method == "POST":
        mpesa_response = json.loads(request.body.decode("utf-8"))

        # Extract payment status
        result_code = mpesa_response["Body"]["stkCallback"]["ResultCode"]
        checkout_request_id = mpesa_response["Body"]["stkCallback"]["CheckoutRequestID"]

        if result_code == 0:
            payment_status = "success"
        else:
            payment_status = "failed"

        # Store the payment status in the database (Example)
        Payment.objects.create(
            checkout_request_id=checkout_request_id,
            status=payment_status
        )

        return JsonResponse({"message": "Callback received successfully"}, status=200)

    return JsonResponse({"error": "Invalid request"}, status=400)

def check_payment_status(request):
    latest_payment = Payment.objects.last()  # Get the latest payment record

    if latest_payment and latest_payment.status == "success":
        return JsonResponse({"payment_status": "success"})
    else:
        return JsonResponse({"payment_status": "pending"})

def payment_status(request):
        return render(request, 'user/payment_status.html')