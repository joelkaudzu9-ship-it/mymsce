# migrate_lesson_model.py
from app import app, db
from models import Lesson
from sqlalchemy import inspect, text


def add_columns():
    """Add new columns to lesson table if they don't exist"""
    with app.app_context():
        inspector = inspect(db.engine)
        columns = [col['name'] for col in inspector.get_columns('lesson')]

        # Add content_type column
        if 'content_type' not in columns:
            db.session.execute(text('ALTER TABLE lesson ADD COLUMN content_type VARCHAR(20) DEFAULT "video"'))
            print("✅ Added content_type column")

        # Add file_path column
        if 'file_path' not in columns:
            db.session.execute(text('ALTER TABLE lesson ADD COLUMN file_path VARCHAR(500)'))
            print("✅ Added file_path column")

        # Add file_size column
        if 'file_size' not in columns:
            db.session.execute(text('ALTER TABLE lesson ADD COLUMN file_size INTEGER DEFAULT 0'))
            print("✅ Added file_size column")

        # Add file_name column
        if 'file_name' not in columns:
            db.session.execute(text('ALTER TABLE lesson ADD COLUMN file_name VARCHAR(200)'))
            print("✅ Added file_name column")

        # Add downloadable column
        if 'downloadable' not in columns:
            db.session.execute(text('ALTER TABLE lesson ADD COLUMN downloadable BOOLEAN DEFAULT 0'))
            print("✅ Added downloadable column")

        db.session.commit()
        print("🎉 Migration complete!")


if __name__ == "__main__":
    add_columns()