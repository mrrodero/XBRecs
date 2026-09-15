"""
Pruebas de las vistas: búsqueda FTS, paginación, valoraciones y
recomendaciones.
"""

import pytest
from django.test import Client

from application.models import Book, Explanation, Rating, User

pytestmark = pytest.mark.django_db


@pytest.fixture
def client_with_user(db):
    """Cliente autenticado como un usuario con libros valorados."""
    user = User.objects.create_user(
        username="alice", password="pass12345!"
    )
    books = [
        Book.objects.create(
            title=f"Book {i}",
            year=2000,
            isbn=str(i) * 13,
            cover="",
            description=f"Description of book number {i}.",
        )
        for i in range(5)
    ]
    for i, book in enumerate(books):
        Rating.objects.create(user=user, book=book, rating=1.0)
    client = Client()
    assert client.login(username="alice", password="pass12345!")
    return client, user, books


class TestSearchView:
    def test_requires_login(self, db):
        client = Client()
        response = client.get("/application/search/?q=dune")
        assert response.status_code == 302
        assert "/login" in response["Location"]

    def test_returns_results_with_highlight(self, client_with_user):
        client, _, _ = client_with_user
        response = client.get("/application/search/?q=book")
        assert response.status_code == 200
        assert b"Book 1" in response.content
        assert b"<mark>" in response.content

    def test_empty_query_shows_no_results(self, client_with_user):
        client, _, _ = client_with_user
        response = client.get("/application/search/")
        assert response.status_code == 200
        assert b"No se han encontrado" in response.content


class TestDiscoverView:
    def test_paginates(self, client_with_user):
        client, _, _ = client_with_user
        # 5 libros + 20 más para forzar más de una página (PAGE_SIZE=20).
        for i in range(20):
            Book.objects.create(
                title=f"Extra {i}",
                year=2001,
                isbn=str(i % 10) * 13,
                cover="",
                description="",
            )
        response = client.get("/application/discover/")
        assert response.status_code == 200
        assert response.context["paginator"].num_pages == 2
        response2 = client.get("/application/discover/?page=2")
        assert response2.status_code == 200
        assert len(response2.context["books"]) == 5


class TestBookRate:
    def test_invalid_rating_rejected(self, client_with_user):
        client, _, books = client_with_user
        response = client.post(
            f"/application/book-rate/{books[0].id}/",
            {"rating": 9},
            headers={"X-Requested-With": "XMLHttpRequest"},
        )
        assert response.status_code == 400

    def test_non_ajax_rejected(self, client_with_user):
        client, _, books = client_with_user
        response = client.post(
            f"/application/book-rate/{books[0].id}/", {"rating": 5}
        )
        assert response.status_code == 400

    def test_creates_and_updates_rating(self, client_with_user):
        client, user, books = client_with_user
        book = books[0]
        response = client.post(
            f"/application/book-rate/{book.id}/",
            {"rating": 3},  # 3 estrellas -> 0.5
            headers={"X-Requested-With": "XMLHttpRequest"},
        )
        assert response.status_code == 200
        rating = Rating.objects.get(user=user, book=book)
        assert rating.rating == pytest.approx(0.5)
        # La señal recalculó el estado del usuario (0.5 < LIKES).
        user.refresh_from_db()
        assert user.sum_ratings == pytest.approx(4 * 1.0)  # los otros 4 libros

    def test_remove_rating(self, client_with_user):
        client, user, books = client_with_user
        book = books[0]
        response = client.post(
            f"/application/book-rate-remove/{book.id}/",
            headers={"X-Requested-With": "XMLHttpRequest"},
        )
        assert response.status_code == 200
        assert not Rating.objects.filter(user=user, book=book).exists()

    def test_remove_missing_rating_404(self, client_with_user):
        client, _, _ = client_with_user
        book = Book.objects.create(
            title="Unread", year=2000, isbn="9" * 13, cover="", description=""
        )
        response = client.post(
            f"/application/book-rate-remove/{book.id}/",
            headers={"X-Requested-With": "XMLHttpRequest"},
        )
        assert response.status_code == 404


class TestRecommendView:
    def test_shows_recommendations_and_explanations(self, client_with_user):
        client, user, _ = client_with_user
        # Un libro popular (12 valoraciones) que alice NO ha valorado.
        popular = Book.objects.create(
            title="Popular", year=2000, isbn="1" * 13, cover="", description=""
        )
        for i in range(12):
            other = User.objects.create_user(
                username=f"other{i}", password="pass12345!"
            )
            Rating.objects.create(user=other, book=popular, rating=1.0)
        response = client.get("/application/recommend/10/")
        assert response.status_code == 200
        # Sin vecinos con embedding, el cold start (popular) recomienda.
        assert b"Popular" in response.content
        assert Explanation.objects.filter(user=user, book=popular).exists()
        assert b"Por qu" in response.content  # "Por qué te lo recomendamos"

    def test_requires_login(self, db):
        client = Client()
        response = client.get("/application/recommend/10/")
        assert response.status_code == 302
        assert "/login" in response["Location"]


class TestProfileView:
    def test_shows_read_books_with_ratings(self, client_with_user):
        client, _, books = client_with_user
        response = client.get("/application/profile/")
        assert response.status_code == 200
        assert response.context["user_ratings"] == {
            book.id: 5 for book in books
        }
