from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.mail import send_mail

User = get_user_model()


def notifier_admin_nouveau_pro(user) -> None:
    admin_emails = list(
        User.objects.filter(is_superuser=True, is_active=True)
        .exclude(email="")
        .values_list("email", flat=True)
    )
    extra_email = getattr(settings, "ADMIN_NOTIFICATION_EMAIL", None)
    if extra_email:
        admin_emails.append(extra_email)

    recipients = list({email.strip().lower() for email in admin_emails if email})
    if not recipients:
        return

    send_mail(
        subject="[MEDINFO] Nouvelle demande de compte Professionnel de santé (PRO)",
        message=(
            "Une nouvelle demande de compte PRO a été enregistrée :\n\n"
            f"ID utilisateur : {user.id}\n"
            f"Nom d'utilisateur : {user.username}\n"
            f"Email : {user.email}\n"
            f"Statut actuel : {user.get_statut_pro_display()}\n"
            f"Compte validé : {'Oui' if user.est_valide else 'Non'}\n\n"
            "Connectez-vous à l'administration pour vérifier le dossier et accepter ou refuser."
        ),
        from_email=getattr(settings, "DEFAULT_FROM_EMAIL", None),
        recipient_list=recipients,
        fail_silently=True,
    )


def notifier_pro_decision(user, accepte: bool) -> None:
    if not user.email:
        return

    if accepte:
        sujet = "[MEDINFO] Votre compte Professionnel de santé est vérifié"
        message = (
            f"Bonjour {user.username},\n\n"
            "Bonne nouvelle : votre demande de compte Professionnel de santé (PRO) a été acceptée par l'administrateur.\n"
            "Votre compte est désormais certifié vérifié et vous pouvez ajouter des médicaments sur MEDINFO."
        )
    else:
        sujet = "[MEDINFO] Demande de compte Professionnel de santé refusée"
        message = (
            f"Bonjour {user.username},\n\n"
            "Votre demande de compte Professionnel de santé (PRO) a été refusée après vérification par l'administrateur.\n"
            "Votre compte reste non vérifié et ne peut pas publier de médicaments."
        )

    send_mail(
        subject=sujet,
        message=message,
        from_email=getattr(settings, "DEFAULT_FROM_EMAIL", None),
        recipient_list=[user.email],
        fail_silently=True,
    )