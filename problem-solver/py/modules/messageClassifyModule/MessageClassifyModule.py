from sc_kpm import ScModule
from .MessageClassifyAgent import MessageClassifyAgent


class MessageClassifyModule(ScModule):
    def __init__(self):
        super().__init__(MessageClassifyAgent())
