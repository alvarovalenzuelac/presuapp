from rest_framework import serializers
from django.contrib.auth import get_user_model

# Obtenemos tu modelo UsuarioCustom de forma segura
User = get_user_model()

class UsuarioSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        # Agregamos 'email' (tu username), telefono y rol
        fields = ['id', 'email', 'first_name', 'last_name', 'numero_telefono', 'rol']