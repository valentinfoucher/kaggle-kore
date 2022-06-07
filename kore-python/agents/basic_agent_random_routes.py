from kaggle_environments.envs.kore_fleets.helpers import *
from random import randint

# basic agent
# with random routes


def agent(obs, config):
    board = Board(obs, config)
    me = board.current_player

    me = board.current_player
    turn = board.step
    spawn_cost = board.configuration.spawn_cost
    kore_left = me.kore
    # flight_plans = ['N', 'S', 'E', 'W',
    #                 "N2E2S2W2", "N3E3S3W", "N4E4S4W", "N5E5S5W"]
    flight_plans = [
        "NESW", "NWSE", "SWNE", "SENW", "N", "W", "S", "E"]

    for shipyard in me.shipyards:
        flight_plan = random.choice(flight_plans)
        if shipyard.ship_count > 10:
            direction = Direction.from_index(turn % 4)
            action = ShipyardAction.launch_fleet_with_flight_plan(
                12, flight_plan)
            shipyard.next_action = action
        elif kore_left > spawn_cost * shipyard.max_spawn:
            action = ShipyardAction.spawn_ships(shipyard.max_spawn)
            shipyard.next_action = action
            kore_left -= spawn_cost * shipyard.max_spawn
        elif kore_left > spawn_cost:
            action = ShipyardAction.spawn_ships(1)
            shipyard.next_action = action
            kore_left -= spawn_cost

    return me.next_actions
