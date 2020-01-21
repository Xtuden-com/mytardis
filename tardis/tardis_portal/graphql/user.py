import graphene
from graphene import Node
from graphene_django import DjangoObjectType

import graphql_jwt

from django.contrib.auth.models import User

from .utils import ExtendedConnection


class UserType(DjangoObjectType):
    class Meta:
        model = User
        fields = ('id', 'username', 'first_name', 'last_name', 'email')
        interfaces = (Node,)
        connection_class = ExtendedConnection


class UserSignIn(graphql_jwt.JSONWebTokenMutation):
    user = graphene.Field(UserType)

    @classmethod
    def resolve(cls, root, info, **kwargs):
        return cls(user=info.context.user)
