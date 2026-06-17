from django.core.management.base import BaseCommand
from django.contrib.auth.models import Group

class Command(BaseCommand):
    help = 'Crea los roles predeterminados para NeuroEsencia'

    def handle(self, *args, **kwargs):
        roles = ['Administrador', 'Psicólogo']

        for nombre in roles:
            grupo, creado = Group.objects.get_or_create(name=nombre)
            if creado:
                self.stdout.write(self.style.SUCCESS(f'Rol "{nombre}" creado.'))
            else:
                self.stdout.write(self.style.WARNING(f'El rol "{nombre}" ya existe.'))