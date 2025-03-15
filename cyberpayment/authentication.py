from cyberpayment.models import Account

class AccountAuthentication(object):
    def authenticate(self, email=None, password=None):
        try:
            user = Account.objects.get(email=email)
            if user.check_password(password) and user.email==email:
                return user
            return None
        except Account.DoesNotExist:
            return None

    def get_user(self, user_id):
        try:
            return Account.objects.get(id=user_id)
        except Account.DoesNotExist:
            return None