from django.urls import path
from panels import views_admin, views_analyst, views_notifications, views_student, views_teacher, views_theme

app_name = 'panels'

urlpatterns = [
    path('theme/preferences/', views_theme.theme_preferences_view, name='theme_preferences'),
    path('profile/', views_theme.user_profile_view, name='user_profile'),
    path('admin-panel/', views_admin.admin_dashboard, name='admin_dashboard'),
    path('admin-panel/users/', views_admin.admin_users, name='admin_users'),
    path('admin-panel/courses/', views_admin.admin_courses, name='admin_courses'),
    path('admin-panel/tickets/', views_admin.admin_tickets, name='admin_tickets'),
    path('admin-panel/logs/', views_admin.admin_logs, name='admin_logs'),
    path('admin-panel/settings/', views_admin.admin_settings, name='admin_settings'),
    path('admin-panel/backup/', views_admin.admin_backup_export, name='admin_backup_export'),
    path('support/submit/', views_admin.submit_support_ticket, name='submit_support_ticket'),
    path('notifications/', views_notifications.notifications_history_view, name='notifications_history'),
    path('notifications/mark-read/', views_admin.mark_notifications_read_view, name='mark_notifications_read'),
    path('notifications/feed/', views_notifications.notifications_feed_view, name='notifications_feed'),
    path('students/<str:student_id>/summary/', views_notifications.student_360_summary_view, name='student_360_summary'),
    path('teacher-panel/', views_teacher.teacher_dashboard, name='teacher_dashboard'),
    path('teacher-panel/students/', views_teacher.teacher_students, name='teacher_students'),
    path('teacher-panel/students/export-pdf/', views_teacher.teacher_roster_pdf, name='teacher_roster_pdf'),
    path('teacher-panel/alerts/', views_teacher.teacher_alerts, name='teacher_alerts'),
    path('teacher-panel/ingest/', views_teacher.teacher_ingest, name='teacher_ingest'),
    path('student-panel/', views_student.student_dashboard, name='student_dashboard'),
    path('student-panel/report/', views_student.student_report, name='student_report'),
    path('student-panel/report/download/', views_student.student_report_download, name='student_report_download'),
    path('student-panel/report/download-pdf/', views_student.student_report_pdf, name='student_report_pdf'),
    path('student-panel/tips/', views_student.student_tips, name='student_tips'),
    path('student-panel/notifications/', views_student.student_notifications, name='student_notifications'),
    path('analyst-panel/', views_analyst.analyst_dashboard, name='analyst_dashboard'),
    path('analyst-panel/accuracy/', views_analyst.analyst_accuracy, name='analyst_accuracy'),
]
