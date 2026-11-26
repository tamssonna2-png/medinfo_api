from django.contrib.auth import authenticate, get_user_model
from rest_framework import serializers
from .models import Medicament
from .models import User

User = get_user_model()


class RegisterSerializer(serializers.ModelSerializer):
    email = serializers.EmailField(required=True)
    password = serializers.CharField(write_only=True, min_length=6)
    role = serializers.ChoiceField(choices=User.Role.choices, default=User.Role.USAGER)

    class Meta:
        model = User
        fields = ["id", "username", "email", "password", "role"]

    def validate_email(self, value):
        email = value.strip().lower()
        if User.objects.filter(email__iexact=email).exists():
            raise serializers.ValidationError("Un compte avec cet email existe déjà.")
        return email

    def create(self, validated_data):
        role = validated_data.get("role", User.Role.USAGER)
        # Pour le MVP de ce soir, est_valide est True par défaut ;
        # tu pourras restreindre l'ajout aux PRO validés quand tu le souhaites.
        user = User.objects.create_user(
            username=validated_data["username"],
            email=validated_data["email"],
            password=validated_data["password"],
            role=role,
            est_valide=True,
        )
        return user


class LoginSerializer(serializers.Serializer):
    username = serializers.CharField()
    password = serializers.CharField(write_only=True)

    def validate(self, data):
        identifier = data["username"].strip()
        password = data["password"]

        login_username = identifier
        if "@" in identifier:
            matched_user = User.objects.filter(email__iexact=identifier).first()
            if not matched_user:
                raise serializers.ValidationError("Identifiants invalides.")
            login_username = matched_user.username

        user = authenticate(username=login_username, password=password)
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




from django.shortcuts import get_object_or_404
from .notifications import notifier_admin_nouveau_pro, notifier_pro_decision


def _is_admin_user(user) -> bool:
    return bool(
        user
        and user.is_authenticated
        and (user.is_staff or user.is_superuser)
    )


def _serialize_pro_user(u: User) -> dict:
    return {
        "id": u.id,
        "username": u.username,
        "email": u.email,
        "first_name": u.first_name,
        "last_name": u.last_name,
        "role": u.role,
        "est_valide": u.est_valide,
        "statut_pro": u.statut_pro,
        "statut_pro_label": u.get_statut_pro_display(),
        "date_joined": u.date_joined,
        "is_active": u.is_active,
    }