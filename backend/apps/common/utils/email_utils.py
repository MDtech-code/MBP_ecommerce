def mask_email(email: str) -> str:
    """user@example.com → u***@example.com"""
    local, domain = email.split("@", 1)
    return f"{local[0]}***@{domain}"