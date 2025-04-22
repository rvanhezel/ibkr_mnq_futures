


class MessageQueue:
    """
    A class to manage messages for the frontend.
    """
    def __init__(self):
        # For displaying warnings in the frontend
        self._messages = []
        self._trading_pause_msg = None
        self._outside_trading_schedule_msg = None

    @property
    def outside_trading_schedule_msg(self):
        return self._outside_trading_schedule_msg

    @outside_trading_schedule_msg.setter
    def outside_trading_schedule_msg(self, value: str):
        self._outside_trading_schedule_msg = value

    @property
    def trading_pause_msg(self):
        return self._trading_pause_msg

    @trading_pause_msg.setter
    def trading_pause_msg(self, value: str):
        self._trading_pause_msg = value

    @property
    def messages(self):
        return self._messages
    
    def add_message(self, message: str):
        self._messages.append(message)

    def clear(self):
        self._messages = []
        self._trading_pause_msg = None
        self._outside_trading_schedule_msg = None

    def read_message(self):
        if self._messages:
            return self._messages.pop(0)
        return None
