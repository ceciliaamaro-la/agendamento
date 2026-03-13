from django.urls import path
from . import views

urlpatterns = [

    path(
        "criar-instancia/",
        views.criar_instancia
    ),

]