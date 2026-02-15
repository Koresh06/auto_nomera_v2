from dishka import Provider, provide, Scope

from src.application.mediator import Mediator



class MediatorProvider(Provider):
    scope = Scope.REQUEST

    @provide
    def mediator(
        self,
    ) -> Mediator:
        mediator = Mediator()

        return mediator