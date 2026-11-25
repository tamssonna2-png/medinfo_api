import base64
import os
import time
import requests
from django.db.models import Q
from rest_framework import status
from rest_framework.authtoken.models import Token
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import Medicament
from .serializers import LoginSerializer, MedicamentSerializer, RegisterSerializer

AVERTISSEMENT_MEDICAL = (
    "Information générale uniquement : ne remplace pas l'avis d'un médecin ou d'un pharmacien. "
    "En cas de doute, symptômes graves, grossesse, enfant en bas âge ou traitement en cours, "
    "consultez un professionnel de santé."
)

FALLBACK_MODELS = [
    "gemini-3.1-flash-lite",
    "gemini-3.5-flash-lite",
    "gemini-3.8-flash",
    "gemini-3.7-flash",
    "gemini-flash-latest",
]


def _load_env_fallback():
    """Charge .env si présent et si GEMINI_API_KEY n'est pas déjà dans l'environnement."""
    if os.environ.get("GEMINI_API_KEY"):
        return
    env_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), ".env")
    if os.path.exists(env_path):
        with open(env_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue
                k, v = line.split("=", 1)
                os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))


def _catalogue_fallback_response(meds, question, medicament_nom, last_error):
    """Réponse de repli basée sur le catalogue local en cas de saturation (503/429) de Gemini."""
    med = None
    if medicament_nom:
        med = meds.filter(
            Q(nom__icontains=medicament_nom) | Q(dci__icontains=medicament_nom)
        ).first()
    else:
        q_low = question.lower()
        for item in meds:
            if item.nom.lower() in q_low or (item.dci and item.dci.lower() in q_low):
                med = item
                break

    if med:
        reponse_texte = (
            f"Pour {med.nom} ({med.dosage or 'dosage non précisé'}) : "
            f"Posologie : {med.posologie or 'Non renseignée'} | "
            f"Effets secondaires : {med.effets_secondaires or 'Non renseignés'} | "
            f"Contre-indications : {med.contre_indications or 'Non renseignées'} | "
            f"Interactions : {med.interactions or 'Non renseignées'}."
        )
        return Response(
            {
                "reponse": reponse_texte,
                "medicament_trouve": med.nom,
                "source": f"Catalogue MediInfo — fiche #{med.id} (repli suite à indisponibilité Gemini : {last_error})",
                "avertissement": AVERTISSEMENT_MEDICAL,
            },
            status=status.HTTP_200_OK,
        )

    return Response(
        {
            "reponse": (
                "Le service IA est temporairement saturé et aucune fiche correspondante "
                "n'a été trouvée dans le catalogue local."
            ),
            "medicament_trouve": None,
            "source": f"Catalogue MediInfo (repli suite à indisponibilité Gemini : {last_error})",
            "avertissement": AVERTISSEMENT_MEDICAL,
        },
        status=status.HTTP_200_OK,
    )


class RegisterView(APIView):
    def post(self, request):
        serializer = RegisterSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        token, _ = Token.objects.get_or_create(user=user)
        return Response(
            {
                "id": user.id,
                "username": user.username,
                "email": user.email,
                "role": user.role,
                "token": token.key,
            },
            status=status.HTTP_201_CREATED,
        )


class LoginView(APIView):
    def post(self, request):
        serializer = LoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.validated_data["user"]
        token, _ = Token.objects.get_or_create(user=user)
        return Response(
            {
                "id": user.id,
                "username": user.username,
                "role": user.role,
                "token": token.key,
            },
            status=status.HTTP_200_OK,
        )


