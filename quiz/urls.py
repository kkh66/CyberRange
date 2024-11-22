from django.urls import path
from . import views

app_name = 'quiz'

urlpatterns = [
    path('create/<int:scenario_id>/', views.create_quiz, name='CreateQuiz'),
    path('list/<int:scenario_id>/', views.quiz_list, name='ListQuiz'),
    path('take/<int:scenario_id>/', views.take_quiz, name='TakeQuiz'),
    path('delete/<int:scenario_id>/', views.quiz_delete, name='DeleteQuiz'),
    path('tutorial', views.list_tutorial, name='ListTutorial'),
    path('edit/<int:scenario_id>/', views.edit_quiz, name='EditQuiz'),
]
