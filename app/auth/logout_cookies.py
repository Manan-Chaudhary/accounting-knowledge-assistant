"""Clear Chainlit JWT cookies when the FastAPI session ends (AU-87)."""

from __future__ import annotations

from fastapi import Request, Response


def clear_chainlit_auth_cookies(request: Request, response: Response) -> None:
    """End Chainlit's access_token cookies alongside the FastAPI session.

    Chainlit may chunk large JWTs as access_token, access_token_0, ...
    Paths vary when mounted under /chat, so both / and /chat are cleared.
    """
    names = {
        name
        for name in request.cookies
        if name == "access_token" or name.startswith("access_token_")
    }
    # Always attempt the default name even if not present on this request.
    names.add("access_token")

    for name in names:
        for path in ("/", "/chat"):
            response.delete_cookie(name, path=path)
