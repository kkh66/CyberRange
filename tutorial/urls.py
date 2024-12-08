from django.urls import path, include
from . import views

app_name = 'tutorial'

urlpatterns = [
    # Basic tutorial views
    path('<int:scenario_id>/', include([
        path('', views.view_tutorial, name='ViewTutorial'),
        path('list/', views.list_tutorials, name='ListTutorials'),
        path('create/', views.create_tutorial, name='CreateTutorial'),
    ])),

    # Section management
    path('section/', include([
        path('add/', views.add_section, name='AddSection'),
        path('edit/', views.edit_section, name='EditSection'),
        path('delete/<int:section_id>/', views.delete_section, name='DeleteSection'),
    ])),

    # Media management
    path('media/', include([
        path('upload/', views.upload_image, name='UploadImage'),
    ])),
]
