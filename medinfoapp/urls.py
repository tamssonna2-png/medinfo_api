from django.urls import path
from .views import AdminProApproveView,AdminProRejectView,AdminProRequestDetailView,AdminProRequestListView, AssistantAIView, LoginView, MedicamentListCreateView, RegisterView

urlpatterns = [
    path("auth/register/", RegisterView.as_view(), name="register"),
    path("auth/login/", LoginView.as_view(), name="login"),
    path("medicines/", MedicamentListCreateView.as_view(), name="medicines"),
    path("ai/ask/", AssistantAIView.as_view(), name="ai-ask"),

    path("admin/pro-requests/", AdminProRequestListView.as_view(), name="admin-pro-requests"),
    path("admin/pro-requests/<int:user_id>/", AdminProRequestDetailView.as_view(), name="admin-pro-request-detail"),
    path("admin/pro-requests/<int:user_id>/approve/", AdminProApproveView.as_view(), name="admin-pro-approve"),
    path("admin/pro-requests/<int:user_id>/reject/", AdminProRejectView.as_view(), name="admin-pro-reject"),
]