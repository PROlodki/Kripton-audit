from rest_framework import serializers
from django.contrib.auth import authenticate

from .models import User

class RegistrationSerializer(serializers.ModelSerializer):

    password = serializers.CharField(
        max_length=128,
        min_length=8,
        write_only=True
    )

    token = serializers.CharField(max_length=255, read_only=True)

class Meta:
    model = User
    fields = ['email', 'username', 'password', 'token']

    def create(self, validate_data):
        return User.objects.create_user(**validate_data)


class LoginSerialiser(serializers.Serializer):
    email = serializers.CharField(max_length=255)
    username = serializers.CharField(max_length=255, read_only=True)
    password = serializers.CharField(max_length=255, write_only=True)
    token = serializers.CharField(max_length=255, read_only=True)
    print(username,email,password,token)
    def validate(self, data):
        email = data.get('email', None)
        password = data.get('password', None)
        username = data.get('username', None)
        if password is None:
            raise serializers.ValidationError(
                'A password is required to log in.'
            )
        user = authenticate(username=username, password=password)

        if user is None:
            raise serializers.ValidationError(
                'A user with this username and password was not found.'
            )
        if not user.is_active:
            raise serializers.ValidationError(
                'This user not active'
            )

        return {
            'email': user.email,
            'username': user.username,
            'token': user.token
        }