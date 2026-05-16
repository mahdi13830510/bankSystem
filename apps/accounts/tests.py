from django.test import TestCase
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError

from rest_framework.test import APITestCase
from rest_framework import status
from rest_framework import serializers

from decimal import Decimal

from apps.accounts.models import Account, AccountStatus, AccountType, CurrencyType
from apps.accounts.services import AccountService
from apps.banks.models import Bank
from apps.accounts.validators import validate_unique_account_type_per_bank_customer


User = get_user_model()


class AccountServiceTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(phone="09145667890", email="test1@gmail.com", password="password")
        self.bank = Bank.objects.create(name="Test Bank", code="TB")

        self.account = AccountService.open_account(
            user=self.user,
            bank_id=self.bank.id,
            type=AccountType.SAVING,
            currency=CurrencyType.USD
        )

    def test_open_account(self):
        account = AccountService.open_account(
            user=self.user,
            bank_id=self.bank.id,
            type=AccountType.BUSINESS,
            currency=CurrencyType.TRY
        )
        self.assertEqual(account.customer, self.user)
        self.assertEqual(account.type, AccountType.BUSINESS)
        self.assertTrue(account.account_number.isdigit())
        self.assertTrue(account.iban.startswith("TR"))

    def test_increase_balance(self):
        AccountService.increase_balance(self.account.id, "100.00")
        self.account.refresh_from_db()
        self.assertEqual(self.account.balance, Decimal("100.00"))

    def test_increase_balance_invalid_amount(self):
        with self.assertRaises(ValidationError):
            AccountService.increase_balance(self.account.id, "-50.00")

    def test_decrease_balance_success(self):
        AccountService.increase_balance(self.account.id, "100.00")
        AccountService.decrease_balance(self.account.id, "40.00")
        self.account.refresh_from_db()
        self.assertEqual(self.account.balance, Decimal("60.00"))

    def test_decrease_balance_insufficient(self):
        AccountService.increase_balance(self.account.id, "50.00")
        with self.assertRaises(ValidationError):
            AccountService.decrease_balance(self.account.id, "60.00")

    def test_block_and_unblock_balance(self):
        AccountService.increase_balance(self.account.id, "100.00")

        AccountService.block_balance(self.account.id, "30.00")
        self.account.refresh_from_db()
        self.assertEqual(self.account.blocked_balance, Decimal("30.00"))
        self.assertEqual(self.account.available_balance, Decimal("70.00"))

        AccountService.unblock_balance(self.account.id, "10.00")
        self.account.refresh_from_db()
        self.assertEqual(self.account.blocked_balance, Decimal("20.00"))

    def test_close_account_with_balance(self):
        AccountService.increase_balance(self.account.id, "10.00")
        with self.assertRaises(ValidationError):
            AccountService.close(self.account.id)

    def test_close_account_success(self):
        AccountService.close(self.account.id)
        self.account.refresh_from_db()
        self.assertEqual(self.account.status, AccountStatus.CLOSED)

    def test_freeze_and_activate(self):
        AccountService.freeze(self.account.id)
        self.account.refresh_from_db()
        self.assertEqual(self.account.status, AccountStatus.BLOCKED)

        AccountService.activate(self.account.id)
        self.account.refresh_from_db()
        self.assertEqual(self.account.status, AccountStatus.ACTIVE)


class AccountAPITest(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(email="test1@gmail.com", national_code="1111111111",
                                             phone="09145660987", password="password123")
        self.staff_user = User.objects.create_user(email="staff1@gmail.com", national_code="1211111111",
                                                   phone="9345660987", is_staff=True)

        self.bank = Bank.objects.create(name="Central Bank", code="CB")

        self.client.force_authenticate(user=self.user)
        self.account = Account.objects.create(
            customer=self.user,
            bank=self.bank,
            account_number="1234567890123456",
            iban="TR123456789012345678901234",
            type=AccountType.SAVING,
            currency=CurrencyType.USD,
            balance=1000
        )

    def test_get_my_accounts(self):
        url = "/accounts/my/"
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]['account_number'], self.account.account_number)

    def test_open_account_api(self):
        url = "/accounts/open/"
        data = {
            "bank_id":self.bank.id,
            "type": AccountType.CURRENT,
            "currency": CurrencyType.EUR
        }
        response = self.client.post(url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Account.objects.filter(customer=self.user).count(), 2)

    def test_deposit_by_staff(self):
        self.client.force_authenticate(user=self.staff_user)
        url = f"/accounts/{self.account.id}/deposit/"
        data = {"amount": "500.00"}
        response = self.client.post(url, data)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.account.refresh_from_db()
        self.assertEqual(self.account.balance, 1500)

    def test_deposit_by_customer_denied(self):
        self.client.force_authenticate(user=self.user)
        url = f"/accounts/{self.account.id}/deposit/"
        data = {"amount": "500.00"}
        response = self.client.post(url, data)

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_freeze_account_by_staff(self):
        self.client.force_authenticate(user=self.staff_user)
        url = f"/accounts/{self.account.id}/freeze/"
        response = self.client.post(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.account.refresh_from_db()
        self.assertEqual(self.account.status, "BLOCKED")


class ValidatorTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(email="test1@gmail.com",
                                             phone="09145660987", password="password123")
        self.bank = Bank.objects.create(name="Val Bank")
        Account.objects.create(
            customer=self.user, bank=self.bank,
            type=AccountType.SAVING, currency="USD",
            account_number="1", iban="1"
        )

    def test_duplicate_account_type_validation(self):
        with self.assertRaises(serializers.ValidationError):
            validate_unique_account_type_per_bank_customer(
                self.user, self.bank, AccountType.SAVING
            )

    def test_different_type_validation_passes(self):
        try:
            validate_unique_account_type_per_bank_customer(
                self.user, self.bank, AccountType.BUSINESS
            )
        except ValidationError:
            self.fail("validate_unique_account_type_per_bank_customer raised ValidationError unexpectedly!")
