from abc import ABC, abstractmethod

class BaseTask(ABC):

    @abstractmethod
    def to_dict(self):
        pass


class Task(BaseTask):

    def __init__(self, id, user_id, title, deadline):
        self.id = id
        self.user_id = user_id
        self.title = title
        self.deadline = deadline

    def to_dict(self):
        return {
            "id": self.id,
            "title": self.title,
            "deadline": str(self.deadline)
        }