class MedicamentListCreateView(APIView):
    def get(self, request):
        query = request.query_params.get("q", "").strip()
        qs = Medicament.objects.all()
        if query:
            qs = qs.filter(Q(nom__icontains=query) | Q(dci__icontains=query))
        serializer = MedicamentSerializer(qs, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

    def post(self, request):
        if not request.user or not request.user.is_authenticated:
            return Response(
                {"detail": "Authentification requise (Token <votre_token>)."},
                status=status.HTTP_401_UNAUTHORIZED,
            )
        if getattr(request.user, "role", None) != "PRO":
            return Response(
                {"detail": "Seul un professionnel de santé (PRO) peut ajouter un médicament."},
                status=status.HTTP_403_FORBIDDEN,
            )
        serializer = MedicamentSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        medicament = serializer.save(ajoute_par=request.user)
        return Response(MedicamentSerializer(medicament).data, status=status.HTTP_201_CREATED)


class AssistantAIView(APIView):
    def post(self, request):
        _load_env_fallback()
        api_key = os.environ.get("GEMINI_API_KEY", "").strip()
        if not api_key:
            return Response(
                {"detail": "GEMINI_API_KEY n'est pas configurée dans l'environnement."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        question = (request.data.get("question") or "").strip()
        medicament_nom = (request.data.get("medicament") or "").strip()
        image_file = request.FILES.get("image")
        image_base64 = (request.data.get("image_base64") or "").strip()
        mime_type = (request.data.get("mime_type") or "").strip()

        if not question and not image_file and not image_base64:
            return Response(
                {"detail": "Fournissez au moins une 'question' ou une 'image'."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if not question:
            question = (
                "Identifie le médicament visible et fournis sa posologie, ses effets secondaires, "
                "ses contre-indications et ses interactions en te basant sur le catalogue fourni."
            )

        if medicament_nom:
            meds = Medicament.objects.filter(
                Q(nom__icontains=medicament_nom) | Q(dci__icontains=medicament_nom)
            )
        else:
            meds = Medicament.objects.all()

        catalogue_lignes = [
            f"- Nom: {m.nom} | DCI: {m.dci} | Dosage: {m.dosage} | Forme: {m.forme} | "
            f"Posologie: {m.posologie} | Effets secondaires: {m.effets_secondaires} | "
            f"Contre-indications: {m.contre_indications} | Interactions: {m.interactions}"
            for m in meds[:30]
        ]
        catalogue_texte = (
            "\n".join(catalogue_lignes)
            if catalogue_lignes
            else "Aucun médicament enregistré dans le catalogue."
        )

        system_prompt = (
            "Tu es l'assistant IA de MediInfo. Tu fournis uniquement des informations générales "
            "sur les médicaments (jamais de diagnostic médical ni d'ordonnance). "
            "Appuie-toi prioritairement sur le catalogue ci-dessous. Si une information n'est pas "
            "présente dans le catalogue ni lisible sur l'image, indique clairement que l'information "
            "est insuffisante dans le catalogue plutôt que d'inventer.\n\n"
            f"CATALOGUE DISPONIBLE :\n{catalogue_texte}"
        )

        parts = [{"text": f"{system_prompt}\n\nQuestion de l'utilisateur : {question}"}]

        if image_file:
            raw_bytes = image_file.read()
            detected_mime = image_file.content_type or mime_type or "image/jpeg"
            parts.append(
                {
                    "inline_data": {
                        "mime_type": detected_mime,
                        "data": base64.b64encode(raw_bytes).decode("utf-8"),
                    }
                }
            )
        elif image_base64:
            if "," in image_base64 and image_base64.startswith("data:"):
                header, b64_data = image_base64.split(",", 1)
                if not mime_type and ";" in header:
                    mime_type = header.split(":", 1)[1].split(";", 1)[0]
            else:
                b64_data = image_base64
            parts.append(
                {
                    "inline_data": {
                        "mime_type": mime_type or "image/jpeg",
                        "data": b64_data,
                    }
                }
            )

        env_model = os.environ.get("GEMINI_MODEL", "").strip()
        models_to_try = ([env_model] if env_model else []) + [
            m for m in FALLBACK_MODELS if m != env_model
        ]

        payload = {"contents": [{"parts": parts}]}
        data = None
        last_error = ""
        used_model = models_to_try[0]
        overload_seen = False

        for model_name in models_to_try:
            url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_name}:generateContent?key={api_key}"
            for attempt in range(2):
                try:
                    resp = requests.post(url, json=payload, timeout=30)
                    if resp.status_code in (503, 429):
                        overload_seen = True
                        last_error = f"{resp.status_code} ({model_name})"
                        time.sleep(1.2)
                        continue
                    resp.raise_for_status()
                    data = resp.json()
                    used_model = model_name
                    break
                except requests.RequestException as exc:
                    last_error = str(exc)
                    if getattr(exc, "response", None) is not None:
                        if exc.response.status_code in (503, 429):
                            overload_seen = True
                        last_error = f"{exc} — {exc.response.text}"
                    break
            if data is not None:
                break

        if data is None:
            if overload_seen:
                return _catalogue_fallback_response(meds, question, medicament_nom, last_error)
            return Response(
                {"detail": f"Erreur lors de l'appel à Gemini : {last_error}"},
                status=status.HTTP_502_BAD_GATEWAY,
            )

        candidates = data.get("candidates") or []
        reponse_texte = ""
        if candidates:
            c_parts = (candidates[0].get("content") or {}).get("parts") or []
            reponse_texte = "".join(p.get("text", "") for p in c_parts if "text" in p).strip()

        if not reponse_texte:
            reponse_texte = "Information insuffisante pour générer une réponse."

        med_trouve = next(
            (
                m.nom
                for m in meds
                if m.nom.lower() in reponse_texte.lower() or m.nom.lower() in question.lower()
            ),
            None,
        )

        return Response(
            {
                "reponse": reponse_texte,
                "medicament_trouve": med_trouve,
                "source": f"Gemini ({used_model}) + Catalogue MediInfo",
                "avertissement": AVERTISSEMENT_MEDICAL,
            },
            status=status.HTTP_200_OK,
        )