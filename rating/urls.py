from django.urls import path, include
from . import views

app_name = 'rating'

urlpatterns = [
    # Basic rating
    path('<int:scenario_id>/', views.rate_content, name='RateContent'),

    # Analytics
    path('analytics/', include([
        path('scenario/<int:scenario_id>/', views.get_scenario_analytics, name='scenario_analytics'),
        path('tutorial/<int:tutorial_id>/', views.get_tutorial_analytics, name='tutorial_analytics'),
    ])),

    # Check completion
    path('check-completion/<int:scenario_id>/', views.check_completion, name='CheckCompletion'),
]
