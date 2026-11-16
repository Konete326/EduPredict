from django.urls import path
from panels import views_admin, views_analyst, views_student, views_teacher

app_name = 'panels'

urlpatterns = [
    path('admin-panel/', views_admin.admin_dashboard, name='admin_dashboard'),
    path('admin-panel/users/', views_admin.admin_users, name='admin_users'),
    path('admin-panel/courses/', views_admin.admin_courses, name='admin_courses'),
    path('admin-panel/tickets/', views_admin.admin_tickets, name='admin_tickets'),
    path('teacher-panel/', views_teacher.teacher_dashboard, name='teacher_dashboard'),
    path('teacher-panel/students/', views_teacher.teacher_students, name='teacher_students'),
    path('teacher-panel/ingest/', views_teacher.teacher_ingest, name='teacher_ingest'),
    path('student-panel/', views_student.student_dashboard, name='student_dashboard'),
    path('student-panel/report/', views_student.student_report, name='student_report'),
    path('analyst-panel/', views_analyst.analyst_dashboard, name='analyst_dashboard'),
]
