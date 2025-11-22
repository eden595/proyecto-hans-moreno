from django.db import models

class Usuario(models.Model):
    id_usuario = models.AutoField(primary_key=True)
    nombre = models.CharField(max_length=100)
    correo = models.CharField(unique=True, max_length=100)
    telefono = models.CharField(max_length=20, blank=True, null=True)
    rut = models.CharField(unique=True, max_length=15, blank=True, null=True)
    pin_hash = models.CharField(max_length=255)
    rol = models.CharField(max_length=50, blank=True, null=True)
    fecha_creacion = models.DateTimeField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'Usuarios'

    def save(self, *args, **kwargs):
        if self.rol:
            self.rol = self.rol.upper()
        super(Usuario, self).save(*args, **kwargs)

    def __str__(self):
        return self.nombre


class Vehiculo(models.Model):
    id_vehiculo = models.AutoField(primary_key=True)
    patente = models.CharField(unique=True, max_length=20)
    modelo = models.CharField(max_length=100)
    conductor = models.ForeignKey(Usuario, models.DO_NOTHING, blank=True, null=True, db_column='conductor_id')
    kilometraje = models.IntegerField()
    fecha_creacion = models.DateTimeField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'Vehiculos'

    def __str__(self):
        return f"{self.patente} - {self.modelo}"


class Recorrido(models.Model):
    id_recorrido = models.AutoField(primary_key=True)
    conductor = models.ForeignKey(Usuario, models.DO_NOTHING, db_column='id_conductor')
    vehiculo = models.ForeignKey(Vehiculo, models.DO_NOTHING, db_column='id_vehiculo')
    fecha = models.DateField()
    hora_inicio = models.TimeField()
    hora_fin = models.TimeField(blank=True, null=True)
    kilometraje_inicio = models.IntegerField(blank=True, null=True)
    kilometraje_fin = models.IntegerField(blank=True, null=True)
    ubicacion_inicio_txt = models.CharField(max_length=255, blank=True, null=True)
    ubicacion_fin_txt = models.CharField(max_length=255, blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'Recorridos'
    
    @property
    def distancia(self):
        if self.kilometraje_fin and self.kilometraje_inicio:
            return self.kilometraje_fin - self.kilometraje_inicio
        return 0


class CargaCombustible(models.Model):
    id_carga = models.AutoField(primary_key=True)
    vehiculo = models.ForeignKey(Vehiculo, models.DO_NOTHING, db_column='id_vehiculo')
    litros = models.FloatField()
    costo_total = models.IntegerField()
    fecha = models.DateField()
    hora = models.TimeField()
    
    class Meta:
        managed = False 
        db_table = 'CargaCombustible'