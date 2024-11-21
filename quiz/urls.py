from django.urls import path
from . import views

app_name = 'quiz'

urlpatterns = [
    path('', views.quiz_list, name='ListQuiz'),
    path('create/<int:scenario_id>/', views.create_quiz, name='CreateQuiz'),
    path('<int:scenario_id>/delete/', views.quiz_delete, name='DeleteQuiz'),
    path('tutorial', views.list_tutorial, name='ListTutorial'),
    path('<int:scenario_id>/take/', views.take_quiz, name='TakeQuiz'),
]
