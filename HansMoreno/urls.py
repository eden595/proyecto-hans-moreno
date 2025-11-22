from PanelAdmin.views import *
from django.contrib import admin
from django.urls import path

urlpatterns = [
    path('admin/', admin.site.urls),
    path('dashboard/', panel_dashboard,name='panel_dashboard'),
    path('rutas/',panel_rutas,name='panel_rutas'),
    path('vehiculos/',panel_vehiculos,name='panel_vehiculos'),
    path('combustible/',panel_combustible,name='panel_combustible'),
    path('reprotes/',panel_reportes,name='panel_reportes')


]
