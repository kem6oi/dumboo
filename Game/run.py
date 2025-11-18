# run.py

import os
from app import create_app # <-- Only import create_app here

# Import Migrate and models are now handled within create_app and shell_context_processor

app = create_app()

# db and migrate are now initialized via app = create_app()

with app.app_context():
    from app import db # Import db locally within context
    db_path = app.config.get('SQLALCHEMY_DATABASE_URI')
    if db_path.startswith('sqlite:///'):
         db_file = db_path.replace('sqlite:///', '', 1)
         # Check if the database file exists relative to app.root_path
         full_db_path = os.path.join(app.root_path, db_file)
         if not os.path.exists(full_db_path):
             print(f"Database file '{db_file}' not found. Creating tables...")
             db.create_all()
             print("Tables created.")
    else:
        # For other databases, you might need different checks or rely solely on migrations
         print("Using non-SQLite database. Ensure migrations are applied via 'flask db upgrade'.")
         # Optionally call db.create_all() here unconditionally for other DBs,
         # but be aware it might fail if tables partially exist.
         # db.create_all()
# --- End of added block ---ocessor
def make_shell_context():
    # Import db and models locally within the shell context function
    # This avoids top-level imports that could contribute to cycles
    from app import db
    from app.models import User, Challenge, Product, Purchase, SolvedChallenge
    return {'db': db, 'User': User, 'Challenge': Challenge, 'Product': Product, 'Purchase': Purchase, 'SolvedChallenge': SolvedChallenge}

if __name__ == '__main__':
    # Ensure upload folders exist - Use app.root_path
    # This needs the app instance, which is available
    upload_folder = os.path.join(app.root_path, app.config['UPLOAD_FOLDER'])
    product_pics_folder = os.path.join(upload_folder, 'product_pics')
    os.makedirs(product_pics_folder, exist_ok=True)

    app.run(debug=True)
