from django.urls import path
from panels import views_admin, views_admin_academic, views_analyst, views_notifications, views_student, views_teacher, views_theme

app_name = 'panels'

urlpatterns = [
    path('theme/preferences/', views_theme.theme_preferences_view, name='theme_preferences'),
    path('profile/', views_theme.user_profile_view, name='user_profile'),
    path('admin-panel/', views_admin.admin_dashboard, name='admin_dashboard'),
    path('admin-panel/users/', views_admin.admin_users, name='admin_users'),
    path('admin-panel/teachers/', views_admin_academic.admin_teachers, name='admin_teachers'),
    path('admin-panel/students/', views_admin_academic.admin_students, name='admin_students'),
    path('admin-panel/semesters/', views_admin_academic.admin_semesters, name='admin_semesters'),
    path('admin-panel/courses/', views_admin_academic.admin_courses, name='admin_courses'),
    path('admin-panel/password-requests/', views_admin_academic.admin_password_requests, name='admin_password_requests'),
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
    path('teacher-panel/courses/', views_teacher.teacher_courses, name='teacher_courses'),
    path('teacher-panel/students/', views_teacher.teacher_students, name='teacher_students'),
    path('teacher-panel/attendance/', views_teacher.teacher_attendance, name='teacher_attendance'),
    path('teacher-panel/tests/', views_teacher.teacher_tests, name='teacher_tests'),
    path('teacher-panel/tests/<str:test_id>/grade/', views_teacher.teacher_test_grade, name='teacher_test_grade'),
    path('teacher-panel/marks/', views_teacher.teacher_marks, name='teacher_marks'),
    path('student-panel/', views_student.student_dashboard, name='student_dashboard'),
    path('analyst-panel/', views_analyst.analyst_dashboard, name='analyst_dashboard'),
    path('analyst-panel/accuracy/', views_analyst.analyst_accuracy, name='analyst_accuracy'),
]
