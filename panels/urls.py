from django.urls import path
from panels import views_admin, views_analyst, views_notifications, views_student, views_teacher, views_theme

app_name = 'panels'

urlpatterns = [
    path('theme/preferences/', views_theme.theme_preferences_view, name='theme_preferences'),
    path('profile/', views_theme.user_profile_view, name='user_profile'),
    path('admin-panel/', views_admin.admin_dashboard, name='admin_dashboard'),
    path('admin-panel/users/', views_admin.admin_users, name='admin_users'),
    path('admin-panel/training/', views_admin.admin_training, name='admin_training'),
    path('admin-panel/tickets/', views_admin.admin_tickets, name='admin_tickets'),
    path('admin-panel/settings/', views_admin.admin_settings, name='admin_settings'),
    path('admin-panel/backup/', views_admin.admin_backup_export, name='admin_backup_export'),
    path('support/submit/', views_admin.submit_support_ticket, name='submit_support_ticket'),
    path('notifications/', views_notifications.notifications_history_view, name='notifications_history'),
    path('notifications/mark-read/', views_admin.mark_notifications_read_view, name='mark_notifications_read'),
    path('notifications/feed/', views_notifications.notifications_feed_view, name='notifications_feed'),
    path('ai-agents/chat/', views_notifications.ai_agent_chat_view, name='ai_agent_chat'),
    path('students/<str:student_id>/summary/', views_notifications.student_360_summary_view, name='student_360_summary'),
    path('teacher-panel/', views_teacher.teacher_dashboard, name='teacher_dashboard'),
    path('student-panel/', views_student.student_dashboard, name='student_dashboard'),
    path('analyst-panel/', views_analyst.analyst_dashboard, name='analyst_dashboard'),
    path('analyst-panel/accuracy/', views_analyst.analyst_accuracy, name='analyst_accuracy'),
]
