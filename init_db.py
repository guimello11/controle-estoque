from app import app, db, User

def init_db():
    with app.app_context():
        # Drop all tables
        db.drop_all()
        
        # Create all tables
        db.create_all()

        # Create admin user
        try:
            admin = User(username='admin', is_admin=True)
            admin.set_password('admin123')
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
