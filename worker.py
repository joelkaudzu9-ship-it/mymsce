# worker.py - Run this as a background process on Render
import os
import time
import requests
from datetime import datetime, timedelta
from app import app, db
from models import Payment, User
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def check_pending_payments():
    """Check pending payments with PayChangu API"""
    with app.app_context():
        logger.info(f"🔍 Checking pending payments at {datetime.utcnow()}")

        # Find pending payments older than 2 minutes
        cutoff = datetime.utcnow() - timedelta(minutes=2)
        pending = Payment.query.filter_by(status='pending').filter(
            Payment.created_at < cutoff
        ).all()

        logger.info(f"Found {len(pending)} pending payments")

        for payment in pending:
            logger.info(f"Checking payment {payment.id}: {payment.reference}")

            # Try to verify with PayChangu
            try:
                headers = {
                    "Accept": "application/json",
                    "Authorization": f"Bearer {os.environ.get('PAYCHANGU_SECRET_KEY')}"
                }

                # Try different verification endpoints
                endpoints = [
                    f"https://api.paychangu.com/transactions/verify/{payment.transaction_id or payment.charge_id}",
                    f"https://api.paychangu.com/verify-payment/{payment.reference}",
                    f"https://api.paychangu.com/mobile-money/payments/{payment.charge_id}/verify"
                ]

                verified = False
                for url in endpoints:
                    try:
                        response = requests.get(url, headers=headers, timeout=10)
                        if response.status_code == 200:
                            data = response.json()
                            status = data.get('status') or data.get('data', {}).get('status')

                            if status in ['success', 'successful', 'completed']:
                                # Activate user
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

                                logger.info(f"✅ AUTO-VERIFIED payment {payment.id}")
                                verified = True
                                break
                    except Exception as e:
                        logger.error(f"Error with {url}: {e}")
                        continue

                if not verified:
                    logger.info(f"⏳ Payment {payment.id} still pending")

            except Exception as e:
                logger.error(f"Error checking payment {payment.id}: {e}")


if __name__ == "__main__":
    logger.info("🚀 Worker started")
    while True:
        try:
            check_pending_payments()
        except Exception as e:
            logger.error(f"Worker error: {e}")

        # Wait 3 minutes before next check
        time.sleep(180)