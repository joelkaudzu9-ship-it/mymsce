# auto_verify.py - Run this every 5 minutes via cron/task scheduler
from app import app, db
from models import Payment, User
from datetime import datetime, timedelta
import requests
import time
import os


def verify_pending_payments():
    """Check pending payments with PayChangu API and auto-activate"""
    with app.app_context():
        print(f"\n🔄 Running auto-verify at {datetime.utcnow()}")

        # Find all pending payments older than 2 minutes
        cutoff = datetime.utcnow() - timedelta(minutes=2)
        pending = Payment.query.filter_by(status='pending').filter(
            Payment.created_at < cutoff
        ).all()

        print(f"Found {len(pending)} pending payments to verify")

        for payment in pending:
            print(f"\nChecking payment {payment.id}: {payment.reference}")

            # Try to verify with PayChangu
            try:
                headers = {
                    "Accept": "application/json",
                    "Authorization": f"Bearer {os.getenv('PAYCHANGU_SECRET_KEY')}"
                }

                # Try different endpoints
                endpoints = [
                    f"https://api.paychangu.com/transactions/verify/{payment.transaction_id or payment.charge_id}",
                    f"https://api.paychangu.com/verify-payment/{payment.reference}",
                    f"https://api.paychangu.com/mobile-money/payments/{payment.charge_id}/verify"
                ]

                for url in endpoints:
                    try:
                        response = requests.get(url, headers=headers, timeout=10)
                        if response.status_code == 200:
                            data = response.json()
                            status = data.get('status') or data.get('data', {}).get('status')

                            if status in ['success', 'successful', 'completed']:
                                # Activate!
                                payment.status = 'completed'
                                payment.completed_at = datetime.utcnow()

                                user = User.query.get(payment.user_id)
                                days_map = {'daily': 1, 'weekly': 7, 'monthly': 30}
                                days = days_map.get(payment.subscription_type, 1)

                                if user.subscription_expiry and user.subscription_expiry > datetime.utcnow():
                                    user.subscription_expiry += timedelta(days=days)
                                else:
                                    user.subscription_expiry = datetime.utcnow() + timedelta(days=days)

                                user.is_active_subscriber = True
                                db.session.commit()
                                print(f"✅ AUTO-ACTIVATED {user.username}")
                                break
                    except:
                        continue

            except Exception as e:
                print(f"Error: {e}")


if __name__ == "__main__":
    verify_pending_payments()