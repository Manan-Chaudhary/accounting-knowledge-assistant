"""FastAPI-owned authentication helpers.

Chainlit must not validate passwords. It will later accept the identity
already established here via header_auth_callback (AU-83, AU-84).
"""

ALLOWED_ROLES = frozenset({"staff", "admin", "team"})

SESSION_USER_ID_KEY = "user_id"
SESSION_EMAIL_KEY = "email"
SESSION_ROLE_KEY = "role"

EMAIL_MAX_LENGTH = 254
PASSWORD_MAX_LENGTH = 128
