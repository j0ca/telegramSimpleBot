class AppSettings:
    def __init__(self, token, name, botName):
        self.token = token
        self.name = name
        self.botName = botName

    @classmethod
    def from_dict(cls, config_dict):
        return cls(**config_dict)