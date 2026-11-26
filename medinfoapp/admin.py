from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin

from .models import Medicament, User
from .notifications import notifier_pro_decision


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    list_display = (
        "username",
        "email",
        "role",
        "statut_pro",
        "est_valide",
        "is_staff",
        "date_joined",
    )
    list_filter = ("role", "statut_pro", "est_valide", "is_staff")
    search_fields = ("username", "email")
    actions = ["accepter_comptes_pro", "refuser_comptes_pro"]

    fieldsets = BaseUserAdmin.fieldsets + (
        (
            "Validation Professionnel de santé (MEDINFO)",
            {
                "fields": ("role", "statut_pro", "est_valide"),
            },
        ),
    )

    @admin.action(description="Accepter et vérifier les comptes PRO sélectionnés")
    def accepter_comptes_pro(self, request, queryset):
        pros = queryset.filter(role=User.Role.PRO)
        compteur = 0
        for user in pros:
            user.est_valide = True
            user.statut_pro = User.StatutPro.VALIDE
            user.save(update_fields=["est_valide", "statut_pro"])
            notifier_pro_decision(user, accepte=True)
            compteur += 1
        self.message_user(request, f"{compteur} compte(s) PRO accepté(s) et notifié(s).")

    @admin.action(description="Refuser les comptes PRO sélectionnés")
    def refuser_comptes_pro(self, request, queryset):
        pros = queryset.filter(role=User.Role.PRO)
        compteur = 0
        for user in pros:
            user.est_valide = False
            user.statut_pro = User.StatutPro.REFUSE
            user.save(update_fields=["est_valide", "statut_pro"])
            notifier_pro_decision(user, accepte=False)
            compteur += 1
        self.message_user(request, f"{compteur} compte(s) PRO refusé(s) et notifié(s).")

    def save_model(self, request, obj, form, change):
        ancien_statut = None
        if change and obj.pk:
            ancien = User.objects.filter(pk=obj.pk).first()
            if ancien:
                ancien_statut = ancien.statut_pro

        if obj.role == User.Role.PRO:
            if "statut_pro" in form.changed_data:
                obj.est_valide = obj.statut_pro == User.StatutPro.VALIDE
            elif "est_valide" in form.changed_data:
                obj.statut_pro = (
                    User.StatutPro.VALIDE if obj.est_valide else User.StatutPro.REFUSE
                )

        super().save_model(request, obj, form, change)

        if change and obj.role == User.Role.PRO and obj.statut_pro != ancien_statut:
            if obj.statut_pro == User.StatutPro.VALIDE:
                notifier_pro_decision(obj, accepte=True)
            elif obj.statut_pro == User.StatutPro.REFUSE:
                notifier_pro_decision(obj, accepte=False)


@admin.register(Medicament)
class MedicamentAdmin(admin.ModelAdmin):
    list_display = ("nom", "dci", "dosage", "forme", "ajoute_par", "date_creation")
    search_fields = ("nom", "dci")