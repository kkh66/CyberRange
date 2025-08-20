from django.urls import path, include
from . import views

app_name = 'account'
urlpatterns = [
    # Basic function
    path('', include([
        path('', views.login, name='login'),
        path('RequestActivation/', views.request_reactivation, name='RequestActivation'),
        path('Activate/', views.activate_user, name='activate_user'),
        path('Register/', views.register, name='register'),
        path('logout/', views.logout_use, name='logout'),
        path('ForgetPassword', views.request_password_reset, name='forget_password'),
        path('ConfirmPin/', views.confirm_pin, name='confirm_pin'),
        path('ReActiviate/', views.reactivate_account, name='ReactivateAccount'),

    ])),
    # Admin function
    path('admin/staff/', include([
        path('add/', views.register_instructor, name='RegisterInstructor'),
        path('activate/', views.activate_instructor, name='ActivateInstructor'),
        path('list/', views.instructor_list, name='InstructorList'),
        path('list/<int:user_id>/toggle/', views.btn_instructor_status, name='Btn_Instructor_Status'),
    ])),
]
