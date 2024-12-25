import datetime

from django.contrib import messages, auth
from django.contrib.auth import logout
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib.auth.models import User
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from django.core.mail import send_mail
from django.db.models import Q
from django.shortcuts import render, redirect, get_object_or_404
from django.template.loader import render_to_string
from django.urls.base import reverse
from django.utils import timezone
from django.utils.html import strip_tags

from CyberRange.utils import generate_code
from .models import PasswordResetRequest, StaffActivationPin, UserActivationPin, LoginAttempt


def check_password_case(password):
    # Check if password has at least one uppercase letter
    has_uppercase = any(char.isupper() for char in password)

    # Check if password has at least one lowercase letter
    has_lowercase = any(char.islower() for char in password)

    # Return True if both uppercase and lowercase are present
    return has_uppercase and has_lowercase


def check_password_numeric_and_symbols(password):
    # Check if password has at least one numeric character
    has_numeric = any(char.isdigit() for char in password)

    # Check if password has at least one special symbol
    has_symbols = any(not char.isalnum() for char in password)

    # Return True if both numeric and symbols are present
    return has_numeric and has_symbols


# Student Functions
def register(request):
    if request.user.is_authenticated:
        return redirect('scenario:console')

    context = {}
    if request.method == 'POST':
        username = request.POST['username']
        password1 = request.POST['password1']
        password2 = request.POST['password2']
        email = request.POST['email']
        first_name = request.POST['first_name']
        last_name = request.POST['last_name']

        context = {
            'username': username,
            'email': email,
            'first_name': first_name,
            'last_name': last_name
        }

        if not (7 <= len(username) <= 30):
            messages.error(request, 'Username must be between 7 and 20 characters')
            return render(request, 'Register.html', context)

        if not check_password_case(password1):
            messages.error(request, 'Password must contain both uppercase and lowercase letters')
            return render(request, 'Register.html', context)

        if not check_password_case(password2):
            messages.error(request, 'Password must contain both uppercase and lowercase letters')
            return render(request, 'Register.html', context)

        if not check_password_numeric_and_symbols(password1):
            messages.error(request, 'Password must contain numeric and special characters')
            return render(request, 'Register.html', context)

        if not check_password_numeric_and_symbols(password2):
            messages.error(request, 'Password must contain numeric and special characters')
            return render(request, 'Register.html', context)

        try:
            validate_password(password1)
        except ValidationError as e:
            messages.error(request, ', '.join(e.messages))
            return render(request, 'Register.html', context)

        if User.objects.filter(username=username).exists():
            messages.error(request, 'Username already exists, choose another one')
            return render(request, 'Register.html', context)

        if User.objects.filter(email=email).exists():
            messages.error(request, 'Email already exists, choose another one')
            return render(request, 'Register.html', context)

        if password1 == password2:
            try:
                user = User.objects.create_user(username=username, first_name=first_name, last_name=last_name,
                                                email=email, password=password1, is_active='False')
                pin = generate_code()
                expires_at = timezone.now() + timezone.timedelta(minutes=15)
                UserActivationPin.objects.create(user=user, pin=pin, expires_at=expires_at)
                send_mail(
                    'Activate your account',
                    f'Please input the the code to active the code {pin} ',
                    'lee',
                    [user.email],
                )
                messages.success(request, "Registration Successful. Please check your email")
                return redirect('account:activate_user')
            except ValidationError as e:
                messages.error(request, ', '.join(e.messages))
                return render(request, 'Register.html', context)
        else:
            messages.error(request, 'Passwords do not match')
            return render(request, 'Register.html', context)
    else:
        return render(request, 'Register.html', context)


def activate_user(request):
    if request.method == 'POST':
        pin = request.POST.get('ActiveAccountCode')

        try:
            activation = UserActivationPin.objects.get(pin=pin)
            if activation.is_valid():
                user = activation.user
                user.is_active = True
                user.save()
                activation.delete()
                messages.success(request, "Your account has been successfully activated. You can now log in.")
                return redirect('account:login')
            else:
                messages.error(request, "Invalid or expired PIN. Please register again.")
        except UserActivationPin.DoesNotExist:
            messages.error(request, "Invalid username or PIN.")

    return render(request, 'ActiveAccount.html')


