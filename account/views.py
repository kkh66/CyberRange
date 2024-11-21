import datetime
from django.contrib.auth import logout, update_session_auth_hash
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from django.core.mail import send_mail
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages, auth
from django.template.loader import render_to_string
from django.urls.base import reverse
from django.utils import timezone
from django.contrib.auth.models import User
from django.utils.html import strip_tags
from CyberRange.utils import generate_code
from .models import PasswordResetRequest, StaffActivationPin, UserActivationPin
from django.contrib.auth.decorators import login_required, user_passes_test
from axes.handlers.proxy import AxesProxyHandler
from axes.backends import AxesBackend


# Student Functions
def register(request):
    if request.user.is_authenticated:
        return redirect('console')
    if request.method == 'POST':
        username = request.POST['username']
        password1 = request.POST['password1']
        password2 = request.POST['password2']
        email = request.POST['email']
        first_name = request.POST['first_name']
        last_name = request.POST['last_name']
        if password1 == password2:
            if User.objects.filter(username=username).exists():
                messages.error(request, 'Username already exists, choose another one')
                return redirect('account:register')
            else:
                if User.objects.filter(email=email).exists():
                    messages.error(request, 'Email already exists, choose another one')
                    return redirect('account:register')
                else:
                    try:
                        validate_password(password1)
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
                        return redirect('account:register')
        else:
            return redirect('account:register')
    else:
        return render(request, 'Register.html')


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


class CustomAxesBackend(AxesBackend):
    def get_lockout_response(self, request, credentials):
        messages.error(
            request,
            'This account has been locked due to too many failed attempts. '
            'Please try again after 24 hours.'
        )
        return render(request, 'Login.html')


def login(request):
    if request.user.is_authenticated:
        return redirect('scenario:console')
    if request.method == 'POST':
        username = request.POST['username']
        password = request.POST['password']
        
        handler = AxesProxyHandler()
        
        if handler.is_locked(request):
            messages.error(
                request,
                'This account has been locked due to too many failed attempts. '
                'Please try again after 24 hours.'
            )
            return render(request, 'Login.html')

        user = auth.authenticate(request=request, username=username, password=password)
        
        if user is not None:
            auth.login(request, user)
            messages.success(request, 'You have successfully logged in.')
            return redirect('scenario:console')
        else:
            failures = handler.get_failures(request)
            attempts_remaining = 3 - failures 
            
            if attempts_remaining > 0:
                messages.warning(
                    request,
                    f'Invalid login credentials. {attempts_remaining} attempts remaining before account lockout.'
                )
            return render(request, 'Login.html')
            
    return render(request, 'Login.html')


def request_password_reset(request):
    if request.method == 'POST':
        username = request.POST.get('username')
        try:
            user = User.objects.get(username=username)
            pin = generate_code()
            expires_at = timezone.now() + datetime.timedelta(minutes=1)
            reset_request = PasswordResetRequest.objects.create(user=user, pin=pin, expires_at=expires_at)
            send_mail(
                'Password Reset PIN',
                f'Your PIN is: {pin}. It will expire in 1 minutes.',
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
            if confirm_password == new_password:
                reset_request = PasswordResetRequest.objects.get(user__username=username, pin=pin, used=False)
                if reset_request.is_valid():
                    user = reset_request.user
                    user.set_password(new_password)
                    user.save()
                    reset_request.used = True
                    reset_request.save()
                    update_session_auth_hash(request, user)
                    messages.success(request, "Password reset complete. Please login again.")
                    return redirect('account:login')
                else:
                    messages.error(request, 'Invalid or expired PIN')
                    return render(request, 'ConfirmPassword.html')
            else:
                messages.error(request, 'Confirm password and password not same')
                return render(request, 'ConfirmPassword.html')
        except PasswordResetRequest.DoesNotExist:
            messages.error(request, 'Invalid PIN or username')
            return render(request, 'ConfirmPassword.html')
    return render(request, 'ConfirmPassword.html')


def logout_use(request):
    logout(request)
    messages.success(request, "You have been successfully logged out.")
    return redirect('account:login')


def is_superuser(user):
    return user.is_superuser


@login_required
@user_passes_test(is_superuser)
def register_instructor(request):
    if request.method == 'POST':
        username = request.POST['staff_username']
        password = request.POST['staff_password']
        confirm_password = request.POST['staff_confirm_password']
        email = request.POST['staff_email']
        first_name = request.POST['staff_first_name']
        last_name = request.POST['staff_last_name']

        if password != confirm_password:
            messages.error(request, 'Passwords do not match')
            return redirect('account:register_Instructor')

        if User.objects.filter(username=username).exists():
            messages.error(request, 'Username already exists, choose another one')
            return redirect('account:register_Instructor')

        if User.objects.filter(email=email).exists():
            messages.error(request, 'Email already exists, choose another one')
            return redirect('account:register_Instructor')

        try:
            validate_password(password)
        except ValidationError as e:
            messages.error(request, ', '.join(e.messages))
            return redirect('account:register_Instructor')

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
        activation_url = request.build_absolute_uri(reverse('account:activate_Instructor'))

        context = {
            'username': username,
            'pin': pin,
            'activation_url': activation_url,
        }
        html_message = render_to_string('Admin/ActivePinPage.html', context)
        plain_message = strip_tags(html_message)

        send_mail(
            'Active Staff Account',
            plain_message,
            'lee',
            [user.email],
            html_message=html_message
        )

        messages.success(request, "Staff registration successful. An activation email has been sent.")
        return redirect('account:register_Instructor')

    return render(request, 'Admin/CreateInstructor.html')


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


@user_passes_test(is_superuser)
def instructor_list(request):
    staff_members = User.objects.filter(is_staff=True).exclude(is_superuser=True)
    context = {
        'staff_members': staff_members
    }
    return render(request, 'admin/InstructorList.html', context)


def btn_instructor_status(request, user_id):
    staff_member = get_object_or_404(User, id=user_id, is_staff=True)
    staff_member.is_active = not staff_member.is_active
    staff_member.save()
    status = "activated" if staff_member.is_active else "deactivated"
    messages.success(request, f'Staff member {staff_member.username} has been {status}.')
    return redirect('account:Instructor_list')


def handler404(request, exception):
    return render(request, '404.html')
