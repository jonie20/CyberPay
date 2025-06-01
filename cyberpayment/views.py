from django.conf import settings
from django.contrib import messages
from django.core.exceptions import ObjectDoesNotExist
from django.contrib.auth import get_user_model
from django.contrib.sites.shortcuts import get_current_site
from django.contrib.auth.tokens import default_token_generator
from django.core.mail import EmailMessage
from django.contrib.auth import login, logout
from django.shortcuts import render,redirect
from django.utils.http import urlsafe_base64_encode, urlsafe_base64_decode
from django.template.loader import render_to_string
from django.utils.encoding import force_bytes
from django.contrib.auth.decorators import login_required
from django.views.decorators.csrf import csrf_exempt
from django.http import JsonResponse, HttpResponseBadRequest
from django.http import HttpResponse
import requests, re, base64
from datetime import datetime
from django.views import View
from django.db.models import Sum
from django.utils.timezone import now
import json
import logging
logger = logging.getLogger(__name__)

from cyberpayment.authentication import AccountAuthentication
from . credentials import MpesaAccessToken, LipanaMpesaPpassword

from cyberpayment.models import Payment, Transaction,Services, Account

CONSUMER_KEY = "77bgGpmlOxlgJu6oEXhEgUgnu0j2WYxA"
CONSUMER_SECRET = "viM8ejHgtEmtPTHd"
MPESA_PASSKEY = "bfb279f9aa9bdbcf158e97dd71a467cd2e0c893059b10f78e6b72ada1ed2c919"

MPESA_SHORTCODE = "174379"
CALLBACK_URL = "https://b71e-102-68-77-175.ngrok-free.app/callback/"
MPESA_BASE_URL = "https://sandbox.safaricom.co.ke"

# Create your views here.

class LoginView(View):
    def get(self, request):
        return render(request, 'login.html')

    def post(self, request):
        email = request.POST.get('email')
        password = request.POST.get('password1')
        user = AccountAuthentication.authenticate(request, email=email, password=password)

        if user is not None:
            login(request, user)

            # Redirect based on user's role or permissions
            if user.is_superuser or user.is_staff:  # For admin users
                return redirect('dash')
            else:  # For regular users
                return redirect('home')  # Ensure 'dash' is defined in urls.py

        else:
            messages.error(request, "Invalid email or password. Please try again.")
            return redirect('login-view')  # Ensure 'login-view' is defined in urls.py

@login_required(login_url='login/')
def dash(request):
    today = now().date()
    services_offered = Services.objects.count()
    users = Account.objects.count()
    today_customers = Transaction.objects.filter(created_at=today).count()
    total_earnings = Transaction.objects.filter(created_at=today).aggregate(Sum('amount'))['amount__sum'] or 0 
    recent_transactions = Transaction.objects.all().order_by('-created_at')[:10]

    context = {
        "recent_transactions": recent_transactions,
        "services_offered": services_offered,
        "users": users,
        "today_customers": today_customers,
        "total_earnings": total_earnings,
    }

    return render(request, 'v1/index.html', context)
@login_required(login_url='login/')
def ipay(request):
    servic = Services.objects.all()
    
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
            "CallBackURL": "https://b71e-102-68-77-175.ngrok-free.app/callback",
            "AccountReference": "CyberPay payment",
            "TransactionDesc": "Web development Charges..."
        }

        response = requests.post(
            api_url,
            json=stk_request_payload,
            headers=headers,
        ).json()

        return response


    return render(request, 'user/index.html', {"servic": servic})


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

        print("Full STK Response:", response)
        

        return response

    except Exception as e:
        print(f"Failed to initiate STK Push: {str(e)}")
        return e


@csrf_exempt
def payment_view(request):
    if request.method == "POST":
        try:
            phone = format_phone_number(request.POST.get("phone"))
            amount = (1)  # Static amount for testing

            if not phone:
                return JsonResponse({"ResponseCode": "1", "errorMessage": "Invalid phone number."}, status=400)

            response = initiate_stk_push(phone, amount)
            print("STK Response:", response)

            if response.get("ResponseCode") == "0":
                checkout_request_id = response.get("CheckoutRequestID")
                merchant_request_id = response.get("MerchantRequestID")

                if not checkout_request_id or not merchant_request_id:
                    logger.error("Missing checkout or merchant request ID in response.")
                    return JsonResponse({"ResponseCode": "1", "errorMessage": "Missing checkout or merchant request ID in response."}, status=400)


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

