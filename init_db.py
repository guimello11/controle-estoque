from app import app, db, User, bcrypt
import os

def init_db():
    with app.app_context():
        # Drop all tables
        db.drop_all()
        
        # Create all tables
        db.create_all()

        # Create admin user
        try:
            hashed_password = bcrypt.generate_password_hash('admin123').decode('utf-8')
            admin = User(username='admin', password_hash=hashed_password, is_admin=True)
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
