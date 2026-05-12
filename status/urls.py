from django.urls import path
from . import views

app_name = 'status'

urlpatterns = [
    path('', views.status_list, name='status_list'),
    path('create/', views.create_status, name='create_status'),
    path('<int:status_id>/', views.view_status, name='view_status'),
    path('<int:status_id>/mark-viewed/', views.mark_as_viewed, name='mark_as_viewed'),
    path('<int:status_id>/hide/', views.hide_status, name='hide_status'),
    path('user/<str:username>/', views.user_status_history, name='user_history'),
]
