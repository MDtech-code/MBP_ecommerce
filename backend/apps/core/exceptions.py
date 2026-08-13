"""
apps/core/exceptions.py
────────────────────────
"""

from __future__ import annotations

from typing import Any


class BaseAppError(Exception):

    status_code: int = 500
    category: str = "unexpected"
    default_code: str = "app_error"
    default_notify: bool = False

    def __init__(
        self,
        message: str,
        *,
        code: str | None = None,
        client_extra: dict[str, Any] | None = None,
        internal: dict[str, Any] | None = None,
        notify: bool | None = None,
    ) -> None:
        
        super().__init__(message)
        self.message = message
        self.code = code or self.default_code
        self.client_extra = client_extra
        self.internal = internal
        self.notify = self.default_notify if notify is None else notify

    def to_envelope(self) -> dict[str, Any]:
        return {
            "category": self.category,
            "message": self.message,
            "code": self.code,
            "extra": self.client_extra,
        }


class DomainError(BaseAppError):
    

    category = "domain"
    default_code = "domain_error"
    default_notify = False

    ALLOWED_STATUS_CODES = {400, 401, 403, 404, 409, 422}

    def __init__(
        self,
        message: str,
        *,
        code: str = "domain_error",
        status_code: int = 400,
        client_extra: dict[str, Any] | None = None,
        internal: dict[str, Any] | None = None,
    ) -> None:

        if status_code not in self.ALLOWED_STATUS_CODES:
            raise ValueError(
                f"DomainError status_code must be one of "
                f"{sorted(self.ALLOWED_STATUS_CODES)}, got {status_code}. "
            )
        super().__init__(message, code=code, client_extra=client_extra, internal=internal)
        self.status_code = status_code


class AuthenticationRequiredError(DomainError):

    """ Raised when a user tries to perform an action without being logged in """

    default_code = "authentication_error"

    def __init__(self,message: str = "Authentication required.",**kwargs) -> None:
        super().__init__(message,code="authentication_error",status_code=401,**kwargs)


class PermissionDeniedError(DomainError):

    """ Raised when the user is authenticated but lacks permission """

    default_code = "permission_error"

    def __init__(self,message: str = "You do not have permission to perform this action.",**kwargs,) -> None:
        super().__init__(message,code="permission_error",status_code=403,**kwargs,)


class NotFoundError(DomainError):

    """ Raised when a resource doesn’t exist """

    default_code = "not_found"

    def __init__(self,message: str = "The requested resource was not found.",**kwargs) -> None:
        super().__init__(message,code="not_found",status_code=404,**kwargs)


class ConflictError(DomainError):

    """ Raised when there’s a state mismatch """

    default_code="Conflict"
  
    def __init__(self,message:str="The request had a conflict",**kwargs) -> None:
       super().__init__(message,code="Conflict",status_code=409,**kwargs)



class UnprocessableEntityError(DomainError):

    """ Raised when the request is syntactically valid but semantically wrong. """

    default_code="Unprocessable Entity"

    def __init__(self,message:str="The request is unprocessable",**kwargs) -> None:
        super().__init__(message,code="Unprocessable_Entity",status_code=422,**kwargs)





class InfrastructureError(BaseAppError):
    
    status_code = 503
    category = "system"
    default_code = "infrastructure_error"
    default_notify = True

    def __init__(
        self,
        message: str,
        *,
        code: str = "infrastructure_error",
        notify: bool = True,
        client_extra: dict[str, Any] | None = None,
        internal: dict[str, Any] | None = None,
    ) -> None:
       
        super().__init__(
            message,
            code=code,
            client_extra=client_extra,
            internal=internal,
            notify=notify,
        )



class InternalServerError(InfrastructureError):
    default_code = "internal_server_error"
    def __init__(self, message: str = "Unexpected server error.", **kwargs) -> None:
        super().__init__(message, code="internal_server_error", **kwargs)
        self.status_code = 500


class BadGatewayError(InfrastructureError):
    default_code = "bad_gateway_error"
    def __init__(self, message: str = "Upstream service returned invalid response.", **kwargs) -> None:
        super().__init__(message, code="bad_gateway", **kwargs)
        self.status_code = 502


class GatewayTimeoutError(InfrastructureError):
    default_code = "gateway_timeout_error"
    def __init__(self, message: str = "Upstream service timed out.", **kwargs) -> None:
        super().__init__(message, code="gateway_timeout", **kwargs)
        self.status_code = 504




