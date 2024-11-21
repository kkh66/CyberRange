from django.urls import path, include
from scenario import views

app_name = 'scenario'

urlpatterns = [
    # Add this at the top level
    path('console/', views.console_view, name='console'),
    # Scenario list and global operations
    path('all/', views.list_all_scenarios, name='list_all_scenarios'),
    path('group/<int:group_id>/', views.scenario_list, name='scenario_list'),
    path('group/<int:group_id>/create/', views.create_scenario, name='create_scenario'),

    # Specific scenario operations
    path('<int:scenario_id>/', include([
        path('', views.scenario_detail, name='scenario_detail'),
        path('edit/', views.edit_scenario, name='edit_scenario'),
        path('delete/', views.delete_scenario, name='delete_scenario'),
        path('start/', views.start_scenario, name='start_scenario'),

        path('rate/', views.rate_scenario, name='rate_scenario'),
        path('ratings/analytics/', views.rating_analytics, name='rating_analytics'),

        # Container management
        path('container/', include([
            path('action/', views.container_action, name='container_action'),
        ])),

        path('status/', views.get_container_status, name='container_status'),
    ])),
]
