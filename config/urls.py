from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/webhooks/', include('webhooks.urls')),
    path('api/', include('teams.urls')),
]
