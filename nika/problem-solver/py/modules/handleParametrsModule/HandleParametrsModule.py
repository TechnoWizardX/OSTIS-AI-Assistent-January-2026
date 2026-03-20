from sc_kpm import ScModule
from .DecreaseParametrAgent import DecreaseParametrAgent
from .IncreaseParametrAgent import IncreaseParametrAgent
from .OpenApplicationAgent import OpenApplicationAgent
from .CloseApplicationAgent import CloseApplicationAgent
from .ActivateButtonAgent import ActivateButtonAgent
from .DeactivateButtonAgent import DeactivateButtonAgent

"""добавляем агента"""
class HandleParametrsModule(ScModule):
    def __init__(self):
        super().__init__(DecreaseParametrAgent(),
                          IncreaseParametrAgent(),
                            OpenApplicationAgent(),
                              CloseApplicationAgent(),
                                ActivateButtonAgent(),
                                DeactivateButtonAgent()
                              )

