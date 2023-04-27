class EndpointError(Exception):
    """Ошибка, если эндпойнт не корректен."""
    pass


class ResponseFormatError(Exception):
    """Ошибка, если формат response не json."""
    pass
