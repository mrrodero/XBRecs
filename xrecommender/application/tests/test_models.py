"""
Pruebas de los modelos: búsqueda FTS, constraints, señales y embeddings.
"""

import numpy as np
import pytest
from django.db import IntegrityError, transaction

from application.models import (
    EMBEDDING_DIM,
    Author,
    Book,
    Rating,
    User,
)

pytestmark = pytest.mark.django_db


def make_book(title, description="", embedding=None):
    book = Book.objects.create(
        title=title, year=2000, isbn="0" * 13, cover="", description=description
    )
    if embedding is not None:
        book.set_embedding(embedding)
        book.save(update_fields=["embedding"])
    return book


def make_user(username, embedding=None):
    user = User.objects.create_user(
        username=username, password="pass12345!", is_staff=False
    )
    if embedding is not None:
        user.set_embedding(embedding)
        user.save(update_fields=["embedding"])
    return user


def vec(x, dim=EMBEDDING_DIM):
    v = np.zeros(dim, dtype=np.float32)
    v[0] = x
    return v


class TestBookSearchText:
    def test_search_text_set_on_save(self):
        book = make_book("Dune", description="A desert planet saga.")
        assert "Dune" in book.search_text
        assert "A desert planet saga." in book.search_text

    def test_search_text_updated_on_author_change(self):
        book = make_book("Dune")
        author = Author.objects.create(name="Frank Herbert")
        book.authors.add(author)
        book.refresh_from_db()
        assert "Frank Herbert" in book.search_text


class TestFullTextSearch:
    def test_search_finds_books_and_highlights(self):
        make_book("Dune", description="The spice must flow on Arrakis.")
        make_book("Neuromancer", description="Cyberspace and hackers.")
        results = Book.objects.search("spice")
        assert len(results) == 1
        assert results[0].title == "Dune"
        assert results[0].search_rank > 0
        assert "<mark>" in results[0].search_headline

    def test_search_no_results(self):
        make_book("Dune", description="The spice must flow.")
        assert Book.objects.search("quantum") == []

    def test_search_plain_type_is_injection_safe(self):
        make_book("Dune", description="Test book.")
        # La sintaxis de tsquery no debe interpretarse.
        results = Book.objects.search("dune & nonexistingword")
        assert results == []


class TestRating:
    def test_unique_constraint_user_book(self):
        user = make_user("alice")
        book = make_book("Dune")
        Rating.objects.create(user=user, book=book, rating=1.0)
        with pytest.raises(IntegrityError), transaction.atomic():
            Rating.objects.create(user=user, book=book, rating=0.5)

    def test_get_book_rating_returns_none_when_missing(self):
        user = make_user("alice")
        book = make_book("Dune")
        assert user.get_book_rating(book) is None


class TestUserEmbeddingSignals:
    def test_embedding_created_from_liked_rating(self):
        user = make_user("alice")
        book = make_book("Dune", embedding=vec(1.0))
        Rating.objects.create(user=user, book=book, rating=1.0)
        user.refresh_from_db()
        assert user.sum_ratings == pytest.approx(1.0)
        assert np.allclose(user.get_embedding(), vec(1.0))

    def test_negative_rating_does_not_update_embedding(self):
        user = make_user("alice")
        book = make_book("Dune", embedding=vec(1.0))
        Rating.objects.create(user=user, book=book, rating=0.5)
        user.refresh_from_db()
        assert user.sum_ratings == 0.0
        assert not np.any(user.get_embedding())

    def test_embedding_updated_when_rating_changes(self):
        user = make_user("alice")
        book = make_book("Dune", embedding=vec(1.0))
        rating = Rating.objects.create(user=user, book=book, rating=1.0)
        rating.rating = 0.5  # pasa a no gustar
        rating.save()
        user.refresh_from_db()
        assert user.sum_ratings == 0.0
        assert not np.any(user.get_embedding())

    def test_embedding_removed_when_rating_deleted(self):
        user = make_user("alice")
        book = make_book("Dune", embedding=vec(1.0))
        rating = Rating.objects.create(user=user, book=book, rating=1.0)
        rating.delete()
        user.refresh_from_db()
        assert user.sum_ratings == 0.0
        assert not np.any(user.get_embedding())

    def test_embedding_is_weighted_mean_of_liked_books(self):
        user = make_user("alice")
        book_a = make_book("A", embedding=vec(1.0))
        book_b = make_book("B", embedding=vec(0.0))
        # book_b con un vector en la segunda dimensión
        vb = np.zeros(EMBEDDING_DIM, dtype=np.float32)
        vb[1] = 1.0
        book_b.set_embedding(vb)
        book_b.save(update_fields=["embedding"])
        Rating.objects.create(user=user, book=book_a, rating=1.0)
        Rating.objects.create(user=user, book=book_b, rating=0.75)
        user.refresh_from_db()
        expected = (1.0 * vec(1.0) + 0.75 * vb) / 1.75
        assert np.allclose(user.get_embedding(), expected, atol=1e-5)
        assert user.sum_ratings == pytest.approx(1.75)
