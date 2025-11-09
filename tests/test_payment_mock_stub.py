import pytest
from unittest.mock import Mock
from services.library_service import pay_late_fees, refund_late_fee_payment
from services.payment_service import PaymentGateway


class TestPayLateFees:
    # for coverage
    def test_process_payment_runs(self):
        gateway = PaymentGateway()
        success, txn_id, msg = gateway.process_payment("123456", 10.0, "Test")
        assert success
        assert txn_id.startswith("txn_")

    def test_verify_payment_status_runs(self):
        gateway = PaymentGateway()
        status = gateway.verify_payment_status("txn_123456")
        assert status["status"] == "completed"

    def test_pay_late_fees_creates_gateway_if_none(self, mocker):
        mocker.patch(
            "services.library_service.calculate_late_fee_for_book",
            return_value={"fee_amount": 5.00, "days_overdue": 2}
        )
        mocker.patch(
            "services.library_service.get_book_by_id",
            return_value={"id": 1, "title": "Mock Book"}
        )

        # Call
        success, msg, txn_id = pay_late_fees("123456", 1)

        # Validate
        assert success is True
        assert txn_id.startswith("txn_")
        assert "Payment successful" in msg

    def test_pay_late_fees_unable_to_calculate_late_fee(self, mocker):
        # Stub
        mocker.patch(
            "services.library_service.calculate_late_fee_for_book",
            return_value=None  # Simulates unable to calculate fee
        )
        mocker.patch(
            "services.library_service.get_book_by_id",
            return_value={"id": 1, "title": "Test Book"}
        )

        # Mock
        payment_gateway = Mock(spec=PaymentGateway)

        # Call
        success, msg, txn_id = pay_late_fees("123456", 1, payment_gateway)

        # Validate
        assert success is False
        assert "Unable to calculate late fees" in msg
        assert txn_id is None
        payment_gateway.process_payment.assert_not_called()

    def test_process_payment_zero_amount_direct(self):
        gateway = PaymentGateway()
        success, txn_id, msg = gateway.process_payment("123456", 0, "Test")
        assert success is False
        assert txn_id == ""
        assert "must be greater than 0" in msg

    def test_process_payment_exceeds_limit_direct(self):
        gateway = PaymentGateway()
        success, txn_id, msg = gateway.process_payment("123456", 2000, "Test")
        assert success is False
        assert txn_id == ""
        assert "exceeds limit" in msg

    def test_process_payment_invalid_patron_id_direct(self):
        gateway = PaymentGateway()
        success, txn_id, msg = gateway.process_payment("12345", 50, "Test")
        assert success is False
        assert txn_id == ""
        assert "Invalid patron ID" in msg

    # mocks and stubs
    def test_pay_late_fees_success(self, mocker):
        # stubs
        mocker.patch(
            "services.library_service.calculate_late_fee_for_book",
            return_value={"fee_amount": 5.00, "days_overdue": 2}
        )
        mocker.patch(
            "services.library_service.get_book_by_id",
            return_value={"id": 1, "title": "Mock Book"}
        )

        # mock
        payment_gateway = Mock(spec=PaymentGateway)
        payment_gateway.process_payment.return_value = (True, "txn_123", "Payment processed successfully")

        # call
        success, msg, txn_id = pay_late_fees("123456", 1, payment_gateway)

        # verify
        assert success is True
        assert "Payment successful" in msg
        assert txn_id == "txn_123"
        payment_gateway.process_payment.assert_called_once_with(
            patron_id="123456",
            amount=5.00,
            description="Late fees for 'Mock Book'"
        )

    def test_pay_late_fees_declined(self, mocker):
        # stubs
        mocker.patch(
            "services.library_service.calculate_late_fee_for_book",
            return_value={"fee_amount": 7.50, "days_overdue": 3}
        )
        mocker.patch(
            "services.library_service.get_book_by_id",
            return_value={"id": 2, "title": "Declined Book"}
        )

        # mock
        payment_gateway = Mock(spec=PaymentGateway)
        payment_gateway.process_payment.return_value = (False, None, "Card declined")

        # call
        success, msg, txn_id = pay_late_fees("654321", 2, payment_gateway)

        # verify
        assert success is False
        assert "Payment failed: Card declined" in msg
        assert txn_id is None

    def test_pay_late_fees_invalid_id(self, mocker):
        # stubs
        mocker.patch("services.library_service.calculate_late_fee_for_book")
        mocker.patch("services.library_service.get_book_by_id")

        # mock
        payment_gateway = Mock(spec=PaymentGateway)

        # call with invalid patron ID
        success, msg, txn_id = pay_late_fees("12AB34", 3, payment_gateway)

        # validate
        assert success is False
        assert "Invalid patron ID" in msg
        assert txn_id is None
        payment_gateway.process_payment.assert_not_called()

    def test_pay_late_fees_zero_late_fee(self, mocker):
        # stubs
        mocker.patch(
            "services.library_service.calculate_late_fee_for_book",
            return_value={"fee_amount": 0.0}
        )
        mocker.patch(
            "services.library_service.get_book_by_id",
            return_value={"id": 4, "title": "Free Book"}
        )

        # mock
        payment_gateway = Mock(spec=PaymentGateway)

        # call
        success, msg, txn_id = pay_late_fees("123456", 4, payment_gateway)

        # validate
        assert success is False
        assert "No late fees to pay" in msg
        assert txn_id is None
        payment_gateway.process_payment.assert_not_called()

    def test_pay_late_fees_network_error(self, mocker):
        # stubs
        mocker.patch(
            "services.library_service.calculate_late_fee_for_book",
            return_value={"fee_amount": 8.00}
        )
        mocker.patch(
            "services.library_service.get_book_by_id",
            return_value={"id": 5, "title": "Network Error Book"}
        )

        # mock
        payment_gateway = Mock(spec=PaymentGateway)
        payment_gateway.process_payment.side_effect = Exception("Network timeout")

        # call
        success, msg, txn_id = pay_late_fees("999999", 5, payment_gateway)

        # validate
        assert success is False
        assert "Payment processing error" in msg
        assert txn_id is None

    def test_pay_late_fees_book_not_found(self, mocker):
        # stubs
        mocker.patch(
            "services.library_service.calculate_late_fee_for_book",
            return_value={"fee_amount": 10.00}
        )
        mocker.patch(
            "services.library_service.get_book_by_id",
            return_value=None
        )

        # mock
        payment_gateway = Mock(spec=PaymentGateway)

        # call
        success, msg, txn_id = pay_late_fees("123456", 999, payment_gateway)

        # validate
        assert success is False
        assert "Book not found" in msg
        assert txn_id is None
        payment_gateway.process_payment.assert_not_called()


