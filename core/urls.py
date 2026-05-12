from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    path('admin/', admin.site.urls),
    path('accounts/', include('django.contrib.auth.urls')),
    path('chat/', include('chatkit.urls')),
    path('status/', include('status.urls')),
    path('calls/', include('calls.urls')),
]
