from django.urls import path
from .views import ChatWithAIView, ConversationView

urlpatterns = [
    path("chat/", ChatWithAIView.as_view()),
    path("conversation/", ConversationView.as_view()),
]