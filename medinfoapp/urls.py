from django.urls import path
from .views import AssistantAIView, LoginView, MedicamentListCreateView, RegisterView

urlpatterns = [
    path("auth/register/", RegisterView.as_view(), name="register"),
    path("auth/login/", LoginView.as_view(), name="login"),
    path("medicines/", MedicamentListCreateView.as_view(), name="medicines"),
    path("ai/ask/", AssistantAIView.as_view(), name="ai-ask"),
]