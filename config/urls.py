from django.contrib import admin
from django.urls import include, path, re_path
from accounts.views import error_404, root_redirect

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', root_redirect, name='root'),
    path('', include('accounts.urls')),
    path('', include('panels.urls')),
    path('', include('analytics.urls')),
    re_path(r'^(?!static/).*$', error_404, name='catch_all_404'),
]

handler404 = 'accounts.views.error_404'
