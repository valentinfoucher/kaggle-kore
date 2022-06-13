# import {Board} from "./kore/Board";
# import { Direction } from "./kore/Direction";
# import { ShipyardAction } from "./kore/ShipyardAction";
# import { KoreIO } from "./kore/KoreIO";
from kaggle_environments.envs.kore_fleets.helpers import *
from random import randint
import math

possible_sizes_fleet = [2, 3, 5, 8, 13, 21, 34]


def process_direction(pos, direction):
    (x, y) = pos
    if direction == 'N':
        return (x, (y+1) % 21)
    if direction == 'S':
        return (x, (y-1) % 21)
    if direction == 'E':
        return ((x+1) % 21, y)
    else:
        return ((x-1) % 21, y)


def process_flight_plan(pos_start, flight_plan):
    (x_start, y_start) = pos_start
    route = []
    current_dir = flight_plan[0]
    current_pos = process_direction((x_start, y_start), current_dir)
    route.append(current_pos)
    for instruction in flight_plan[1:]:
        if instruction in ['N', 'S', 'E', 'W']:
            current_dir = instruction
            current_pos = process_direction(current_pos, current_dir)
            route.append(current_pos)
        else:
            for i in range(int(instruction)):
                current_pos = process_direction(current_pos, current_dir)
                route.append(current_pos)
    return route


def compute_kore_route(kore_map_dict, route):
    total_kore = 0
    for pos in route:
        total_kore += kore_map_dict[pos].kore
    return total_kore


def getRandomInt(min, max):
    return random.randint(min, max)


def random_rectangle_flight_plan(board):
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
    return flightPlan


def launch_best_random_rectangle_ship(shipyard, board, N):
    routes = []
    for i in range(N):
        flight_plan = random_rectangle_flight_plan(board)
        route = process_flight_plan(shipyard.position, flight_plan)
        kore_count = compute_kore_route(board.cells, route)
        average_kore = kore_count//(len(route))
        routes.append([flight_plan, average_kore])
    flight_plan = max(routes, key=lambda k: k[1])[0]

    fleet_size = max(
        [s for s in possible_sizes_fleet if s <= shipyard.ship_count])

    action = ShipyardAction.launch_fleet_with_flight_plan(
        fleet_size, flight_plan)
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
        if(remainingKore > 1000 and shipyard.max_spawn > 5):
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
                flightPlan += 'C'
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
            launch_best_random_rectangle_ship(shipyard, board, 10)

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
