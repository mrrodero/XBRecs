from django.urls import path
from .views import SignupView, HomeView, RecommendView

urlpatterns = [
    path('signup/', SignupView.as_view(), name='signup'),
    path('', HomeView.as_view(), name='home'),
    path('recommend/', RecommendView.as_view(), name='recommend'),
]
