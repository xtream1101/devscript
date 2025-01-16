class BearAuthException(Exception):
    pass


class DuplicateError(Exception):
    pass


class UserNotVerifiedError(Exception):
    # take in the user and the provider
    def __init__(self, email: str, provider: str):
        self.email = email
        self.provider = provider
        super().__init__(f"{email} is not verified")


class FailedLoginError(Exception):
    def __init__(self, detail: str):
        self.detail = detail
        super().__init__(detail)


class FailedRegistrationError(Exception):
    def __init__(self, detail: str):
        self.detail = detail
        super().__init__(detail)


class GenericException(Exception):
    def __init__(self, detail: str):
        self.detail = detail
        super().__init__(detail)
