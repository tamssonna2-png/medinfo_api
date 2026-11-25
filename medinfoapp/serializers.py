from django.contrib.auth import authenticate, get_user_model
from rest_framework import serializers
from .models import Medicament

User = get_user_model()


class RegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, min_length=6)
    role = serializers.ChoiceField(choices=User.Role.choices, default=User.Role.USAGER)

    class Meta:
        model = User
        fields = ["id", "username", "email", "password", "role"]

    def create(self, validated_data):
        role = validated_data.get("role", User.Role.USAGER)
        # Pour le MVP de ce soir, est_valide est True par défaut ;
        # tu pourras restreindre l'ajout aux PRO validés quand tu le souhaites.
        user = User.objects.create_user(
            username=validated_data["username"],
            email=validated_data.get("email", ""),
            password=validated_data["password"],
            role=role,
            est_valide=True,
        )
        return user


class LoginSerializer(serializers.Serializer):
    username = serializers.CharField()
    password = serializers.CharField(write_only=True)

    def validate(self, data):
        user = authenticate(username=data["username"], password=data["password"])
        if not user:
            raise serializers.ValidationError("Identifiants invalides.")
        if not user.is_active:
            raise serializers.ValidationError("Compte désactivé.")
        data["user"] = user
        return data


class MedicamentSerializer(serializers.ModelSerializer):
    ajoute_par_username = serializers.CharField(source="ajoute_par.username", read_only=True)

    class Meta:
        model = Medicament
        fields = [
            "id",
            "nom",
            "dci",
            "dosage",
            "forme",
            "posologie",
            "effets_secondaires",
            "contre_indications",
            "interactions",
            "ajoute_par",
            "ajoute_par_username",
            "date_creation",
        ]
        read_only_fields = ["id", "ajoute_par", "ajoute_par_username", "date_creation"]