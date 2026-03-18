# reset_db.py
import os
from app import app, db
from models import User, Subject, Lesson, Payment, EmailVerification, PasswordReset


def reset_database():
    """Completely reset the database"""
    with app.app_context():
        # Drop all tables
        print("🗑️  Dropping all tables...")
        db.drop_all()

        # Create all tables fresh
        print("🏗️  Creating fresh tables...")
        db.create_all()

        # Create admin user
        print("👤 Creating admin user...")
        admin = User(
            username='admin',
            email='admin@mymsce.com',
            phone='0999123456',
            is_admin=True,
            is_verified=True,
            email_verified=True
        )
        admin.set_password('admin123')
        db.session.add(admin)

        # Create sample subjects
        print("📚 Creating sample subjects...")
        subjects = [
            {'name': 'Mathematics', 'form': 3, 'description': 'Form 3 Mathematics', 'icon': 'calculator', 'order': 1},
            {'name': 'Physics', 'form': 3, 'description': 'Form 3 Physics', 'icon': 'flask', 'order': 2},
            {'name': 'Chemistry', 'form': 3, 'description': 'Form 3 Chemistry', 'icon': 'beaker', 'order': 3},
            {'name': 'Mathematics', 'form': 4, 'description': 'Form 4 Mathematics', 'icon': 'calculator', 'order': 1},
            {'name': 'Physics', 'form': 4, 'description': 'Form 4 Physics', 'icon': 'flask', 'order': 2},
            {'name': 'Chemistry', 'form': 4, 'description': 'Form 4 Chemistry', 'icon': 'beaker', 'order': 3},
            {'name': 'Biology', 'form': 4, 'description': 'Form 4 Biology', 'icon': 'leaf', 'order': 4},
        ]

        for subj in subjects:
            subject = Subject(**subj)
            db.session.add(subject)

        db.session.commit()

        # Create free sample lessons
        print("🎓 Creating free sample lessons...")
        math_3 = Subject.query.filter_by(name='Mathematics', form=3).first()

        if math_3:
            lessons = [
                {
                    'title': 'Introduction to Algebra - Free Sample',
                    'description': 'Learn the basics of algebraic expressions',
                    'content': '<h3>What is Algebra?</h3><p>Algebra is a branch of mathematics dealing with symbols.</p>',
                    'video_url': 'https://www.youtube.com/watch?v=NybHckSEQBI',
                    'video_type': 'youtube',
                    'duration': 15,
                    'subject_id': math_3.id,
                    'form': 3,
                    'is_free': True,
                    'order': 1
                },
                {
                    'title': 'Linear Equations - Free Sample',
                    'description': 'Understanding linear equations',
                    'content': '<h3>Linear Equations</h3><p>Equations of the first degree.</p>',
                    'video_url': 'https://www.youtube.com/watch?v=7DPWeB01NS8',
                    'video_type': 'youtube',
                    'duration': 20,
                    'subject_id': math_3.id,
                    'form': 3,
                    'is_free': True,
                    'order': 2
                }
            ]

            for les in lessons:
                lesson = Lesson(**les)
                db.session.add(lesson)

        db.session.commit()

        print("\n✅ Database reset complete!")
        print("=" * 40)
        print("Admin Login:")
        print("  Email: admin@mymsce.com")
        print("  Password: admin123")
        print("=" * 40)


if __name__ == "__main__":
    # Ask for confirmation
    response = input("⚠️  This will DELETE ALL DATA. Are you sure? (yes/no): ")
    if response.lower() == 'yes':
        reset_database()
    else:
        print("❌ Reset cancelled.")