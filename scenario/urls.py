from django.urls import path, include
from scenario import views

app_name = 'scenario'

urlpatterns = [
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
        path('progress/', views.check_progress, name='check_progress'),

        # Steps management
        path('steps/', views.manage_steps, name='manage_steps'),
        path('steps/<int:step_id>/', include([
            path('edit/', views.edit_step, name='edit_step'),
            path('delete/', views.delete_step, name='delete_step'),
            path('complete/', views.complete_step, name='complete_step'),
        ])),

        # Container management
        path('container/', include([
            path('action/', views.container_action, name='container_action'),
            path('info/', views.container_info, name='container_info'),
        ])),
    ])),
]
