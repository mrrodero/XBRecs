from django.urls import path
from .views import (
    SignupView, HomeView, BookSearchView, DiscoverView,
    book_rate, book_rate_remove,
    BookDetailView,
    RecommendView, ProfileView
)

urlpatterns = [
    path('signup/', SignupView.as_view(), name='signup'),
    path('', HomeView.as_view(), name='home'),
    path('search/', BookSearchView.as_view(), name='search'),
    path('discover/', DiscoverView.as_view(), name='discover'),
    path('book-rate/<int:book_id>/', book_rate, name='book-rate'),
    path(
        'book-rate-remove/<int:book_id>/',
        book_rate_remove,
        name='book-rate-remove'
    ),
    path(
        'book-detail/<int:book_id>/',
        BookDetailView.as_view(),
        name='book-detail'
    ),
    path('recommend/<int:count>', RecommendView.as_view(), name='recommend'),
    path('profile/', ProfileView.as_view(), name='profile'),
]