class TestRefundLateFeePayment:

    # for coverage
    def test_refund_payment_runs(self):
        gateway = PaymentGateway()
        success, msg = gateway.refund_payment("txn_123456", 5.0)
        assert success
        assert "Refund" in msg

    def test_refund_late_fees_creates_gateway_if_none(self, mocker):
        success, message = refund_late_fee_payment("txn_123456", 5.0)

        assert success is True
        assert "Refund" in message

    def test_refund_uses_default_gateway_when_none_provided(self):
        success, message = refund_late_fee_payment("txn_123456", 5.0, None)
        assert success is True
        assert "Refund" in message


    # mock and stubs
    def test_refund_success(self):
        # mock
        payment_gateway = Mock(spec=PaymentGateway)
        payment_gateway.refund_payment.return_value = (True, "Refund processed successfully")

        # call
        success, message = refund_late_fee_payment("txn_123456", 10.00, payment_gateway)

        # verify
        assert success is True
        assert message == "Refund processed successfully"
        payment_gateway.refund_payment.assert_called_once_with("txn_123456", 10.00)

    def test_invalid_transaction_id(self):
        # Test empty transaction ID
        payment_gateway = Mock(spec=PaymentGateway)
        success, message = refund_late_fee_payment("", 10.00, payment_gateway)
        assert success is False
        assert message == "Invalid transaction ID."
        payment_gateway.refund_payment.assert_not_called()

        # Test invalid format
        success, message = refund_late_fee_payment("abc123", 10.00, payment_gateway)
        assert success is False
        assert message == "Invalid transaction ID."
        payment_gateway.refund_payment.assert_not_called()

    def test_invalid_refund_amount_zero_or_negative(self):
        # mock
        payment_gateway = Mock(spec=PaymentGateway)

        # Test zero amount
        success, message = refund_late_fee_payment("txn_123456", 0, payment_gateway)
        assert success is False
        assert message == "Refund amount must be greater than 0."
        payment_gateway.refund_payment.assert_not_called()

        # Test negative amount
        success, message = refund_late_fee_payment("txn_123456", -5, payment_gateway)
        assert success is False
        assert message == "Refund amount must be greater than 0."
        payment_gateway.refund_payment.assert_not_called()

    def test_refund_amount_exceeds_limit(self):
        # mock
        payment_gateway = Mock(spec=PaymentGateway)

        # call
        success, message = refund_late_fee_payment("txn_123456", 20.00, payment_gateway)

        # assert
        assert success is False
        assert message == "Refund amount exceeds maximum late fee."
        payment_gateway.refund_payment.assert_not_called()

    def test_refund_failure_from_gateway(self):
        # mock
        payment_gateway = Mock(spec=PaymentGateway)
        payment_gateway.refund_payment.return_value = (False, "Gateway refused refund")

        # call
        success, message = refund_late_fee_payment("txn_999999", 10.00, payment_gateway)

        # validate
        assert success is False
        assert message == "Refund failed: Gateway refused refund"
        payment_gateway.refund_payment.assert_called_once_with("txn_999999", 10.00)

    def test_refund_raises_exception(self):
        # mock
        payment_gateway = Mock(spec=PaymentGateway)
        payment_gateway.refund_payment.side_effect = Exception("Network down")

        # call
        success, msg = refund_late_fee_payment("txn_123456", 5.0, payment_gateway)

        # validate
        assert success is False
        assert "Network down" in msg
