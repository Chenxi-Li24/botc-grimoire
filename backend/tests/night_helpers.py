from app.game import GameManager, Player
from app.roles import DEMON, MINION, SCRIPT_PACKS
from app.state import SeatState


def make_game(assignments, *, claim_seat=None, night=1, script=None):
    required = set(assignments.values())
    if script is None:
        script = next((
            script_id for script_id, pack in SCRIPT_PACKS.items()
            if required <= set(pack.character_by_id)
        ), "wafu-leiming")

    game = GameManager()
    game.reset()
    game.save = lambda: None
    game.script_id = script
    game.player_count = max(5, max(assignments))
    game.seat_states = {
        seat: SeatState(seat=seat)
        for seat in range(1, game.player_count + 1)
    }
    for seat, character_id in assignments.items():
        state = game.seat_state(seat)
        state.character_id = character_id
        character = SCRIPT_PACKS[script].character_by_id.get(character_id)
        state.alignment = (
            "evil" if character and character.team in {MINION, DEMON} else "good"
        )

    player_id = None
    if claim_seat is not None:
        player_id = "test-player"
        player = Player(id=player_id, name="测试玩家", seat=claim_seat)
        game.players[player_id] = player
        game.seat_state(claim_seat).claimed_by = player_id
        player.bind(game.seat_state(claim_seat))

    game.status = "playing"
    game.phase = "night"
    game.night_no = night
    game.day_no = max(0, night - 1)
    game._bind_night_ledgers()
    game._bind_night_service()
    return game, player_id