def stk_status_view(request):
    if request.method == 'POST':
        try:
            body_unicode = request.body.decode('utf-8')
            print("Raw Request Body:", body_unicode)  # Debugging
            
            data = json.loads(body_unicode)
            checkout_request_id = data.get('checkout_request_id')
            print("Extracted CheckoutRequestID:", checkout_request_id)  # Debugging
            
            if not checkout_request_id:
                return JsonResponse({"error": "Missing checkout_request_id"}, status=400)

            status = query_stk_push(checkout_request_id)

            # Changes made to retrieve name
            # result = status.get("Result", {})
            # customer_name = result.get("FirstName", "") + " " + result.get("MiddleName", "") + " " + result.get("LastName", "")
            # customer_name = customer_name.strip()


            return JsonResponse({
                "status": status,
                # "customer_name": customer_name or "Unknown"
                })
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
            name = next((item["Value"] for item in metadata if item["Name"] == "Name"), None)

            if not name:
                query_result = query_stk_push(checkout_id)
                name = query_result.get("customer_name", "Unknown")
                
            # Save transaction to the database
            query=Transaction(
                amount=amount, 
                name = name,
                checkout_id=checkout_id, 
                mpesa_code=mpesa_code,
                phone_number= phone,
                status="Success")
            query.save()
            return JsonResponse({"ResultCode": 0, "ResultDesc": "Payment successful"})

        # Payment failed
        return JsonResponse({"ResultCode": result_code, "ResultDesc": "Payment failed"})

    except (json.JSONDecodeError, KeyError) as e:
        return HttpResponseBadRequest(f"Invalid request data: {str(e)}")

def payment_history(request):
    transactions = Transaction.objects.all()
    return render(request, 'user/payment_history.html', {"transactions": transactions})

def payments(request):
    transactions = Transaction.objects.all()

    return render(request, 'v1/payments.html', {"transactions": transactions})
def add_user(request):
    if request.method == "POST":
        try:
            full_name = request.POST['full_name']
            email = request.POST['email']
            phone_number = request.POST['phoneNumber']
            id_number = request.POST['idNumber']

            # Check if ID number already exists
            if Account.objects.filter(id_number=id_number).exists():
                return JsonResponse({"status": "error", "message": "ID number already exists"}, status=400)

            # Create and save the user
            user = Account.objects.create(
                full_name=full_name,
                email=email,
                phone_number=phone_number,
                id_number=id_number
            )

            if email:
                uid = urlsafe_base64_encode(force_bytes(user.pk))

                token = default_token_generator.make_token(user)
                domain = get_current_site(request).domain
                link = f"http://{domain}/activate/{uid}/{token}/"

                print(f"Users found: {user.id}")

                email_subject = "Set Password for your account"
                html_message = render_to_string('v1/activate.html', {
                    "link": link,
                    "user": user,
                })
                from_email = settings.EMAIL_HOST_USER
                to_email = [email]

                try:
                    email_message = EmailMessage(
                        email_subject,
                        html_message,
                        from_email,
                        to_email,
                    )
                    email_message.content_subtype = "html"
                    email_message.send(fail_silently=False)
                    return JsonResponse({"status": "success", "message": "User added successfully and email sent"})
                except Exception as e:
                    return JsonResponse({"status": "error", "message": f"Failed to send email: {str(e)}"}, status=500)
        
        except KeyError as e:
            return JsonResponse({"status": "error", "message": f"Missing field: {str(e)}"}, status=400)
        except Exception as e:
            return JsonResponse({"status": "error", "message": f"An unexpected error occurred: {str(e)}"}, status=500)
    
    return HttpResponseBadRequest("Invalid request method")


def set_pass(request, uid, token):
    try:
        # Decode the user ID
        try:
            user_id = urlsafe_base64_decode(uid).decode('utf-8')
            print(f"Decoded user ID: {user_id}")  # Debugging log
        except Exception as e:
            print(f"Error decoding UID: {e}")
            return JsonResponse({"status": "success", "message": "User added successfully and email sent"})
            # return redirect('login-view')

        # Fetch the user using Account model
        user = Account.objects.filter(id=user_id).first()
        if not user:
            print(f"User with ID {user_id} does not exist in Account model.")
            return JsonResponse({"status": "success", "message": "User added successfully and email sent"})
            # return redirect('login-view')

        if default_token_generator.check_token(user, token):
            if request.method == 'POST':
                new_password = request.POST.get('password')
                confirm_password = request.POST.get('confirm_password')
                if new_password and new_password == confirm_password:
                    user.set_password(new_password)
                    user.save()

                    # Send email notification
                    email_subject = "Password Changed Successfully"
                    html_content = render_to_string('user/confirm_pass.html', {'user': user})
                    from_email = settings.EMAIL_HOST_USER
                    to_email = [user.email]

                    try:
                        email = EmailMessage(
                            subject=email_subject,
                            body=html_content,
                            from_email=from_email,
                            to=to_email,
                        )
                        email.content_subtype = "html"
                        email.send(fail_silently=False)
                    except Exception as e:
                        # Log or display the exception message
                        return JsonResponse({"status": "success", "message": "Error sending email: {str(e)}"})

                    return JsonResponse({"status": "success", "message": "User added successfully and email sent"})
                    return redirect('users')  # Redirect to login after password reset
                else:
                    return JsonResponse({"status": "success", "message": "Password does not match"})
            return render(request, 'user/set-password.html', {'uid': uid, 'token': token})
        else:
            return JsonResponse({"status": "success", "message": "Password reset link is invalid or has expired"})
            return redirect('home')
    except Exception as e:
        print(f"Error encountered: {str(e)}")
        return JsonResponse({"status": "success", "message": "unexpected error occurred"})
        return redirect('home')  
