"""Named result object shared by public functions that return several quantities."""


class Result(dict):
    """Mapping of named results with attribute access.

    This follows ``scipy.optimize.OptimizeResult``: a ``dict`` subclass, so
    existing mapping use keeps working, whose keys can also be read as
    attributes. Each function documents its fields under ``Returns``.

    Examples
    --------
    >>> result = Result(B=5.0)
    >>> result.B == result["B"] == 5.0
    True
    """

    def __getattr__(self, name):
        try:
            return self[name]
        except KeyError as error:
            raise AttributeError(name) from error

    def __dir__(self):
        return sorted(set(super().__dir__()) | set(self))


__all__ = ["Result"]
