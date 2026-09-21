"""Single-table process lifetime dependencies."""

from ..game import GameManager
from .realtime import Hub

game = GameManager()
hub = Hub(game)
