from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):
    class Role(models.TextChoices):
        USAGER = "USAGER", "Usager"
        PRO = "PRO", "Professionnel de santé"

    role = models.CharField(
        max_length=10,
        choices=Role.choices,
        default=Role.USAGER,
    )
    est_valide = models.BooleanField(default=True)

    def save(self, *args, **kwargs):
        # Par défaut : un usager est actif/valide directement ;
        # un pro peut être créé en attente ou validé selon ton besoin de test ce soir.
        if not self.pk and self.role == self.Role.PRO and "est_valide" not in kwargs:
            pass
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.username} ({self.get_role_display()})"


class Medicament(models.Model):
    nom = models.CharField(max_length=255, db_index=True)
    dci = models.CharField(max_length=255, blank=True, default="")
    dosage = models.CharField(max_length=100, blank=True, default="")
    forme = models.CharField(max_length=100, blank=True, default="")
    posologie = models.TextField()
    effets_secondaires = models.TextField(blank=True, default="")
    contre_indications = models.TextField(blank=True, default="")
    interactions = models.TextField(blank=True, default="")
    ajoute_par = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="medicaments_ajoutes",
    )
    date_creation = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["nom"]

    def __str__(self):
        return f"{self.nom} ({self.dosage})".strip()