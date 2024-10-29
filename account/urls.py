from django.urls import path, include
from . import views

app_name = 'account'

urlpatterns = [
    # Basic function
    path('', views.login, name='login'),
    path('register/', views.register, name='register'),
    path('console', views.console, name='console'),
    path('active/', views.activate_user, name='activate_user'),
    path('confirm-pin/', views.confirm_pin, name='confirm_pin'),
    path('forget_password', views.request_password_reset, name='forget_password'),
    path('logout/', views.logout_use, name='logout'),

    # Admin function
    path('admin/staff/', include([
        path('add/', views.register_instructor, name='register_Instructor'),
        path('activate/', views.activate_instructor, name='activate_Instructor'),
        path('list/', views.instructor_list, name='Instructor_list'),
        path('list/<int:user_id>/toggle/', views.btn_instructor_status, name='Btn_Instructor_Status'),
    ])),
]
