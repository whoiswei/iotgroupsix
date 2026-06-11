from django.urls import path
from . import views

urlpatterns = [
    path('', views.home, name='home'),
    path('logout/', views.logout_view, name='logout'),
    path('dashboard/', views.dashboard, name='dashboard'),
    
    # Creator urls
    path('creator/', views.creator_list, name='creator_list'),
    path('creator/new/', views.creator_form, name='creator_form'),
    path('creator/<int:project_id>/edit/', views.creator_form, name='creator_edit'),
    path('creator/<int:project_id>/delete/', views.creator_delete, name='creator_delete'),
    
    # Player urls
    path('player/', views.player_list, name='player_list'),
    path('player/play/<int:project_id>/', views.player_play, name='player_play'),
    
    # API endpoints for MQTT & Node-RED integration
    path('api/game/start/<int:project_id>/', views.api_start_game, name='api_start_game'),
    path('api/game/status/<int:session_id>/', views.api_game_status, name='api_game_status'),
    path('api/game/event/', views.api_game_event, name='api_game_event'),
]