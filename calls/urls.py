from django.urls import path
from . import views

app_name = 'calls'

urlpatterns = [
    path('', views.calls_list, name='calls_list'),
    path('start/<int:user_id>/', views.initiate_call, name='initiate_call'),
    path('call/<int:call_id>/', views.view_call, name='view_call'),
    path('call/<int:call_id>/accept/', views.accept_call, name='accept_call'),
    path('call/<int:call_id>/reject/', views.reject_call, name='reject_call'),
    path('call/<int:call_id>/end/', views.end_call, name='end_call'),

    # Quick call initiation from chat (type-specific)
    path('with/<str:username>/audio/', views.call_with_friend_audio, name='call_with_friend_audio'),
    path('with/<str:username>/video/', views.call_with_friend_video, name='call_with_friend_video'),

    # Existing generic quick call initiation (kept for compatibility)
    path('with/<str:username>/', views.call_with_friend, name='call_with_friend'),

    path('api/incoming/', views.get_incoming_calls, name='get_incoming_calls'),

    # WebRTC signaling (MVP: REST + polling)
    path('api/<int:call_id>/signal/', views.call_signal, name='call_signal'),
]
