from django.urls import path
from accounts import views

app_name = 'accounts'

urlpatterns = [
    path('auth/', views.auth_view, name='auth_view'),
    path('auth/approval-status/', views.approval_status_view, name='approval_status'),
    path('auth/logout/', views.logout_view, name='logout_view'),
]
