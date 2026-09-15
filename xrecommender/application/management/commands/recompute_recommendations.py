"""
Recalcula las recomendaciones precalculadas.

Uso:

    python manage.py recompute_recommendations            # todos los usuarios
    python manage.py recompute_recommendations --user 42   # un usuario concreto
"""

from application.models import User
from application.recommend import recompute_recommendations
from django.core.management.base import BaseCommand, CommandError


class Command(BaseCommand):
    """Recalcula las recomendaciones de uno o todos los usuarios."""

    help = (
        "Recalcula las recomendaciones precalculadas de todos los usuarios "
        "o de un usuario concreto (--user)."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--user",
            type=int,
            default=None,
            help="Id del usuario a recalcular (por defecto, todos).",
        )

    def handle(self, *args, **options):
        user_id = options["user"]
        if user_id is not None:
            try:
                user = User.objects.get(pk=user_id)
            except User.DoesNotExist:
                raise CommandError(f"El usuario {user_id} no existe.")
            recompute_recommendations(user)
            self.stdout.write(self.style.SUCCESS(f"Usuario {user_id} recalculado."))
            return

        total = User.objects.count()
        self.stdout.write(f"Recalculando recomendaciones de {total} usuarios...")
        for i, user in enumerate(
            User.objects.order_by("id").iterator(chunk_size=500), 1
        ):
            recompute_recommendations(user)
            if i % 1000 == 0 or i == total:
                self.stdout.write(f"  {i}/{total} usuarios")
        self.stdout.write(self.style.SUCCESS("Recomendaciones recalculadas."))
