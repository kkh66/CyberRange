from django.urls import path, include
from . import views

app_name = 'group'

urlpatterns = [
    path('', views.group_list, name='group_list'),
    path('create/', views.create_group, name='create_group'),
    path('add/', views.add_group, name='add_group'),

    path('<int:group_id>/', include([
        path('', views.group_detail, name='group_detail'),
        path('edit/', views.edit_group, name='edit_group'),
        path('announcement/', views.create_announcement, name='create_announcement'),
        path('students/add/', views.add_students, name='add_students'),
        path('students/<int:student_id>/remove/', views.remove_student, name='remove_student'),


    ])),

]
