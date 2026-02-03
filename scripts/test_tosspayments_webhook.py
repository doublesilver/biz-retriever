#!/usr/bin/env python3
"""
Test Tosspayments Webhook Handler

This script tests the webhook endpoint by sending sample webhook events
with proper HMAC-SHA256 signatures.

Usage:
    python scripts/test_tosspayments_webhook.py
    python scripts/test_tosspayments_webhook.py --url https://your-domain.com/api/webhooks/tosspayments
    python scripts/test_tosspayments_webhook.py --secret your_webhook_secret
"""

import argparse
import hmac
import hashlib
import json
import requests
from datetime import datetime


def generate_signature(payload: dict, secret: str) -> str:
    """
    Generate HMAC-SHA256 signature for webhook payload
    
    Args:
        payload: Webhook payload dictionary
        secret: TOSSPAYMENTS_WEBHOOK_SECRET
    
    Returns:
        Hex-encoded HMAC-SHA256 signature
    """
    payload_str = json.dumps(payload, ensure_ascii=False)
    signature = hmac.new(
        secret.encode('utf-8'),
        payload_str.encode('utf-8'),
        hashlib.sha256
    ).hexdigest()
    return signature


def test_payment_confirmed(webhook_url: str, secret: str):
    """Test payment.confirmed event"""
    print("\n" + "="*60)
    print("TEST 1: payment.confirmed")
    print("="*60)
    
    payload = {
        "eventType": "payment.confirmed",
        "orderId": f"BIZ-123-PRO-{datetime.now().strftime('%Y%m%d%H%M%S')}",
        "paymentKey": f"test_payment_key_{datetime.now().timestamp()}",
        "orderName": "프로 플랜 - 월간 구독",
        "status": "DONE",
        "totalAmount": 30000,
        "method": "카드",
        "approvedAt": datetime.now().isoformat(),
        "card": {
            "issuerCode": "61",
            "acquirerCode": "11",
            "number": "433012******1234",
            "installmentPlanMonths": 0,
            "isInterestFree": False,
            "cardType": "신용"
        }
    }
    
    signature = generate_signature(payload, secret)
    headers = {
        "Content-Type": "application/json",
        "X-Tosspayments-Signature": signature
    }
    
    print(f"Payload: {json.dumps(payload, indent=2, ensure_ascii=False)}")
    print(f"Signature: {signature}")
    
    try:
        response = requests.post(webhook_url, json=payload, headers=headers, timeout=10)
        print(f"\nResponse Status: {response.status_code}")
        print(f"Response Body: {response.text}")
        
        if response.status_code == 200:
            print("✅ TEST PASSED")
        else:
            print("❌ TEST FAILED")
    except Exception as e:
        print(f"❌ TEST FAILED: {str(e)}")


def test_payment_failed(webhook_url: str, secret: str):
    """Test payment.failed event"""
    print("\n" + "="*60)
    print("TEST 2: payment.failed")
    print("="*60)
    
    payload = {
        "eventType": "payment.failed",
        "orderId": f"BIZ-123-PRO-{datetime.now().strftime('%Y%m%d%H%M%S')}",
        "status": "FAILED",
        "failureCode": "PAY_PROCESS_CANCELED",
        "failureMessage": "사용자가 결제를 취소하였습니다."
    }
    
    signature = generate_signature(payload, secret)
    headers = {
        "Content-Type": "application/json",
        "X-Tosspayments-Signature": signature
    }
    
    print(f"Payload: {json.dumps(payload, indent=2, ensure_ascii=False)}")
    print(f"Signature: {signature}")
    
    try:
        response = requests.post(webhook_url, json=payload, headers=headers, timeout=10)
        print(f"\nResponse Status: {response.status_code}")
        print(f"Response Body: {response.text}")
        
        if response.status_code == 200:
            print("✅ TEST PASSED")
        else:
            print("❌ TEST FAILED")
    except Exception as e:
        print(f"❌ TEST FAILED: {str(e)}")


def test_payment_canceled(webhook_url: str, secret: str):
    """Test payment.canceled event"""
    print("\n" + "="*60)
    print("TEST 3: payment.canceled")
    print("="*60)
    
    payload = {
        "eventType": "payment.canceled",
        "orderId": f"BIZ-123-PRO-{datetime.now().strftime('%Y%m%d%H%M%S')}",
        "paymentKey": f"test_payment_key_{datetime.now().timestamp()}",
        "status": "CANCELED",
        "cancelReason": "고객 변심",
        "canceledAt": datetime.now().isoformat(),
        "cancels": [
            {
                "cancelAmount": 30000,
                "cancelReason": "고객 변심",
                "canceledAt": datetime.now().isoformat()
            }
        ]
    }
    
    signature = generate_signature(payload, secret)
    headers = {
        "Content-Type": "application/json",
        "X-Tosspayments-Signature": signature
    }
    
    print(f"Payload: {json.dumps(payload, indent=2, ensure_ascii=False)}")
    print(f"Signature: {signature}")
    
    try:
        response = requests.post(webhook_url, json=payload, headers=headers, timeout=10)
        print(f"\nResponse Status: {response.status_code}")
        print(f"Response Body: {response.text}")
        
        if response.status_code == 200:
            print("✅ TEST PASSED")
        else:
            print("❌ TEST FAILED")
    except Exception as e:
        print(f"❌ TEST FAILED: {str(e)}")


def test_invalid_signature(webhook_url: str):
    """Test invalid signature (should return 401)"""
    print("\n" + "="*60)
    print("TEST 4: Invalid Signature (Security Test)")
    print("="*60)
    
    payload = {
        "eventType": "payment.confirmed",
        "orderId": "BIZ-123-PRO-20260203",
        "paymentKey": "test_invalid",
        "totalAmount": 30000
    }
    
    headers = {
        "Content-Type": "application/json",
        "X-Tosspayments-Signature": "invalid_signature_12345"
    }
    
    print(f"Payload: {json.dumps(payload, indent=2)}")
    print(f"Signature: invalid_signature_12345 (intentionally wrong)")
    
    try:
        response = requests.post(webhook_url, json=payload, headers=headers, timeout=10)
        print(f"\nResponse Status: {response.status_code}")
        print(f"Response Body: {response.text}")
        
        if response.status_code == 401:
            print("✅ TEST PASSED (correctly rejected invalid signature)")
        else:
            print("❌ TEST FAILED (should return 401)")
    except Exception as e:
        print(f"❌ TEST FAILED: {str(e)}")


def main():
    parser = argparse.ArgumentParser(description="Test Tosspayments Webhook Handler")
    parser.add_argument(
        "--url",
        default="http://localhost:3000/api/webhooks/tosspayments",
        help="Webhook URL (default: http://localhost:3000/api/webhooks/tosspayments)"
    )
    parser.add_argument(
        "--secret",
        default="test_webhook_secret",
        help="TOSSPAYMENTS_WEBHOOK_SECRET (default: test_webhook_secret)"
    )
    args = parser.parse_args()
    
    print("╔" + "="*58 + "╗")
    print("║ Tosspayments Webhook Handler Test Suite                 ║")
    print("╚" + "="*58 + "╝")
    print(f"\nWebhook URL: {args.url}")
    print(f"Webhook Secret: {args.secret}")
    
    # Run tests
    test_payment_confirmed(args.url, args.secret)
    test_payment_failed(args.url, args.secret)
    test_payment_canceled(args.url, args.secret)
    test_invalid_signature(args.url)
    
    print("\n" + "="*60)
    print("ALL TESTS COMPLETED")
    print("="*60)


if __name__ == "__main__":
    main()
