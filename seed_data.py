# seed_data.py
from app import app, db
from models import User, Subject, Lesson
from datetime import datetime


def seed_database():
    with app.app_context():
        # Create admin if not exists
        admin = User.query.filter_by(email='admin@mymsce.com').first()
        if not admin:
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
            print("✅ Admin user created")

        # Create subjects
        subjects_data = [
            # Form 3 Subjects
            {'name': 'Mathematics', 'form': 3, 'description': 'Form 3 Mathematics - Algebra, Geometry, Trigonometry',
             'icon': 'calculator', 'order': 1},
            {'name': 'Physics', 'form': 3, 'description': 'Form 3 Physics - Mechanics, Waves, Electricity',
             'icon': 'flask', 'order': 2},
            {'name': 'Chemistry', 'form': 3, 'description': 'Form 3 Chemistry - Atomic Structure, Bonding, Reactions',
             'icon': 'beaker', 'order': 3},
            {'name': 'Biology', 'form': 3, 'description': 'Form 3 Biology - Cells, Tissues, Nutrition', 'icon': 'leaf',
             'order': 4},

            # Form 4 Subjects
            {'name': 'Mathematics', 'form': 4, 'description': 'Form 4 Mathematics - Calculus, Statistics, Probability',
             'icon': 'calculator', 'order': 1},
            {'name': 'Physics', 'form': 4, 'description': 'Form 4 Physics - Modern Physics, Electronics, Nuclear',
             'icon': 'flask', 'order': 2},
            {'name': 'Chemistry', 'form': 4, 'description': 'Form 4 Chemistry - Organic Chemistry, Equilibrium',
             'icon': 'beaker', 'order': 3},
            {'name': 'Biology', 'form': 4, 'description': 'Form 4 Biology - Genetics, Evolution, Ecology',
             'icon': 'leaf', 'order': 4},
        ]

        for subj_data in subjects_data:
            subject = Subject.query.filter_by(name=subj_data['name'], form=subj_data['form']).first()
            if not subject:
                subject = Subject(**subj_data)
                db.session.add(subject)
                print(f"✅ Created subject: {subj_data['name']} Form {subj_data['form']}")

        db.session.commit()

        # Create free sample lessons
        math_form3 = Subject.query.filter_by(name='Mathematics', form=3).first()
        if math_form3:
            free_lessons = [
                {
                    'title': 'Introduction to Algebra - Free Sample',
                    'description': 'Learn the basics of algebraic expressions and equations',
                    'content': '<h3>What is Algebra?</h3><p>Algebra is a branch of mathematics dealing with symbols and the rules for manipulating those symbols.</p><h4>Key Concepts:</h4><ul><li>Variables</li><li>Expressions</li><li>Equations</li></ul>',
                    'video_url': 'https://www.youtube.com/watch?v=NybHckSEQBI',
                    'video_type': 'youtube',
                    'duration': 15,
                    'is_free': True,
                    'order': 1
                },
                {
                    'title': 'Linear Equations - Free Sample',
                    'description': 'Understanding and solving linear equations',
                    'content': '<h3>Linear Equations</h3><p>Linear equations are equations of the first degree.</p>',
                    'video_url': 'https://www.youtube.com/watch?v=7DPWeB01NS8',
                    'video_type': 'youtube',
                    'duration': 20,
                    'is_free': True,
                    'order': 2
                }
            ]

            for lesson_data in free_lessons:
                lesson = Lesson.query.filter_by(title=lesson_data['title']).first()
                if not lesson:
                    lesson = Lesson(
                        subject_id=math_form3.id,
                        form=3,
                        **lesson_data
                    )
                    db.session.add(lesson)
                    print(f"✅ Created free lesson: {lesson_data['title']}")

        db.session.commit()
        print("\n🎉 Database seeded successfully!")
        print("\nAdmin Login:")
        print("Email: admin@mymsce.com")
        print("Password: admin123")


if __name__ == '__main__':
    seed_database()