from PanelAdmin.views import *
from django.contrib import admin
from django.urls import path
from django.contrib.auth import views as auth_views

urlpatterns = [
    path('admin/', admin.site.urls),
    
    # Login y Logout
    path('login/', auth_views.LoginView.as_view(template_name='PanelAdmin/login.html'), name='login'),
    path('logout/', auth_views.LogoutView.as_view(next_page='login'), name='logout'),

    # --- RUTA API GPS (Ahora sí funcionará porque views.py ya la tiene) ---
    path('api/gps/update/', update_gps_location, name='api_gps_update'),

    # Rutas del Panel
    path('', panel_dashboard, name='home'),
    path('dashboard/', panel_dashboard, name='panel_dashboard'),
    path('rutas/', panel_rutas, name='panel_rutas'),
    path('vehiculos/', panel_vehiculos, name='panel_vehiculos'),
    path('combustible/', panel_combustible, name='panel_combustible'),
    path('reportes/', panel_reportes, name='panel_reportes'),
    path('conductores/', panel_conductores, name='panel_conductores'),
    
    # Acciones
    path('reportes/pdf/', generar_pdf_reporte, name='generar_pdf'),
    path('eliminar/ruta/<int:id>/', eliminar_ruta, name='eliminar_ruta'),
    path('eliminar/combustible/<int:id>/', eliminar_combustible, name='eliminar_combustible'),
]