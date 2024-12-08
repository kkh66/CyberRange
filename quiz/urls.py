from django.urls import path, include
from . import views

app_name = 'quiz'

urlpatterns = [
    # Quiz management
    path('<int:scenario_id>/', include([
        path('', views.quiz_list, name='ListQuiz'),
        path('create/', views.create_quiz, name='CreateQuiz'),
        path('take/', views.take_quiz, name='TakeQuiz'),
        path('edit/', views.edit_quiz, name='EditQuiz'),
        path('delete/', views.quiz_delete, name='DeleteQuiz'),
        path('submit/', views.submit_quiz, name='SubmitQuiz'),
    ])),
    path('check-completion/<int:scenario_id>/', views.check_completion, name='CheckCompletion'),
]