def users(request):
    users = Account.objects.all()

    if request.method == "POST":
        full_name=request.POST('full_name'),
        email=request.POST('email'),
        phone_number=request.POST('phoneNumber'),
        id_number=request.POST('idNumber'),

        Account.objects.create(
                full_name=full_name,
                email=email,
                phone_number=phone_number,
                id_number=id_number
            )
        if email:
            users = Account.objects.filter(email=email)
            if users.exists():
                for user in users:
                    uid = urlsafe_base64_encode(force_bytes(user.id))
                    token = default_token_generator.make_token(user)
                    domain = get_current_site(request).domain
                    link = f"http://{domain}/activate/{uid}/{token}/"

                    email_subject = "Set Password for your account"
                    html_message = render_to_string('v1/activate_account.html', {
                        "link": link,
                        "user": user,
                    })
                    from_email = settings.EMAIL_HOST_USER
                    to_email = [user.email]

                    try:
                        email = EmailMessage(
                            email_subject,
                            html_message,
                            from_email,
                            to_email,
                        )
                        email.content_subtype = "html"
                        email.send(fail_silently=False)
                        messages.success(request, "User added successfully. An email has been sent to the user to set their password.")
                    except Exception as e:
                        print(f"Failed to send email: {str(e)}")
                return redirect('users')


        return redirect('services')

    return render(request, 'v1/users.html' , {"users": users})
class RegisterView(View):

    def post(self, request):

        # Automatically set username to be the same as the first name
        username = request.POST('full_name').lower()  # Use the lowercase of the first name as the username

        # Check if the username already exists
        if Account.objects.filter(username=username).exists():
            messages.error(request, "This username already exists. Please choose another one.")
            return redirect('register')  # Redirect back to the registration form

        # Create Account model using the form data
        account_model = Account.objects.create(
            full_name=request.POST('full_name'),
            email=request.POST('email'),
            phone_number=request.POST('phoneNumber'),
            id_number=request.POST('idNumber'),
        )

        # Set password and save the account model
        account_model.set_password(request.POST.get('password1'))
        account_model.save()

        # Redirect to the dashboard without logging the user in
        messages.success(request, "Registration successful! You can now log in.")
        return redirect('dashboard')  # Redirect to the dashboard after successful registration
def services(request):
    services = Services.objects.all()

    if request.method == "POST":
        name = request.POST['name']
        description = request.POST['description']
        cost = request.POST['amount']

        service = Services(name=name, description=description, cost=cost)
        service.save()

        return redirect('services')

    return render(request, 'v1/services.html', {"services": services})

def reset_pass(request):
    if request.method == 'POST':
        email = request.POST.get('email')
        # print(f"Received email: {email}")  # Debug statement
        if email:
            users = Account.objects.filter(email=email)
            # print(f"Users found: {users.count()}")  # Debug statement
            if users.exists():
                for user in users:
                    uid = urlsafe_base64_encode(force_bytes(user.id))
                    token = default_token_generator.make_token(user)
                    domain = get_current_site(request).domain
                    link = f"http://{domain}/accounts/set_pass/{uid}/{token}/"

                    # Prepare the reset password email
                    email_subject = "Password Reset Request"
                    html_content = render_to_string('reset_email.html', {'link': link})  # Render the HTML template
                    from_email = settings.EMAIL_HOST_USER  # Your configured sender email
                    to_email = [user.email]

                    try:
                        # Create the email object
                        email = EmailMessage(
                            subject=email_subject,
                            body=html_content,
                            from_email=from_email,
                            to=to_email,
                        )

                        # Specify the content type as HTML
                        email.content_subtype = "html"

                        # Send the email
                        email.send(fail_silently=False)
                        messages.success(request, f"Password reset email sent to {user.email}.")
                    except Exception as e:
                        messages.error(request, f"Error sending email to {user.email}: {str(e)}")

                return redirect('login-view')
            else:
                messages.error(request, "No account found with that email address.")
        else:
            messages.error(request, "Please enter a valid email address.")

    return render(request, 'reset-password.html')