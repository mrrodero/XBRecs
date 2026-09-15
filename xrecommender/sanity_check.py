"""
Verificación de humo con datos reales (base de datos de desarrollo).

Uso:
    python manage.py shell < sanity_check.py   (o ejecutar con python)
"""

from django.conf import settings
from django.db import connection
from django.test import Client

from application.models import Book, Rating, Recommendation, User
from application.recommend import (
    cold_start_recommendations,
    recommend_books,
)
from application.xai import get_explanation

print("=" * 60)
print("SANEITY CHECK — datos reales")
print("=" * 60)

# En este entorno los workers paralelos de Postgres se cuelgan; se
# desactivan para la sesión.
with connection.cursor() as cur:
    cur.execute("SET max_parallel_workers_per_gather = 0")

# 1. Conteos.
print(
    f"libros={Book.objects.count()} usuarios={User.objects.count()} "
    f"ratings={Rating.objects.count()} recs={Recommendation.objects.count()}"
)

# 2. Búsqueda a texto completo (FTS).
results = Book.objects.search("dune", limit=5)
print(f"FTS 'dune': {len(results)} resultados")
for b in results[:3]:
    print(f"  - {b.title} (headline: {str(b.search_headline)[:60]}...)")

# 3. Recomendaciones colaborativas (usuario con muchas valoraciones).
from django.db.models import Count

user = User.objects.annotate(n=Count("ratings")).order_by("-n").first()
print(f"\nUsuario {user.pk} ({user.username}): {user.n} valoraciones")
recs = Recommendation.objects.filter(user=user).order_by("-score")[:5]
print(f"Recomendaciones persistidas: {recs.count()}")
for r in recs:
    print(f"  - {r.book.title} (score={r.score:.2f})")

# 4. Modelo en vivo (debe coincidir con lo persistido).
live = recommend_books(user, n=35, k=5)
print(f"Recomendaciones en vivo: {len(live)}")
for b, s in live[:3]:
    print(f"  - {b.title} (score={s:.2f})")

# 5. Cold start (usuario nuevo sin valoraciones).
new_user = User.objects.create(username="nuevo_sanity")
cold = cold_start_recommendations(new_user, k=5)
print(f"\nCold start (usuario nuevo): {len(cold)} recomendaciones")
for b, s in cold[:3]:
    print(f"  - {b.title} (score={s:.2f})")

# 6. Explicación (keywords, sin LLM).
if recs:
    expl = get_explanation(user, recs[0].book)
    print(f"\nExplicación para '{recs[0].book.title}':")
    print(f"  {expl[:200]}")

# 7. Vistas web (client de Django).
settings.ALLOWED_HOSTS = [*settings.ALLOWED_HOSTS, "testserver"]
client = Client()
client.force_login(user)
for url in [
    "/",
    "/application/search/?q=dune",
    "/application/discover/",
    "/application/recommend/10/",
    "/application/profile/",
]:
    resp = client.get(url)
    print(f"GET {url} -> {resp.status_code}")

new_user.delete()
print("\nOK — sanity check completado.")
