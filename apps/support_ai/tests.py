import uuid

from django.test import TestCase
from django.contrib.auth import get_user_model

from rest_framework.test import APITestCase
from rest_framework import status

from .models import AIConversation, AIMessage, AIMessageRole
from .services import AIService
from .serializers import AIConversationSerializer
from .llm import SimpleLLM

User = get_user_model()


# ---  (Model Tests) ---
class SupportAIModelTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(email="testuser@gmail.com",
                                             phone="09145670987",
                                             password="password123")

    def test_create_conversation(self):
        conv = AIConversation.objects.create(user=self.user)
        self.assertIsInstance(conv.id, uuid.UUID)
        self.assertEqual(conv.user.phone, "09145670987")

    def test_create_message(self):
        conv = AIConversation.objects.create(user=self.user)
        message = AIMessage.objects.create(
            conversation=conv,
            role=AIMessageRole.USER,
            content="Hello AI"
        )
        self.assertEqual(message.content, "Hello AI")
        self.assertEqual(message.role, AIMessageRole.USER)
        self.assertEqual(conv.messages.count(), 1)


# ---  LLM (Service & LLM Tests) ---
class SupportAIServiceTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(email="testuser@gmail.com",
                                             phone="09145670987",
                                             password="password123")

    def test_get_or_create_conversation(self):
        conv1 = AIService.get_or_create_conversation(self.user)
        self.assertEqual(AIConversation.objects.count(), 1)

        conv2 = AIService.get_or_create_conversation(self.user)
        self.assertEqual(conv1.id, conv2.id)
        self.assertEqual(AIConversation.objects.count(), 1)

    def test_simple_llm_responses(self):
        resp_loan = SimpleLLM.generate_response("",
                                                "tell me about loans")
        self.assertIn("loan", resp_loan.lower())

        resp_fraud = SimpleLLM.generate_response("",
                                                 "someone stole my card fraud")
        self.assertIn("suspicious", resp_fraud.lower())

        resp_default = SimpleLLM.generate_response("",
                                                   "hello")
        self.assertEqual(resp_default,
                         "I am your banking assistant. How can I help you?")

    def test_send_message_service(self):
        response = AIService.send_message(self.user,
                                          "I want a loan")

        conv = AIConversation.objects.get(user=self.user)
        self.assertEqual(conv.messages.count(), 2)
        self.assertEqual(conv.messages.filter(role=AIMessageRole.USER).first().content, "I want a loan")
        self.assertIsNotNone(response)


# ---  (API/View Tests) ---
class SupportAIAPITest(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(email="testuser@gmail.com",
                                             phone="09145670987",
                                             password="password123")
        self.client.force_authenticate(user=self.user)
        self.chat_url = "/support_ai/chat/"
        self.conv_url = "/support_ai/conversation/"

    def test_chat_with_ai_view(self):
        data = {"message": "Hello, I have a question about fraud."}
        response = self.client.post(self.chat_url, data, format='json')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("response", response.data)
        self.assertEqual(AIMessage.objects.count(), 2)

    def test_get_conversation_history(self):
        AIService.send_message(self.user, "Test message")

        response = self.client.get(self.conv_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['messages']), 2)
        self.assertEqual(response.data['user'], self.user.id)

    def test_unauthenticated_access(self):
        self.client.logout()
        response = self.client.get(self.conv_url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)


# ---  (Serializer Tests) ---
class SupportAISerializerTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(email="testuser@gmail.com",
                                             phone="09145670987",
                                             password="password123")
        self.conv = AIConversation.objects.create(user=self.user)
        AIMessage.objects.create(conversation=self.conv,
                                 role=AIMessageRole.USER, content="Hi")

    def test_conversation_serializer(self):
        serializer = AIConversationSerializer(instance=self.conv)
        self.assertEqual(len(serializer.data['messages']), 1)
        self.assertEqual(serializer.data['messages'][0]['content'],
                         "Hi")
