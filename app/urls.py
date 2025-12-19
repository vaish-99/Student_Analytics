from django.urls import path
from . import views

urlpatterns = [
    path('', views.home, name='home'),
    path('register/', views.register, name='register'),
    path('login/', views.user_login, name='login'),
    path('dashboard/', views.dashboard, name='dashboard'),
    path('learning/', views.learning_module, name='learning'),
    path('analytics/', views.engagement, name='engagement'),
    # Learning data CRUD API
    path('learning/api/create/', views.learning_create, name='learning_create'),
    path('learning/api/update/<int:pk>/', views.learning_update, name='learning_update'),
    path('learning/api/delete/<int:pk>/', views.learning_delete, name='learning_delete'),
    path('learning/api/list/', views.learning_list, name='learning_list'),
    path('logout/', views.user_logout, name='logout'),
]