def login(request):
    if request.user.is_authenticated:
        return redirect('scenario:console')

    if request.method == 'POST':
        username = request.POST['username']
        password = request.POST['password']

        context = {
            'username': username,
        }

        try:
            user = User.objects.get(username=username)
            if not user.is_active:
                messages.error(
                    request,
                    'Your account has been deactivated due to too many failed attempts. '
                    'Please Input Your Username to Request Activation.'
                )
                return redirect('account:RequestActivation')

            user_auth = auth.authenticate(request=request, username=username, password=password)

            if user_auth is not None:
                auth.login(request, user_auth)
                LoginAttempt.clear_attempts(user)
                messages.success(request, 'You have successfully logged in.')
                return redirect('scenario:console')
            else:
                LoginAttempt.add_failed_attempt(user)
                failed_attempts = LoginAttempt.get_failed_attempts(user)

                if failed_attempts >= LoginAttempt.MAX_ATTEMPTS:
                    user.is_active = False
                    user.save()
                    LoginAttempt.clear_attempts(user)
                    messages.error(
                        request,
                        'Your account has been deactivated due to too many failed attempts. '
                        'Please Reactivate your account.'
                    )
                    return redirect('account:RequestActivation')
                else:
                    attempts_remaining = LoginAttempt.MAX_ATTEMPTS - failed_attempts
                    messages.warning(
                        request,
                        f'Invalid login credentials. {attempts_remaining} attempts remaining before account deactivation.'
                    )
                return render(request, 'Login.html', context)

        except User.DoesNotExist:
            messages.error(request, 'Invalid username or password.')
            return render(request, 'Login.html', context)

    return render(request, 'Login.html')


def request_password_reset(request):
    if request.method == 'POST':
        username = request.POST.get('username')
        try:
            user = User.objects.get(username=username)
            pin = generate_code()
            expires_at = timezone.now() + datetime.timedelta(minutes=15)
            reset_request = PasswordResetRequest.objects.create(user=user, pin=pin, expires_at=expires_at)
            send_mail(
                'Password Reset PIN',
                f'Your PIN is: {pin}. It will expire in 15 minutes.',
                'lee',
                [user.email],
            )
            return redirect('account:confirm_pin')
        except User.DoesNotExist:
            messages.error(request, 'User not found')
            return render(request, 'ForgotPassword.html')

    return render(request, 'ForgotPassword.html')


def confirm_pin(request):
    if request.method == 'POST':
        username = request.POST.get('username')
        pin = request.POST.get('pin')
        new_password = request.POST.get('password')
        confirm_password = request.POST.get('confirm_password')
        try:
            if not check_password_case(new_password):
                messages.error(request, 'Password must contain both uppercase and lowercase letters')
                return redirect('account:confirm_pin')

            if not check_password_case(confirm_password):
                messages.error(request, 'Password must contain both uppercase and lowercase letters')
                return redirect('account:confirm_pin')

            if not check_password_numeric_and_symbols(new_password):
                messages.error(request, 'Password must contain numeric and special characters')
                return redirect('account:confirm_pin')

            if not check_password_numeric_and_symbols(confirm_password):
                messages.error(request, 'Password must contain numeric and special characters')
                return redirect('account:confirm_pin')

            try:
                validate_password(new_password)
            except ValidationError as e:
                messages.error(request, ', '.join(e.messages))
                return redirect('account:confirm_pin')

            if new_password != confirm_password:
                messages.error(request, 'Passwords do not match')
                return redirect('account:confirm_pin')

            reset_request = PasswordResetRequest.objects.get(user__username=username, pin=pin, used=False)
            if reset_request.is_valid():
                user = reset_request.user
                user.set_password(new_password)
                user.save()
                reset_request.used = True
                reset_request.save()
                messages.success(request, 'Your password has been reset successfully. You can now login.')
                return redirect('account:login')
            else:
                messages.error(request, 'Invalid or expired PIN')
        except PasswordResetRequest.DoesNotExist:
            messages.error(request, 'Invalid username or PIN')

    return render(request, 'ConfirmPassword.html')


def logout_use(request):
    logout(request)
    messages.success(request, "You have been successfully logged out.")
    return redirect('account:login')


