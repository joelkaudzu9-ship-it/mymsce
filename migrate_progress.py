# migrate_progress.py
from app import app, db
from sqlalchemy import inspect, text


def add_created_at_column():
    """Add created_at column to progress table if it doesn't exist"""
    with app.app_context():
        inspector = inspect(db.engine)
        columns = [col['name'] for col in inspector.get_columns('progress')]

        if 'created_at' not in columns:
            print("➕ Adding created_at column to progress table...")
            db.session.execute(text('ALTER TABLE progress ADD COLUMN created_at TIMESTAMP'))
            db.session.commit()
            print("✅ Column added successfully!")
        else:
            print("✅ created_at column already exists")


if __name__ == "__main__":
    add_created_at_column()