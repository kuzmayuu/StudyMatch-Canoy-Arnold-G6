from django.urls import path

from . import views

app_name = "matching"

urlpatterns = [
    # Administrator: subject catalog
    path("subjects/", views.subject_list, name="subject_list"),
    path("subjects/new/", views.subject_create, name="subject_create"),
    path("subjects/<int:pk>/edit/", views.subject_edit, name="subject_edit"),
    path("subjects/<int:pk>/delete/", views.subject_delete, name="subject_delete"),
    # Student: profile data used for matching
    path("my-subjects/", views.my_subjects, name="my_subjects"),
    path("my-subjects/<int:pk>/remove/", views.my_subject_remove, name="my_subject_remove"),
    path("availability/", views.availability_list, name="availability_list"),
    path("availability/<int:pk>/edit/", views.availability_edit, name="availability_edit"),
    path("availability/<int:pk>/delete/", views.availability_delete, name="availability_delete"),
    path("preferences/", views.preferences, name="preferences"),
]