@login_required
@user_passes_test(lambda u: u.is_superuser)
def register_instructor(request):
    context = {}
    if request.method == 'POST':
        username = request.POST['staff_username']
        password = request.POST['staff_password']
        confirm_password = request.POST['staff_confirm_password']
        email = request.POST['staff_email']
        first_name = request.POST['staff_first_name']
        last_name = request.POST['staff_last_name']

        context = {
            'staff_username': username,
            'staff_email': email,
            'staff_first_name': first_name,
            'staff_last_name': last_name
        }

        if not check_password_case(password):
            messages.error(request, 'Password must contain both uppercase and lowercase letters')
            return render(request, 'Admin/CreateInstructor.html', context)

        if not check_password_case(confirm_password):
            messages.error(request, 'Password must contain both uppercase and lowercase letters')
            return render(request, 'Admin/CreateInstructor.html', context)

        if not check_password_numeric_and_symbols(password):
            messages.error(request, 'Password must contain numeric and special characters')
            return render(request, 'Admin/CreateInstructor.html', context)

        if not check_password_numeric_and_symbols(confirm_password):
            messages.error(request, 'Password must contain numeric and special characters')
            return render(request, 'Admin/CreateInstructor.html', context)

        if password != confirm_password:
            messages.error(request, 'Passwords do not match')
            return render(request, 'Admin/CreateInstructor.html', context)

        if User.objects.filter(username=username).exists():
            messages.error(request, 'Username already exists, choose another one')
            return render(request, 'Admin/CreateInstructor.html', context)

        if User.objects.filter(email=email).exists():
            messages.error(request, 'Email already exists, choose another one')
            return render(request, 'Admin/CreateInstructor.html', context)

        try:
            validate_password(password)
        except ValidationError as e:
            messages.error(request, ', '.join(e.messages))
            return render(request, 'Admin/CreateInstructor.html', context)

        user = User.objects.create_user(
            username=username,
            email=email,
            password=password,
            first_name=first_name,
            last_name=last_name,
            is_staff=True,
            is_active=False
        )

        pin = generate_code()
        expires_at = timezone.now() + timezone.timedelta(minutes=15)
        StaffActivationPin.objects.create(user=user, pin=pin, expires_at=expires_at)
        activation_url = request.build_absolute_uri(reverse('account:ActivateInstructor'))

        email_context = {
            'username': username,
            'pin': pin,
            'activation_url': activation_url,
        }
        html_message = render_to_string('Admin/ActivePinPage.html', email_context)
        plain_message = strip_tags(html_message)

        send_mail(
            'Active Staff Account',
            plain_message,
            'lee',
            [user.email],
            html_message=html_message
        )

        messages.success(request, "Staff registration successful. An activation email has been sent.")
        return redirect('account:RegisterInstructor')

    return render(request, 'Admin/CreateInstructor.html', context)


def activate_instructor(request):
    if request.method == 'POST':
        username = request.POST.get('username')
        pin = request.POST.get('pin')

        try:
            activation = StaffActivationPin.objects.get(user__username=username, pin=pin)
            if activation.is_valid():
                user = activation.user
                user.is_active = True
                user.save()
                activation.delete()
                messages.success(request, "Your account has been successfully activated. You can now log in.")
                return redirect('account:login')
            else:
                messages.error(request, "Invalid or expired PIN. Please contact the administrator.")
        except StaffActivationPin.DoesNotExist:
            messages.error(request, "Invalid username or PIN.")

    return render(request, 'Admin/ActiveInstructor.html')


@user_passes_test(lambda u: u.is_superuser)
def instructor_list(request):
    search_query = request.GET.get('search', '').strip()
    staff_members = User.objects.filter(is_staff=True).exclude(is_superuser=True)

    if search_query:
        staff_members = staff_members.filter(
            Q(username__icontains=search_query) |
            Q(email__icontains=search_query)
        )

    context = {
        'staff_members': staff_members,
    }
    return render(request, 'Admin/InstructorList.html', context)


@user_passes_test(lambda u: u.is_superuser)
def btn_instructor_status(request, user_id):
    staff_member = get_object_or_404(User, id=user_id, is_staff=True)
    staff_member.is_active = not staff_member.is_active
    staff_member.save()
    status = "activated" if staff_member.is_active else "deactivated"
    messages.success(request, f'Staff member {staff_member.username} has been {status}.')
    return redirect('account:InstructorList')


def handler404(request, exception):
    return render(request, '404.html')


def reactivate_account(request):
    if request.method == 'POST':
        username = request.POST.get('username')
        pin = request.POST.get('pin')

        try:
            user = User.objects.get(username=username)
            activation = UserActivationPin.objects.get(user=user, pin=pin)

            if activation.is_valid():
                user.is_active = True
                user.save()
                LoginAttempt.clear_attempts(user)  # Clear failed attempts
                activation.delete()
                messages.success(request, "Your account has been successfully reactivated. You can now log in.")
                return redirect('account:login')
            else:
                messages.error(request, "Invalid or expired PIN. Please request a new one.")
        except (User.DoesNotExist, UserActivationPin.DoesNotExist):
            messages.error(request, "Invalid username or PIN.")

    return render(request, 'ReActive.html')


def request_reactivation(request):
    if request.method == 'POST':
        username = request.POST.get('username')
        try:
            user = User.objects.get(username=username)
            if not user.is_active:
                # Generate and save activation pin
                pin = generate_code()
                expires_at = timezone.now() + timezone.timedelta(minutes=15)
                UserActivationPin.objects.filter(user=user).delete()
                UserActivationPin.objects.create(user=user, pin=pin, expires_at=expires_at)

                # Send email with activation pin
                send_mail(
                    'Reactivate your account',
                    f'Your account reactivation PIN is: {pin}',
                    'lee',
                    [user.email],
                )
                messages.success(request, "A reactivation PIN has been sent to your email.")
                return redirect('account:ReactivateAccount')
            else:
                messages.error(request, "This account is already active.")
        except User.DoesNotExist:
            messages.error(request, "No account found with this username.")

    return render(request, 'RequestReactive.html')
