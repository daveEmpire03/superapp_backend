import uuid

from django.contrib.auth.models import UserManager as DjangoUserManager


class UserManager(DjangoUserManager):
    use_in_migrations = True

    @staticmethod
    def _generate_internal_username():
        return f"user_{uuid.uuid4().hex[:20]}"

    def _create_user(self, email, password, **extra_fields):
        if not email:
            raise ValueError("The email address is required.")

        email = self.normalize_email(email).strip().lower()

        username = extra_fields.get("username")
        if not username:
            extra_fields["username"] = self._generate_internal_username()

        user = self.model(
            email=email,
            **extra_fields,
        )
        user.set_password(password)
        user.save(using=self._db)

        return user

    def create_user(self, email, password=None, **extra_fields):
        extra_fields.setdefault("is_staff", False)
        extra_fields.setdefault("is_superuser", False)
        extra_fields.setdefault("role", self.model.Role.CUSTOMER)

        return self._create_user(email, password, **extra_fields)

    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        extra_fields.setdefault("is_active", True)
        extra_fields.setdefault("role", self.model.Role.ADMIN)

        if extra_fields.get("is_staff") is not True:
            raise ValueError("Superuser must have is_staff=True.")

        if extra_fields.get("is_superuser") is not True:
            raise ValueError("Superuser must have is_superuser=True.")

        return self._create_user(email, password, **extra_fields)
