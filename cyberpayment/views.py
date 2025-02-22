from django.shortcuts import render,redirect
from django.views.decorators.csrf import csrf_exempt
from django.http import JsonResponse, HttpResponseBadRequest
from django.http import HttpResponse
import requests, re, base64
from datetime import datetime
from .forms import PaymentForm
import json
import logging
logger = logging.getLogger(__name__)

from . credentials import MpesaAccessToken, LipanaMpesaPpassword

from cyberpayment.models import Payment, Transaction

CONSUMER_KEY = "77bgGpmlOxlgJu6oEXhEgUgnu0j2WYxA"
CONSUMER_SECRET = "viM8ejHgtEmtPTHd"
MPESA_PASSKEY = "bfb279f9aa9bdbcf158e97dd71a467cd2e0c893059b10f78e6b72ada1ed2c919"

MPESA_SHORTCODE = "174379"
CALLBACK_URL = "https://new.com/head"
MPESA_BASE_URL = "https://sandbox.safaricom.co.ke"

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

        response = requests.post(
            api_url,
            json=stk_request_payload,
            headers=headers,
        ).json()

        return response

        # response = requests.post(api_url, json=stk_request_payload, headers=headers)
        
        # if response.status_code == 200:
        #     return redirect('payment_status')  # Redirect to waiting page
        # else:
        #     return HttpResponse("Error processing payment request", status=500)
        
        
    return render(request, 'user/index.html')


def payment(request): 
    try:
        response = ipay()
        print(response)

        if response.get("ResponseCode") == "0":
            checkout_request_id = response["CheckoutRequestID"]
            return render(request, 'user/pending.html', {"checkout_request_id": checkout_request_id})
        else:
            error_message = response.get("errorMessage", "Failed to send STK push. Please try again.")
            return render(request, 'user/index.html', { "error_message": error_message})


    except ValueError as e:
        return render(request, 'user/index.html', { "error_message": str(e)})
    except Exception as e:
        return render(request, 'user/index.html', { "error_message": f"An unexpected error occurred: {str(e)}"})


    return render(request, 'user/index.html')  











# Phone number formatting and validation
def format_phone_number(phone):
    phone = phone.replace("+", "")
    if re.match(r"^254\d{9}$", phone):
        return phone
    elif phone.startswith("0") and len(phone) == 10:
        return "254" + phone[1:]
    else:
        raise ValueError("Invalid phone number format")

# Generate M-Pesa access token
def generate_access_token():
    try:
        credentials = f"{CONSUMER_KEY}:{CONSUMER_SECRET}"
        encoded_credentials = base64.b64encode(credentials.encode()).decode()

        headers = {
            "Authorization": f"Basic {encoded_credentials}",
            "Content-Type": "application/json",
        }
        response = requests.get(
            f"{MPESA_BASE_URL}/oauth/v1/generate?grant_type=client_credentials",
            headers=headers,
        ).json()

        if "access_token" in response:
            return response["access_token"]
        else:
            raise Exception("Access token missing in response.")

    except requests.RequestException as e:
        raise Exception(f"Failed to connect to M-Pesa: {str(e)}")

# Initiate STK Push and handle response
def initiate_stk_push(phone, amount):
    try:
        token = generate_access_token()
        headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}

        timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
        stk_password = base64.b64encode(
            (MPESA_SHORTCODE + MPESA_PASSKEY + timestamp).encode()
        ).decode()

        request_body = {
            "BusinessShortCode": MPESA_SHORTCODE,
            "Password": stk_password,
            "Timestamp": timestamp,
            "TransactionType": "CustomerPayBillOnline",
            "Amount": amount,
            "PartyA": phone,
            "PartyB": MPESA_SHORTCODE,
            "PhoneNumber": phone,
            "CallBackURL": CALLBACK_URL,
            "AccountReference": "account",
            "TransactionDesc": "Payment for goods",
        }

        response = requests.post(
            f"{MPESA_BASE_URL}/mpesa/stkpush/v1/processrequest",
            json=request_body,
            headers=headers,
        ).json()

        return response

    except Exception as e:
        print(f"Failed to initiate STK Push: {str(e)}")
        return e

# Payment View

# def payment_view(request):
#     if request.method == "POST":
#             try:
#                 phone = format_phone_number(request.POST['phone'])
#                 amount = (1)
#                 response = initiate_stk_push(phone, amount)
#                 print(response)

