"""
Pruebas del recomendador: ANN, cold start y precomputación.
"""

import numpy as np
import pytest

from application.models import EMBEDDING_DIM, Book, Rating, Recommendation, User
from application.recommend import (
    cold_start_recommendations,
    k_nearest,
    popular_books,
    recommend_books,
    recompute_recommendations,
    top_k_books,
)

pytestmark = pytest.mark.django_db


_COMP = {"a": 0, "b": 1}


def vec(dim=EMBEDDING_DIM, **components):
    v = np.zeros(dim, dtype=np.float32)
    for name, value in components.items():
        v[_COMP[name]] = value
    return v


def make_book(title, embedding=None):
    book = Book.objects.create(
        title=title, year=2000, isbn="0" * 13, cover="", description=""
    )
    if embedding is not None:
        book.set_embedding(embedding)
        book.save(update_fields=["embedding"])
    return book


def make_user(username, embedding):
    return User.objects.create_user(
        username=username, password="pass12345!", embedding=embedding
    )


@pytest.fixture
def users_books(db):
    """Tres usuarios con embeddings conocidos y varios libros."""
    alice = make_user("alice", vec(a=1.0))
    bob = make_user("bob", vec(a=0.9, b=0.1))
    carol = make_user("carol", vec(b=1.0))
    books = {
        "dune": make_book("Dune", vec(a=1.0)),
        # Embeddings con componente `a` para que, tras la recomputación
        # por señales (embedding = media de libros que gustan), la
        # similitud con alice siga siendo positiva.
        "neve": make_book("Neuromancer", vec(a=0.5, b=0.5)),
        "habitat": make_book("The Habitat", vec(a=0.5, b=0.5)),
    }
    return alice, bob, carol, books


class TestKNearest:
    def test_orders_by_cosine_similarity(self, users_books):
        alice, bob, carol, _ = users_books
        nearest = k_nearest(alice, 2)
        assert [u.pk for u, _ in nearest] == [bob.pk, carol.pk]
        sim_bob, sim_carol = (s for _, s in nearest)
        assert sim_bob > sim_carol

    def test_excludes_self(self, users_books):
        alice, _, _, _ = users_books
        nearest = k_nearest(alice, 10)
        assert all(u.pk != alice.pk for u, _ in nearest)

    def test_zero_embedding_returns_empty(self, db):
        user = User.objects.create_user(username="empty", password="pass12345!")
        assert k_nearest(user, 5) == []


class TestTopKBooks:
    def test_excludes_already_rated_books(self, users_books):
        alice, bob, _, books = users_books
        # Alice ha valorado Dune: debe quedar excluida de la predicción.
        Rating.objects.create(user=alice, book=books["dune"], rating=1.0)
        # Bob valoró Dune y Neuromancer.
        Rating.objects.create(user=bob, book=books["dune"], rating=1.0)
        Rating.objects.create(user=bob, book=books["neve"], rating=1.0)
        recs = top_k_books(alice, k_nearest(alice, 2), 5)
        assert [b.title for b, _ in recs] == ["Neuromancer"]

    def test_no_neighbors_returns_empty(self, users_books):
        alice, _, _, _ = users_books
        assert top_k_books(alice, [], 5) == []


class TestRecommendBooks:
    def test_returns_books_and_scores(self, users_books):
        alice, bob, _, books = users_books
        Rating.objects.create(user=bob, book=books["neve"], rating=1.0)
        recs = recommend_books(alice, n=2, k=5)
        assert len(recs) == 1
        assert recs[0][0].title == "Neuromancer"
        assert recs[0][1] > 0


def _extra_book():
    return make_book("Extra", vec(a=0.5, b=0.5))


class TestColdStart:
    def test_popular_books_for_empty_user(self, users_books):
        _, _, _, books = users_books
        # Dune es el más valorado.
        for _ in range(12):
            other = User.objects.create_user(
                username=f"u{User.objects.count()}", password="pass12345!"
            )
            Rating.objects.create(user=other, book=books["dune"], rating=1.0)
        recs = cold_start_recommendations(User.objects.filter(username="alice").first(), k=5)
        assert recs[0][0].title == "Dune"

    def test_popular_books_requires_minimum_ratings(self, users_books):
        _, _, _, books = users_books
        other = User.objects.create_user(username="u1", password="pass12345!")
        Rating.objects.create(user=other, book=books["dune"], rating=1.0)
        # Menos de 10 valoraciones: no es popular.
        assert popular_books(5) == []


class TestRecomputeRecommendations:
    def test_persists_recommendations(self, users_books):
        alice, bob, carol, books = users_books
        # Alice necesita >= MIN_RATINGS_FOR_CF valoraciones.
        for book in books.values():
            Rating.objects.create(user=alice, book=book, rating=1.0)
        # Bob y Carol valoran un libro extra que Alice no ha valorado.
        extra = _extra_book()
        Rating.objects.create(user=bob, book=extra, rating=1.0)
        Rating.objects.create(user=carol, book=extra, rating=1.0)
        recompute_recommendations(alice)
        recs = Recommendation.objects.filter(user=alice)
        assert recs.count() == 1
        assert recs.first().book == extra
        # Dune ya lo valoró Alice: no debe estar recomendado.
        assert not recs.filter(book=books["dune"]).exists()

    def test_cold_start_used_for_new_user(self, users_books):
        alice, _, _, books = users_books
        for _ in range(12):
            other = User.objects.create_user(
                username=f"u{User.objects.count()}", password="pass12345!"
            )
            Rating.objects.create(user=other, book=books["dune"], rating=1.0)
        recompute_recommendations(alice)
        recs = Recommendation.objects.filter(user=alice)
        assert recs.exists()
        assert recs.first().book.title == "Dune"
