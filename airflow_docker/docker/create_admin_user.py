# create_admin_user.py

from airflow.models import User
from airflow.utils.db import provide_session
from sqlalchemy.orm import Session

# 管理者アカウントの初期値（必要に応じて環境変数にしてもよい）
username = "admin"
password = "admin"
email = "admin@example.com"
firstname = "Admin"
lastname = "User"


@provide_session
def create_admin_user(session: Session = None):
    if session.query(User).filter(User.username == username).first():
        print(f"✅ Admin user '{username}' already exists.")
        return

    user = User(
        username=username,
        email=email,
        is_active=True,
        is_superuser=True,
        first_name=firstname,
        last_name=lastname,
    )
    user.password = password
    session.add(user)
    session.commit()
    print(f"🎉 Created admin user: {username}")


if __name__ == "__main__":
    create_admin_user()