#                 if response.get("ResponseCode") == "0":
#                     checkout_request_id = response["CheckoutRequestID"]
#                     return render(request, 'user/pending.html', {"checkout_request_id": checkout_request_id})
#                 else:
#                     error_message = response.get("errorMessage", "Failed to send STK push. Please try again.")
#                     return render(request, 'user/test.html', { "error_message": error_message})

#             except ValueError as e:
#                 return render(request, 'user/test.html', { "error_message": str(e)})
#             except Exception as e:
#                 return render(request, 'user/test.html', { "error_message": f"An unexpected error occurred: {str(e)}"})

#     else:
#         form = PaymentForm()

#     return render(request, 'user/test.html')
@csrf_exempt
def payment_view(request):
    if request.method == "POST":
        try:
            phone = format_phone_number(request.POST.get("phone"))
            amount = (10)  # Static amount for testing

            if not phone:
                return JsonResponse({"ResponseCode": "1", "errorMessage": "Invalid phone number."}, status=400)

            response = initiate_stk_push(phone, amount)
            print("STK Response:", response)

            if response.get("ResponseCode") == "0":
                checkout_request_id = response["CheckoutRequestID"]
                merchant_request_id = response["MerchantRequestID"]

                # Save transaction in the database
                # Transaction.objects.create(
                #     phone=phone,
                #     amount=amount,
                #     merchant_request_id=merchant_request_id,
                #     checkout_request_id=checkout_request_id,
                #     status="PENDING"
                # )

                return JsonResponse({"ResponseCode": "0", "CheckoutRequestID": checkout_request_id})

            return JsonResponse({
                "ResponseCode": "1",
                "errorMessage": response.get("errorMessage", "Failed to send STK push. Please try again.")
            }, status=400)

        except ValueError as e:
            return JsonResponse({"ResponseCode": "1", "errorMessage": str(e)}, status=400)
        except Exception as e:
            return JsonResponse({"ResponseCode": "1", "errorMessage": f"An unexpected error occurred: {str(e)}"}, status=500)

    return JsonResponse({"ResponseCode": "1", "errorMessage": "Invalid request method"}, status=405)

# Query STK Push status
def query_stk_push(checkout_request_id):
    print("Quering...")
    try:
        token = generate_access_token()
        headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}

        timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
        password = base64.b64encode(
            (MPESA_SHORTCODE + MPESA_PASSKEY + timestamp).encode()
        ).decode()

        request_body = {
            "BusinessShortCode": MPESA_SHORTCODE,
            "Password": password,
            "Timestamp": timestamp,
            "CheckoutRequestID": checkout_request_id
        }

        response = requests.post(
            f"{MPESA_BASE_URL}/mpesa/stkpushquery/v1/query",
            json=request_body,
            headers=headers,
        )
        print(response.json())
        return response.json()

    except requests.RequestException as e:
        print(f"Error querying STK status: {str(e)}")
        return {"error": str(e)}

# View to query the STK status and return it to the frontend
def stk_status_view(request):
    if request.method == 'POST':
        try:
            # Parse the JSON body
            data = json.loads(request.body)
            checkout_request_id = data.get('checkout_request_id')
            print("CheckoutRequestID:", checkout_request_id)

            # Query the STK push status using your backend function
            status = query_stk_push(checkout_request_id)

            # Return the status as a JSON response
            return JsonResponse({"status": status})
        except json.JSONDecodeError:
            return JsonResponse({"error": "Invalid JSON body"}, status=400)

    return JsonResponse({"error": "Invalid request method"}, status=405)

@csrf_exempt  # To allow POST requests from external sources like M-Pesa
def payment_callback(request):
    if request.method != "POST":
        return HttpResponseBadRequest("Only POST requests are allowed")

    try:
        callback_data = json.loads(request.body)  # Parse the request body
        result_code = callback_data["Body"]["stkCallback"]["ResultCode"]

        if result_code == 0:
            # Successful transaction
            checkout_id = callback_data["Body"]["stkCallback"]["CheckoutRequestID"]
            metadata = callback_data["Body"]["stkCallback"]["CallbackMetadata"]["Item"]

            amount = next(item["Value"] for item in metadata if item["Name"] == "Amount")
            mpesa_code = next(item["Value"] for item in metadata if item["Name"] == "MpesaReceiptNumber")
            phone = next(item["Value"] for item in metadata if item["Name"] == "PhoneNumber")

            # Save transaction to the database
            Transaction.objects.create(
                amount=amount, 
                checkout_id=checkout_id, 
                mpesa_code=mpesa_code, 
                phone_number=phone, 
                status="Success"
            )
            return JsonResponse({"ResultCode": 0, "ResultDesc": "Payment successful"})

        # Payment failed
        return JsonResponse({"ResultCode": result_code, "ResultDesc": "Payment failed"})

    except (json.JSONDecodeError, KeyError) as e:
        return HttpResponseBadRequest(f"Invalid request data: {str(e)}")


