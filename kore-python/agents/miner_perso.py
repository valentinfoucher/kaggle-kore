# import {Board} from "./kore/Board";
# import { Direction } from "./kore/Direction";
# import { ShipyardAction } from "./kore/ShipyardAction";
# import { KoreIO } from "./kore/KoreIO";
from kaggle_environments.envs.kore_fleets.helpers import *
from random import randint
import math


def getRandomInt(min, max):
    return random.randint(min, max)


def agent(obs, config):
    board = Board(obs, config)
    me = board.current_player
    turn = board.step
    spawn_cost = board.configuration.spawn_cost
    kore_left = me.kore

    convert_cost = board.configuration.convert_cost
    remainingKore = me.kore

    for shipyard in me.shipyards:
        if(remainingKore > 1000 and shipyard.max_spawn > 5):
            if(shipyard.ship_count >= convertCost + 10):
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
                    convertCost + 10, math.floor(shipyard.shipCount / 2))
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
            gap1 = getRandomInt(3, 9)
            gap2 = getRandomInt(3, 9)
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
            action = ShipyardAction.launch_fleet_with_flight_plan(
                21, flightPlan)
            shipyard.next_action = action
        elif(remainingKore > board.configuration.spawn_cost * shipyard.max_spawn):
            remainingKore -= board.configuration.spawn_cost
            if(remainingKore >= spawn_cost):
                action = ShipyardAction.spawn_ships(
                    min(shipyard.max_spawn, math.floor(remainingKore / spawn_cost)))
                shipyard.next_action = action

        elif(shipyard.ship_count >= 2):
            dirStr = Direction.random_direction().to_char()
            action = ShipyardAction.launch_fleet_with_flight_plan(2, dirStr)
            shipyard.next_action = action
    return me.next_actions
