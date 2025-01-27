class AuthDuplicateError(Exception):
    pass


class AuthBannedError(Exception):
    pass


class UserNotVerifiedError(Exception):
    def __init__(self, email: str, provider: str):
        self.email = email
        self.provider = provider
        super().__init__(f"{email} is not verified")


class FailedRegistrationError(Exception):
    def __init__(self, detail: str):
        self.detail = detail
        super().__init__(detail)


class ValidationError(Exception):
    def __init__(self, detail: str):
        self.detail = detail
        super().__init__(detail)
