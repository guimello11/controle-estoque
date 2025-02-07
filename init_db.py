from app import app, db, User
from werkzeug.security import generate_password_hash

def init_db():
    with app.app_context():
        # Drop all tables
        db.drop_all()
        
        # Create all tables
        db.create_all()

        # Create admin user
        try:
            admin = User(
                username='admin',
                password_hash=generate_password_hash('admin123', method='scrypt'),
                is_admin=True
            )
            db.session.add(admin)
            db.session.commit()
            print('Database initialized successfully!')
            print('Admin user created with:')
            print('Username: admin')
            print('Password: admin123')
        except Exception as e:
            print(f'Error creating admin user: {str(e)}')
            db.session.rollback()
            raise

if __name__ == '__main__':
    init_db()