# @csrf_exempt
# def callback(request):
#     logger.info(f"Received request: {request.method}, Body: {request.body}")

#     if request.method == 'GET':
#         return JsonResponse({'message': 'MPesa callback endpoint active'}, status=200)

#     if request.method == 'POST':
#         try:
#             # Check if the request body is empty
#             if not request.body:
#                 logger.error("Received empty request body")
#                 return JsonResponse({'error': 'Empty request body'}, status=400)

#             # Parse the JSON data
#             resp = json.loads(request.body.decode('utf-8'))
#             logger.info(f"Parsed JSON: {resp}")

#             data = resp.get('Body', {}).get('stkCallback', {})
#             if data.get("ResultCode") == 0:
#                 m_id = data.get("MerchantRequestID")
#                 c_id = data.get("CheckoutRequestID")
#                 code = ""

#                 for item in data.get("CallbackMetadata", {}).get("Item", []):
#                     if item["Name"] == "MpesaReceiptNumber":
#                         code = item["Value"]

#                 from .models import Transaction
#                 transaction = Transaction.objects.get(merchant_request_id=m_id, checkout_request_id=c_id)
#                 transaction.code = code
#                 transaction.status = "COMPLETED"
#                 transaction.save()

#             return HttpResponse("OK")

#         except json.JSONDecodeError as e:
#             logger.error(f"Invalid JSON data received: {e}")
#             return JsonResponse({'error': 'Invalid JSON data'}, status=400)

#     return JsonResponse({'error': 'Invalid request method'}, status=405)
# def mpesa_callback(request):
#     if request.method == 'POST':
#         try:
#             data = json.loads(request.body.decode('utf-8'))

#             # Validate the callback URL signature (if applicable)
#             # ... (Implement signature validation based on M-Pesa documentation)

#             # Extract relevant data from the callback 
#             merchant_request_id = data.get('MerchantRequestID')
#             checkout_request_id = data.get('CheckoutRequestID')
#             result_code = data.get('ResultCode')
#             result_description = data.get('ResultDesc')
#             amount = data.get('Amount') 

#             # Update payment status in your database
#             # ... (Logic to update payment status in your models)

#             if result_code == '0':
#                 # Payment successful
#                 return JsonResponse({'status': 'success', 'message': 'Payment received successfully'})
#             else:
#                 # Payment failed
#                 return JsonResponse({'status': 'error', 'message': 'Payment failed: ' + result_description})

#         except Exception as e:
#             return JsonResponse({'status': 'error', 'message': 'Error processing callback: ' + str(e)})

#     return JsonResponse({'status': 'error', 'message': 'Invalid request method'})

# def payment_callback(request):
#     if request.method == "POST":
#         mpesa_response = json.loads(request.body.decode("utf-8"))

#         # Extract payment status
#         result_code = mpesa_response["Body"]["stkCallback"]["ResultCode"]
#         checkout_request_id = mpesa_response["Body"]["stkCallback"]["CheckoutRequestID"]

#         if result_code == 0:
#             payment_status = "success"
#         else:
#             payment_status = "failed"

#         # Store the payment status in the database (Example)
#         Payment.objects.create(
#             checkout_request_id=checkout_request_id,
#             status=payment_status
#         )

#         return JsonResponse({"message": "Callback received successfully"}, status=200)

#     return JsonResponse({"error": "Invalid request"}, status=400)

# def check_payment_status(request):
#     latest_payment = Payment.objects.last()  # Get the latest payment record

#     if latest_payment and latest_payment.status == "success":
#         return JsonResponse({"payment_status": "success"})
#     else:
#         return JsonResponse({"payment_status": "pending"})

# def payment_status(request):
#         return render(request, 'user/payment_status.html')
        