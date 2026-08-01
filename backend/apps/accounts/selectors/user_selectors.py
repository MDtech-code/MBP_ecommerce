# apps/accounts/selectors/user_selectors.py


from apps.accounts.models import User




def get_user_by_email(email: str) -> User | None:
    """Return User with this email or None. Used for existence checks."""
    return User.objects.filter(email=email.lower().strip()).first()



def email_exists(email: str, exclude_user_id: int | None = None) -> bool:
    """Return True if this email is already registered."""
    qs = User.objects.filter(email=email.lower().strip())
    if exclude_user_id:
        qs = qs.exclude(id=exclude_user_id)
    return qs.exists()