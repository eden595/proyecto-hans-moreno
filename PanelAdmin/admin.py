from django.contrib import admin
from .models import Usuario, Vehiculo, Recorrido, CargaCombustible

class UsuarioAdmin(admin.ModelAdmin):
    list_display = ('id_usuario', 'nombre', 'rol', 'correo')
    search_fields = ('nombre', 'rut')

class VehiculoAdmin(admin.ModelAdmin):
    list_display = ('patente', 'modelo', 'conductor', 'kilometraje')
    search_fields = ('patente',)

class RecorridoAdmin(admin.ModelAdmin):
    list_display = ('fecha', 'vehiculo', 'conductor', 'distancia')
    list_filter = ('fecha',)

class CargaCombustibleAdmin(admin.ModelAdmin):
    list_display = ('fecha', 'vehiculo', 'litros', 'costo_total')
    list_filter = ('fecha', 'vehiculo')

admin.site.register(Usuario, UsuarioAdmin)
admin.site.register(Vehiculo, VehiculoAdmin)
admin.site.register(Recorrido, RecorridoAdmin)
admin.site.register(CargaCombustible, CargaCombustibleAdmin)