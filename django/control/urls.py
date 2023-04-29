from django.urls import path

from . import views

urlpatterns = [
    path("", views.index, name="index"),
    path("move", views.move, name="move"),
    path("video_feed", views.video_feed, name="video_feed")
]