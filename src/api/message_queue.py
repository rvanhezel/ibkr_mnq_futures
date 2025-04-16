


class MessageQueue:
    """
    A class to manage messages for the frontend.
    """
    def __init__(self):
        self._messages = []
        self._sys_errors = []

    @property
    def messages(self):
        return self._messages
    
    @property
    def sys_errors(self):
        return self._sys_errors
    
    def add_message(self, message: str):
        self._messages.append(message)

    def clear_messages(self):
        self._messages = []

    def add_sys_error(self, error: str):
        self._sys_errors.append(error)

    def clear_sys_errors(self):
        self._sys_errors = []

    def read_message(self):
        if self._messages:
            return self._messages.pop(0)
        return None

    def read_sys_error(self):
        if self._sys_errors:
            return self._sys_errors.pop(0)
