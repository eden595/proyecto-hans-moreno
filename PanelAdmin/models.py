from django.db import models


class Usuario(models.Model):
    id_usuario = models.AutoField(primary_key=True)
    nombre = models.CharField(max_length=100)
    correo = models.CharField(max_length=150)
    telefono = models.CharField(max_length=20, blank=True, null=True)
    rut = models.CharField(max_length=20)
    pin_hash = models.CharField(max_length=255)
    rol = models.CharField(max_length=50)
    fecha_creacion = models.DateTimeField()

    class Meta:
        managed = False          # Django NO crea ni modifica esta tabla
        db_table = 'Usuarios'    # nombre EXACTO de la tabla en la BD

    def __str__(self):
        return self.nombre


class Vehiculo(models.Model):
    id_vehiculo = models.AutoField(primary_key=True)
    patente = models.CharField(max_length=20)
    modelo = models.CharField(max_length=100)
    conductor = models.ForeignKey(
        Usuario,
        models.DO_NOTHING,
        db_column='conductor_id',
        blank=True,
        null=True,
        related_name='vehiculos'
    )
    kilometraje = models.IntegerField()
    fecha_creacion = models.DateTimeField()

    class Meta:
        managed = False
        db_table = 'Vehiculos'

    def __str__(self):
        return f"{self.patente} - {self.modelo}"


class Recorrido(models.Model):
    id_recorrido = models.AutoField(primary_key=True)
    conductor = models.ForeignKey(
        Usuario,
        models.DO_NOTHING,
        db_column='id_conductor',
        related_name='recorridos'
    )
    vehiculo = models.ForeignKey(
        Vehiculo,
        models.DO_NOTHING,
        db_column='id_vehiculo',
        related_name='recorridos'
    )
    fecha = models.DateField()
    hora_inicio = models.TimeField()
    hora_fin = models.TimeField()
    kilometraje_inicio = models.IntegerField()
    kilometraje_fin = models.IntegerField()
    ubicacion_inicio_txt = models.CharField(max_length=255)
    ubicacion_fin_txt = models.CharField(max_length=255)

    class Meta:
        managed = False
        db_table = 'Recorridos'

    @property
    def distancia(self):
        """Distancia recorrida en km (simple: fin - inicio)."""
        try:
            return self.kilometraje_fin - self.kilometraje_inicio
        except TypeError:
            return None

    def __str__(self):
        return f"Recorrido {self.id_recorrido}"
