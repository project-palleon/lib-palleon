from dataclasses import dataclass


@dataclass(frozen=True)
class Dependency:
    # dataclass because this way we can change the api without having the user to change something
    name: str
    nr_history: int

    @property
    def value(self):
        return self.nr_history
