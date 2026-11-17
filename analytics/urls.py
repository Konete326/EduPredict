from django.urls import path
from analytics import views

app_name = 'analytics'

urlpatterns = [
    path('analyst-panel/upload/', views.upload_dataset, name='upload_dataset'),
    path('analyst-panel/run-ml/', views.run_predictions, name='run_predictions'),
    path('analyst-panel/evaluation/', views.model_evaluation, name='model_evaluation'),
]
