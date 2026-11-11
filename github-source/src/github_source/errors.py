"""Stable acquisition errors; content activation is always the caller's decision."""


class GitHubError(Exception):
    def __init__(self, code, message, *, status=None, retry_after=None):
        super().__init__(message)
        self.code = code
        self.status = status
        self.retry_after = retry_after

    def to_dict(self):
        result = {"code": self.code, "message": str(self)}
        if self.status is not None:
            result["status"] = self.status
        if self.retry_after is not None:
            result["retry_after"] = self.retry_after
        return result
