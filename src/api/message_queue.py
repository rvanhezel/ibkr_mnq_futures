


class MessageQueue:
    """
    A class to manage messages for the frontend.
    """
    def __init__(self):
        # For displaying warnings in the frontend
        self._messages = []
        
    @property
    def messages(self):
        return self._messages
    
    def add_message(self, message: str):
        self._messages.append(message)

    def clear_messages(self):
        self._messages = []

    def read_message(self):
        if self._messages:
            return self._messages.pop(0)
        return None
