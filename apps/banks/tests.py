from django.test import TestCase
from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase, APIClient
from .models import Bank, Branch, BankStatus
import uuid

User = get_user_model()


# --- Model Tests ---
class BankModelTest(TestCase):
    def setUp(self):
        self.bank = Bank.objects.create(
            name="Test Bank",
            code="TB01",
            swift_code="TESTTR22",
            transfer_fee=10.50
        )

    def test_bank_creation(self):
        self.assertEqual(self.bank.name, "Test Bank")
        self.assertEqual(self.bank.iban_prefix, "TR")
        self.assertEqual(self.bank.status, BankStatus.ACTIVE)
        self.assertTrue(self.bank.supports_instant_transfer)

    def test_unique_fields(self):
        with self.assertRaises(Exception):
            Bank.objects.create(name="Test Bank", code="OTHER", swift_code="S1")


class BranchModelTest(TestCase):
    def setUp(self):
        self.bank = Bank.objects.create(name="Bank A", code="BA", swift_code="SW1")
        self.branch = Branch.objects.create(
            bank=self.bank,
            name="Central",
            code="C100",
            city="Istanbul",
            address="Some Address"
        )

    def test_branch_creation(self):
        self.assertEqual(self.branch.bank, self.bank)
        self.assertTrue(self.branch.is_active)

    def test_unique_together_constraint(self):
        with self.assertRaises(Exception):
            Branch.objects.create(bank=self.bank, name="New", code="C100")


# --- API Tests ---
class BankAPITest(APITestCase):
    def setUp(self):
        self.client = APIClient()
        self.admin_user = User.objects.create_superuser(phone="09145670945", email="tesr1@gmail.com",
                                                        password='password',
                                                        national_code="1111111111")
        self.regular_user = User.objects.create_user(phone='09385660956', email="test2@gmail.com",
                                                     password='password'
                                                     , national_code="2222222222")

        self.active_bank = Bank.objects.create(name="Active Bank", code="B1", swift_code="SW1",
                                               status=BankStatus.ACTIVE)
        self.inactive_bank = Bank.objects.create(name="Inactive Bank", code="B2", swift_code="SW2",
                                                 status=BankStatus.INACTIVE)

        self.bank_list_url = "/"
        self.bank_create_url = "/create/"

    def test_get_active_banks(self):
        response = self.client.get(self.bank_list_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]['name'], "Active Bank")

    def test_get_bank_detail(self):
        url = f"/{self.active_bank.id}/"
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['code'], "B1")

    def test_create_bank_as_admin(self):
        self.client.force_authenticate(user=self.admin_user)
        data = {
            "name": "New Bank",
            "code": "NB99",
            "swift_code": "NEWBTRXX",
            "transfer_fee": "5.00"
        }
        response = self.client.post(self.bank_create_url, data,format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Bank.objects.count(), 3)


    def test_create_bank_as_regular_user_forbidden(self):
        self.client.force_authenticate(user=self.regular_user)
        response = self.client.post(self.bank_create_url, {"name": "Fail"})
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_update_bank_status_as_admin(self):
        self.client.force_authenticate(user=self.admin_user)
        url = f"/{self.active_bank.id}/status/"
        data = {"status": BankStatus.MAINTENANCE}
        response = self.client.patch(url, data)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.active_bank.refresh_from_db()
        self.assertEqual(self.active_bank.status, BankStatus.MAINTENANCE)


class BranchAPITest(APITestCase):
    def setUp(self):
        self.bank = Bank.objects.create(name="Bank X", code="BX", swift_code="SWX")
        self.branch_active = Branch.objects.create(bank=self.bank, name="Active Br", code="BR1", is_active=True)
        self.branch_inactive = Branch.objects.create(bank=self.bank, name="Inactive Br", code="BR2", is_active=False)

    def test_list_branches_for_bank(self):
        url = f"/{self.bank.id}/branches/"
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]['code'], "BR1")

    def test_list_branches_invalid_bank(self):
        random_uuid = uuid.uuid4()
        url = f"/{random_uuid}/branches/"
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 0)

