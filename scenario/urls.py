from django.urls import path, include
from scenario import views

app_name = 'scenario'

urlpatterns = [
    # Global views
    path('', include([
        path('all/', views.list_all_scenarios, name='list_all_scenarios'),
        path('console/', views.console, name='console'),
    ])),

    # Group-specific operations
    path('group/<int:group_id>/', include([
        path('', views.scenario_list, name='scenario_list'),
        path('create/', views.create_scenario, name='create_scenario'),
    ])),

    # Scenario-specific operations
    path('<int:scenario_id>/', include([
        path('', views.scenario_detail, name='scenario_detail'),
        path('edit/', views.edit_scenario, name='edit_scenario'),
        path('delete/', views.delete_scenario, name='delete_scenario'),
        path('start/', views.start_scenario, name='start_scenario'),
        path('approve/<int:user_id>/', views.approve_scenario, name='approve_scenario'),
        path('description', views.scenario_description, name='ScenarioDescription'),
        path('details/', views.manage_scenario_description, name='ScenarioAddDescription'),

        # Container management
        path('container/', include([
            path('status/', views.get_container_status, name='container_status'),
            path('action/', views.container_action, name='container_action'),
        ])),
    ])),

    # Screenshot submission
    path('submit-screenshots/<int:scenario_id>/', views.submit_screenshots, name='submit_screenshots'),
]
