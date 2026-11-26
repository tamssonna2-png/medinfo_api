from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):
    class Role(models.TextChoices):
        USAGER = "USAGER", "Usager"
        PRO = "PRO", "Professionnel de santé"

    # MODIF : définition de StatutPro manquante
    class StatutPro(models.TextChoices):
        NON_APPLICABLE = "NONE", "Non applicable"
        EN_ATTENTE = "PENDING", "En attente de validation"
        VALIDE = "VERIFIED", "Vérifié"
        REFUSE = "REJECTED", "Refusé"

    email = models.EmailField(unique=True)
    role = models.CharField(
        max_length=10,
        choices=Role.choices,
        default=Role.USAGER,
    )
    est_valide = models.BooleanField(default=True)
    statut_pro = models.CharField(
        max_length=10,
        choices=StatutPro.choices,
        default=StatutPro.NON_APPLICABLE,
    )

    class Meta(AbstractUser.Meta):
        constraints = [
            models.UniqueConstraint(
                models.functions.Lower("email"),
                name="unique_lower_email",
            )
        ]

    def save(self, *args, **kwargs):
        if self.email:
            self.email = self.email.strip().lower()
        if not self.pk:
            if self.role == self.Role.PRO:
                self.est_valide = False
                if self.statut_pro == self.StatutPro.NON_APPLICABLE:
                    self.statut_pro = self.StatutPro.EN_ATTENTE
            else:
                self.est_valide = True
                self.statut_pro = self.StatutPro.NON_APPLICABLE

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