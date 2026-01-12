from django_filters.rest_framework import DjangoFilterBackend


class StrictDjangoFilterBackend(DjangoFilterBackend):
    raise_exception = True
