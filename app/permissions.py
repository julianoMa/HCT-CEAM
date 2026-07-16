from functools import wraps

from flask import abort
from flask_login import current_user


def requires_role(min_role):
    """Bloque l'accès si l'utilisateur n'est pas connecté ou si son rôle
    est strictement inférieur à min_role (0=Déclarant, 1=Membre CEAM,
    2=Président CEAM, 3=Administrateur)."""

    def decorator(view):
        @wraps(view)
        def wrapped(*args, **kwargs):
            if not current_user.is_authenticated:
                abort(401)
            if current_user.role < min_role:
                abort(403)
            return view(*args, **kwargs)

        return wrapped

    return decorator
