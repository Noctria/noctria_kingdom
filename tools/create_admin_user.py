from airflow import settings
from airflow.models import DagBag
from airflow.www.security import AirflowSecurityManager
from airflow.www.app import create_app
from airflow.utils.db import create_session
from flask_appbuilder.security.sqla.models import User
from flask_appbuilder.security.manager import AUTH_DB

app = create_app(config=settings.conf)

with app.app_context():
    sm: AirflowSecurityManager = app.appbuilder.sm
    if not sm.find_user(username="admin"):
        print("🛠️ Creating default admin user...")
        sm.add_user(
            username="admin",
            first_name="Admin",
            last_name="User",
            email="admin@example.com",
            role=sm.find_role("Admin"),
            password="admin"
        )
    else:
        print("✅ Admin user already exists.")
