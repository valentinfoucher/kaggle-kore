# import {Board} from "./kore/Board";
# import { Direction } from "./kore/Direction";
# import { ShipyardAction } from "./kore/ShipyardAction";
# import { KoreIO } from "./kore/KoreIO";
from kaggle_environments.envs.kore_fleets.helpers import *
from random import randint
import math

possible_sizes_fleet = [2, 3, 5, 8, 13, 21, 34]


def getRandomInt(min, max):
    return random.randint(min, max)


def launch_rectangle_ship(shipyard, board):
    turn = board.step
    max_length = min(1+turn//20, 9)
    gap1 = getRandomInt(0, max_length)
    gap2 = getRandomInt(0, max_length)
    startDir = getRandomInt(0, 3)
    flightPlan = Direction.list_directions(
    )[startDir].to_char() + str(gap1)
    nextDir = (startDir + 1) % 4
    flightPlan += Direction.list_directions(
    )[nextDir].to_char() + str(gap2)
    nextDir2 = (nextDir + 1) % 4
    flightPlan += Direction.list_directions()[
        nextDir2].to_char() + str(gap1)
    nextDir3 = (nextDir2 + 1) % 4
    flightPlan += Direction.list_directions()[nextDir3].to_char()

    fleet_size = max(
        [s for s in possible_sizes_fleet if s <= shipyard.ship_count])

    action = ShipyardAction.launch_fleet_with_flight_plan(
        fleet_size, flightPlan)
    shipyard.next_action = action


def agent(obs, config):
    board = Board(obs, config)
    me = board.current_player
    turn = board.step
    spawn_cost = board.configuration.spawn_cost
    kore_left = me.kore

    convert_cost = board.configuration.convert_cost
    remainingKore = me.kore

    # possible_sizes_fleet = [2, 3, 5, 8, 13, 21, 34]

    for shipyard in me.shipyards:
        if(remainingKore > 200 and shipyard.max_spawn > 5):
            if(shipyard.ship_count >= convert_cost + 10):
                gap1 = getRandomInt(3, 9)
                gap2 = getRandomInt(3, 9)
                startDir = getRandomInt(0, 3)
                flightPlan = Direction.list_directions()[
                    startDir].to_char() + str(gap1)
                nextDir = (startDir + 1) % 4
                flightPlan += Direction.list_directions()[
                    nextDir].to_char() + str(gap2)
                nextDir2 = (nextDir + 1) % 4
                flightPlan += Direction.list_directions()[nextDir2].to_char()
                nb_ships_to_spawn = min(
                    convert_cost + 10, math.floor(shipyard.ship_count / 2))
                action = ShipyardAction.launch_fleet_with_flight_plan(
                    nb_ships_to_spawn, flightPlan)
                shipyard.next_action = action

            elif(remainingKore >= spawn_cost):
                remainingKore -= spawn_cost
                nb_ships_to_spawn = min(
                    shipyard.max_spawn, math.floor(remainingKore / spawn_cost))
                action = ShipyardAction.spawn_ships(nb_ships_to_spawn)
                shipyard.next_action = action

        elif(shipyard.ship_count >= 21):
            launch_rectangle_ship(shipyard, board)
            # max_length = min(1+turn//20, 9)
            # gap1 = getRandomInt(0, max_length)
            # gap2 = getRandomInt(0, max_length)
            # startDir = getRandomInt(0, 3)
            # flightPlan = Direction.list_directions(
            # )[startDir].to_char() + str(gap1)
            # nextDir = (startDir + 1) % 4
            # flightPlan += Direction.list_directions(
            # )[nextDir].to_char() + str(gap2)
            # nextDir2 = (nextDir + 1) % 4
            # flightPlan += Direction.list_directions()[
            #     nextDir2].to_char() + str(gap1)
            # nextDir3 = (nextDir2 + 1) % 4
            # flightPlan += Direction.list_directions()[nextDir3].to_char()

            # fleet_size = max(
            #     [s for s in possible_sizes_fleet if s <= shipyard.ship_count])

            # action = ShipyardAction.launch_fleet_with_flight_plan(
            #     fleet_size, flightPlan)
            # shipyard.next_action = action
        elif(remainingKore > board.configuration.spawn_cost * shipyard.max_spawn):
            remainingKore -= board.configuration.spawn_cost
            if(remainingKore >= spawn_cost):
                action = ShipyardAction.spawn_ships(
                    min(shipyard.max_spawn, math.floor(remainingKore / spawn_cost)))
                shipyard.next_action = action

        elif(shipyard.ship_count >= 2):
            dirStr = Direction.random_direction().to_char()
            count_spawn = shipyard.ship_count
            action = ShipyardAction.launch_fleet_with_flight_plan(
                count_spawn, dirStr)
            shipyard.next_action = action
    return me.next_actions
