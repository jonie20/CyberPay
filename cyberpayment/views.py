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




















































def pay_overdue(request, id):
    transaction = get_object_or_404(Transaction, pk=id)
    total = transaction.total_fine
    phone = transaction.student.phone
    cl = MpesaClient()
    phone_number = '0723740215'
    amount = 1
    account_reference = transaction.student.adm_no
    transaction_desc = 'Fines'
    callback_url = 'https://mature-octopus-causal.ngrok-free.app/handle/payment/transactions'
    response = cl.stk_push(phone_number, amount, account_reference, transaction_desc, callback_url)
    if response.response_code == "0":
        payment= Payment.objects.create(transaction=transaction,
                                        merchant_request_id=response.merchant_request_id ,
                                        checkout_request_id=response.checkout_request_id,
                                        amount=amount)
        payment.save()
        messages.success(request, f'Your payment was triggered successfully')
    return redirect('book_fines')


def callback(request):
    resp = json.loads(request.body)
    data = resp['Body']['stkCallback']
    if data["ResultCode"] == "0":
        m_id = data["MerchantRequestID"]
        c_id = data["CheckoutRequestID"]
        code =""
        item = data["CallbackMetadata"]["Item"]
        for i in item:
            name = i["Name"]
            if name == "MpesaReceiptNumber":
                code= i["Value"]
        transaction = Transaction.objects.get(merchant_request_id=m_id, checkout_request_id=c_id)
        transaction.code = code
        transaction.status = "COMPLETED"
        transaction.save()
    return HttpResponse("OK")

def send_mpesa_request(request):
    if request.method == 'POST':
        try:
            phone_number = request.POST.get('')
            amount = request.POST.get('amount')

            # Generate Access Token
            auth_url = 'https://sandbox.safaricom.co.ke/oauth/v1/generate?grant_type=client_credentials'
            auth_response = requests.get(auth_url, auth=(CONSUMER_KEY, CONSUMER_SECRET))
            auth_data = json.loads(auth_response.text)
            access_token = auth_data['access_token']

            # Prepare request payload
            headers = {
                "Authorization": "Bearer " + access_token,
                "Content-Type": "application/json"
            }

            payload = {
                "BusinessShortCode": "174379", 
                "Password": generate_password(CONSUMER_KEY, CONSUMER_SECRET), 
                "Timestamp": get_timestamp(),
                "TransactionType": "CustomerPayBillOnline", 
                "Amount": 1, 
                "PartyA": +254714378269, 
                "PartyB": "174379", 
                "PhoneNumber": phone_number, 
                "AccountReference": "Reference1",
                "Remarks": "Payment for Service" 
            }

            # Send request to Daraja API
            response = requests.post(BASE_URL, headers=headers, data=json.dumps(payload))
            response_data = json.loads(response.text)

            if response_data.get('ResponseCode') == '0':
                return JsonResponse({'status': 'success', 'message': 'Payment request sent successfully', 'response': response_data})
            else:
                return JsonResponse({'status': 'error', 'message': 'Payment request failed', 'response': response_data})

        except Exception as e:
            return JsonResponse({'status': 'error', 'message': str(e)})

    return JsonResponse({'status': 'error', 'message': 'Invalid request method'})

# Helper functions
def generate_password(consumer_key, consumer_secret):
    import base64
    from datetime import datetime
    current_time = datetime.now().strftime("%Y%m%d%H%M%S")
    data_to_encode = f"{consumer_key}{consumer_secret}{current_time}".encode()
    encoded_string = base64.b64encode(data_to_encode)
    return encoded_string.decode('utf-8')

def get_timestamp():
    from datetime import datetime
    return datetime.now().strftime("%Y%m%d%H%M%S")
