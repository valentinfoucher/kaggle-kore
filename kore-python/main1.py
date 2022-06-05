from itertools import combinations
import json
from kaggle_environments import make
import os
import re
import json
import enum
import glob
import shutil
import collections
import requests
import pickle

import numpy as np
import matplotlib
import matplotlib.animation
import matplotlib.patheffects
import matplotlib.pyplot as plt
import IPython.display

import kaggle_environments

import logging
import logstash
import sys
import uuid

# make a UUID based on the host address and current time
#uuidOne = uuid.uuid1()


host = 'localhost'

test_logger = logging.getLogger('python-logstash-logger')
test_logger.setLevel(logging.INFO)
# test_logger.addHandler(logstash.LogstashHandler(host, 5000, version=1))
test_logger.addHandler(logstash.TCPLogstashHandler(host, 5000, version=1))


env = make("kore_fleets")
# The list of available default agents.
f = open('agents.json')
agents = json.load(f)
f.close()


class FlightPlanClass(enum.IntEnum):
    invalid = 0
    unknown = 1
    acyclic = 2
    boomerang = 3
    rectangle = 4


def kore_mining_rate(kore_amount, fleetsize):
    kore_amount_before_regeneration = kore_amount / 1.02
    if kore_amount_before_regeneration < 500:
        kore_amount = kore_amount_before_regeneration
    precentage_mining_rate = np.log(max(1, fleetsize)) / 20
    kore_amount = kore_amount / (1-precentage_mining_rate)
    return kore_amount * precentage_mining_rate


def calculate_mining_rates(kore_amount_matrices, agent_fleetsize_matrices):
    return [sum(kore_mining_rate(kore_amount, fleetsize)
                for kore_amount, fleetsize in zip(kore_amounts, fleetsizes))
            for kore_amounts, fleetsizes in zip(kore_amount_matrices, agent_fleetsize_matrices)]


def split_into_number_and_char(srr):
    # https://stackoverflow.com/q/430079/5894029
    arr = []
    for word in re.split('(\d+)', srr):
        try:
            num = int(word)
            arr.append(num)
        except ValueError:
            for c in word:
                arr.append(c)
    return arr


def extract_flight_plan(x, y, dir_idx, plan, endpoints=set()):
    dir_to_dxdy = [(0, 1), (1, 0), (0, -1), (-1, 0)]  # NESW
    dcode_to_dxdy = {"N": (0, 1), "E": (1, 0), "S": (0, -1), "W": (-1, 0)}
    dx, dy = dir_to_dxdy[dir_idx]

    reflected_endpoints = set()
    for ex, ey in endpoints:
        for zx in [-1, 0, 1]:
            for zy in [-1, 0, 1]:
                reflected_endpoints.add((ex+zx*21, ey+zy*21))
    endpoints = reflected_endpoints

    plan = collections.deque(split_into_number_and_char(plan))

    cx, cy = x, y
    path = [(cx, cy)]
    construct = []
    first_move_complete = False

    while plan:
        if first_move_complete and (cx, cy) in endpoints:
            return path, construct, (cx, cy) == (x, y)
        first_move_complete = True
        word = plan.popleft()
        if type(word) == int:
            if word == 0:
                continue
            cx += dx
            cy += dy
            path.append((cx, cy))
            word -= 1
            if word > 0:
                plan.appendleft(word)
            continue
        if word == "C":
            construct.append((cx, cy))
            continue
        dx, dy = dcode_to_dxdy[word]
        cx += dx
        cy += dy
        path.append((cx, cy))

    is_cyclic = False
    visited = set()
    for _ in range(21):
        if cx == x and cy == y:
            is_cyclic = True
        if construct or (cx, cy) in endpoints or (cx, cy) in visited:
            break
        visited.add((cx, cy))
        cx += dx
        cy += dy
        path.append((cx, cy))

    return path, construct, is_cyclic


def fleetplan_matching(flight_plan, sx=0, sy=0, endpoints=set()):
    # plan class, target_x, target_y, polarity, construct

    # plan class - boomerang, rectangle, acyclic
    # polarity - whether first move vertical or horizontal
    # target_x/y - an opinionated value of the maximum extent
    # whether construct is genuine will not be analyzed here

    if not re.match("^[NSEW][NSEWC0-9]*$", flight_plan):
        return (FlightPlanClass.invalid, 0, 0, False, [])

    polarity = (flight_plan[0] == "N") or (flight_plan[0] == "S")

    path, construct, is_cyclic = extract_flight_plan(
        sx, sy, 0, flight_plan, endpoints=endpoints)

    x_max_extent = 0
    y_max_extent = 0
    target_x, target_y = 0, 0
    for x, y in path:
        if abs(x-sx) > x_max_extent or abs(y-sy) > y_max_extent:
            x_max_extent = abs(x-sx)
            y_max_extent = abs(y-sy)
            target_x, target_y = x, y

    # orbit
    if re.match("^[NSEW]$", flight_plan):
        return (FlightPlanClass.acyclic, target_x, target_y, polarity, construct)

    # sneek peek, yo-yo
    for d1, d2 in zip("NSEW", "SNWE"):
        if re.match(f"^[{d1}][0-9]*[{d2}][0-9]*$", flight_plan):
            return (FlightPlanClass.boomerang, target_x, target_y, polarity, construct)

    # travelling
    for d1, d2 in zip("NSEW", "SNWE"):
        if re.match(f"[NSEW][0-9]*[NSEW][0-9]*$", flight_plan):
            return (FlightPlanClass.acyclic, target_x, target_y, polarity, construct)

    # flat rectangle, rectangle
    if is_cyclic:
        for d1, d2 in zip("NSEW", "SNWE"):
            if re.match(f"^[{d1}][0-9]*[NSEW][0-9]*[{d2}][0-9]*[NSEW][0-9]*$", flight_plan):
                return (FlightPlanClass.rectangle, target_x, target_y, polarity, construct)

    # crowbar, boomerang
    if is_cyclic:
        for d1, d2 in zip("NSEW", "SNWE"):
            if re.match(f"^[NSEW][0-9]*[{d1}][0-9]*[{d2}][0-9]*[NSEW][0-9]*$", flight_plan):
                return (FlightPlanClass.boomerang, target_x, target_y, polarity, construct)

    return (FlightPlanClass.unknown, target_x, target_y, polarity, construct)


class KoreMatch():
    def __init__(self, match_info, home_agent="home", away_agent="away", save_animation=False):
        self.match_info = match_info
        self.home_agent = home_agent
        self.away_agent = away_agent
        self.save_animation = save_animation

        res = match_info
        self.home_actions = [home_info["action"] for home_info, _ in res]
        self.away_actions = [away_info["action"] for _, away_info in res]

        self.home_kore_stored = [info[0]["observation"]
                                 ["players"][0][0] for info in res]
        self.away_kore_stored = [info[0]["observation"]
                                 ["players"][1][0] for info in res]

        self.home_shipyards = [info[0]["observation"]
                               ["players"][0][1] for info in res]
        self.away_shipyards = [info[0]["observation"]
                               ["players"][1][1] for info in res]
        self.all_shipyards_locations = [
            set(kaggle_environments.helpers.Point.from_index(int(loc_idx), 21) for loc_idx, _, _ in home_shipyards.values()) |
            set(kaggle_environments.helpers.Point.from_index(int(loc_idx), 21)
                for loc_idx, _, _ in away_shipyards.values())
            for home_shipyards, away_shipyards in zip(self.home_shipyards, self.away_shipyards)
        ]
        self.home_fleets = [info[0]["observation"]
                            ["players"][0][2] for info in res]
        self.away_fleets = [info[0]["observation"]
                            ["players"][1][2] for info in res]

        self.home_kore_carried = [
            sum(x[1] for x in fleet_info.values()) for fleet_info in self.home_fleets]
        self.away_kore_carried = [
            sum(x[1] for x in fleet_info.values()) for fleet_info in self.away_fleets]

        self.home_ship_standby = [sum(shipyard[1] for shipyard in shipyards.values(
        )) for shipyards in self.home_shipyards]
        self.away_ship_standby = [sum(shipyard[1] for shipyard in shipyards.values(
        )) for shipyards in self.away_shipyards]
        self.home_ship_launched = [
            sum(fleet[2] for fleet in fleets.values()) for fleets in self.home_fleets]
        self.away_ship_launched = [
            sum(fleet[2] for fleet in fleets.values()) for fleets in self.away_fleets]

        self.home_fleetsize_matrices = [
            [0 for _ in info[0]["observation"]["kore"]] for info in res]
        self.away_fleetsize_matrices = [
            [0 for _ in info[0]["observation"]["kore"]] for info in res]

        for turn, (home_fleets_info, away_fleets_info) in enumerate(zip(self.home_fleets, self.away_fleets)):
            for home_fleet_info in home_fleets_info.values():
                location, fleetsize = home_fleet_info[0], home_fleet_info[2]
                self.home_fleetsize_matrices[turn][location] += fleetsize
            for away_fleet_info in away_fleets_info.values():
                location, fleetsize = away_fleet_info[0], away_fleet_info[2]
                self.away_fleetsize_matrices[turn][location] += fleetsize

        self.kore_amount_matrices = [
            info[0]["observation"]["kore"] for info in res]

        self.home_mining_rates = calculate_mining_rates(
            self.kore_amount_matrices, self.home_fleetsize_matrices)
        self.away_mining_rates = calculate_mining_rates(
            self.kore_amount_matrices, self.away_fleetsize_matrices)

        self.home_spawing_costs = [-10 * sum(int(action.split("_")[1]) for action in actions.values()
                                             if action.startswith("SPAWN")) for actions in self.home_actions]
        self.away_spawing_costs = [-10 * sum(int(action.split("_")[1]) for action in actions.values()
                                             if action.startswith("SPAWN")) for actions in self.away_actions]

        self.home_launch_counts = [[int(action.split("_")[1]) for action in actions.values() if action.startswith("LAUNCH")]
                                   for actions in self.home_actions]
        self.away_launch_counts = [[int(action.split("_")[1]) for action in actions.values() if action.startswith("LAUNCH")]
                                   for actions in self.away_actions]
        self.home_launch_plans = [[(action.split("_")[2]) for action in actions.values() if action.startswith("LAUNCH")]
                                  for actions in self.home_actions]
        self.away_launch_plans = [[(action.split("_")[2]) for action in actions.values() if action.startswith("LAUNCH")]
                                  for actions in self.away_actions]

        self.home_combat_diffs = [(a2+b2-a1-b1)-x-y for x, y, a1, b1, a2, b2 in
                                  zip(self.home_mining_rates[1:], self.home_spawing_costs[1:], self.home_kore_carried, self.home_kore_stored,
                                      self.home_kore_carried[1:], self.home_kore_stored[1:])]
        self.away_combat_diffs = [(a2+b2-a1-b1)-x-y for x, y, a1, b1, a2, b2 in
                                  zip(self.away_mining_rates[1:], self.away_spawing_costs[1:], self.away_kore_carried, self.away_kore_stored,
                                      self.away_kore_carried[1:], self.away_kore_stored[1:])]

        self.home_kore_asset_sums = 500*np.array(list(map(len, self.home_shipyards))) \
            + 10*np.array(self.home_ship_standby) + 10*np.array(self.home_ship_launched) \
            + np.array(self.home_kore_stored) + \
            np.array(self.home_kore_carried)
        self.away_kore_asset_sums = 500*np.array(list(map(len, self.away_shipyards))) \
            + 10*np.array(self.away_ship_standby) + 10*np.array(self.away_ship_launched) \
            + np.array(self.away_kore_stored) + \
            np.array(self.away_kore_carried)

    def plot_statistics_kore(self):
        plt.figure(figsize=(15, 5))
        plt.plot(self.home_kore_stored, label=self.home_agent +
                 " (stored)", color="blue", linestyle="dotted")
        plt.plot(self.away_kore_stored, label=self.away_agent +
                 " (stored)", color="red", linestyle="dotted")
        plt.plot(self.home_kore_carried, label=self.home_agent +
                 " (carried)", color="blue")
        plt.plot(self.away_kore_carried, label=self.away_agent +
                 " (carried)", color="red")
        plt.title("Kore carried and stored over time")
        plt.xlim(-20, 400+20)
        plt.legend()
        plt.show()

    def plot_statistics_shipyards(self):
        plt.figure(figsize=(15, 4))
        plt.stairs(list(map(len, self.home_shipyards)),
                   label=self.home_agent, lw=1.5, baseline=None, color="blue")
        plt.stairs(list(map(len, self.away_shipyards)),
                   label=self.away_agent, lw=1.5, baseline=None, color="red")
        plt.title("Number of shipyards over time")
        plt.xlim(-20, 400+20)
        plt.legend()
        plt.show()

    def plot_statistics_ships(self):
        plt.figure(figsize=(15, 5))
        plt.stairs(self.home_ship_standby, label=self.home_agent +
                   " (standby)", baseline=None, color="blue")
        plt.stairs(self.away_ship_standby, label=self.away_agent +
                   " (standby)", baseline=None, color="red")
        plt.stairs(self.home_ship_launched, label=self.home_agent +
                   " (launched)", baseline=None, color="blue", linestyle="dotted")
        plt.stairs(self.away_ship_launched, label=self.away_agent +
                   " (launched)", baseline=None, color="red", linestyle="dotted")
        plt.title("Ships standby and launched over time")
        plt.xlim(-20, 400+20)
        plt.legend()
        plt.show()

    def plot_statistics_kore_rates(self):
        plt.figure(figsize=(15, 5))
        plt.plot(self.home_mining_rates, label=self.home_agent +
                 " (mining)", color="blue")
        plt.plot(self.away_mining_rates, label=self.away_agent +
                 " (mining)", color="red")
        plt.stairs(self.home_spawing_costs, label=self.home_agent +
                   " (spawning)", baseline=None, color="blue")
        plt.stairs(self.away_spawing_costs, label=self.away_agent +
                   " (spawning)", baseline=None, color="red")
        plt.title("Kore change rates over time")
        plt.xlim(-20, 400+20)
        plt.legend()
        plt.show()

    def plot_statistics_combat_diffs(self):
        plt.figure(figsize=(15, 5))
        plt.stairs(self.home_combat_diffs, label=self.home_agent +
                   "(combat)", baseline=None, color="blue")
        plt.stairs(self.away_combat_diffs, label=self.away_agent +
                   "(combat)", baseline=None, color="red")
        plt.title("Kore combat diffs over time")
        plt.xlim(-20, 400+20)
        plt.legend()
        plt.show()

    def plot_statistics_asset_sums(self):
        plt.figure(figsize=(15, 3))
        plt.stairs(self.home_kore_asset_sums, label=self.home_agent,
                   baseline=None, color="blue")
        plt.stairs(self.away_kore_asset_sums, label=self.away_agent,
                   baseline=None, color="red")
        plt.title("Value of assets in terms of Kore over time")
        plt.xlim(-20, 400+20)
        plt.legend()
        plt.show()

    def plot_statistics_launch_sizes(self):
        display_limit = 100
        limits = [1, 2, 3, 5, 8, 13, 21, 34, 55]

        plt.figure(figsize=(15, 6))
        for limit in limits:
            plt.axhline(limit, color="gainsboro", zorder=0)
            plt.axhline(-limit, color="gainsboro", zorder=0)

        home_xpts, home_ypts = [], []
        home_xpts_extra, home_ypts_extra = [], []
        for turn_idx, (launch_counts, launch_plans) in enumerate(zip(self.home_launch_counts, self.home_launch_plans)):
            for launch_count, launch_plan in zip(launch_counts, launch_plans):
                _, _, is_cyclic = extract_flight_plan(0, 0, 0, launch_plan)
                if "C" in launch_plan:
                    home_xpts_extra.append(turn_idx)
                    home_ypts_extra.append(launch_count)
                    continue
                home_xpts.append(turn_idx)
                home_ypts.append(launch_count)
        plt.scatter(home_xpts, home_ypts, color="blue",
                    s=4, label=self.home_agent)
        plt.scatter(home_xpts_extra, home_ypts_extra, color="red", s=7)

        away_xpts, away_ypts = [], []
        away_xpts_extra, away_ypts_extra = [], []
        for turn_idx, (launch_counts, launch_plans) in enumerate(zip(self.away_launch_counts, self.away_launch_plans)):
            for launch_count, launch_plan in zip(launch_counts, launch_plans):
                _, _, is_cyclic = extract_flight_plan(0, 0, 0, launch_plan)
                if "C" in launch_plan:
                    away_xpts_extra.append(turn_idx)
                    away_ypts_extra.append(-launch_count)
                    continue
                away_xpts.append(turn_idx)
                away_ypts.append(-launch_count)
        plt.scatter(away_xpts, away_ypts, color="red",
                    s=4, label=self.away_agent)
        plt.scatter(away_xpts_extra, away_ypts_extra, color="blue", s=7)

        plt.title("Launch sizes over time")
        plt.xlim(-20, 400+20)
        plt.yscale('symlog', linthresh=9)
        plt.yticks([-x for x in limits[2:]] + limits[2:],
                   [-x for x in limits[2:]] + limits[2:])
        plt.legend()
        plt.show()

    def plot_statistics_launch_plan_shapes(self):
        plt.figure(figsize=(15, 3))
        xpts = []
        ypts = []

        for turn_idx, launch_plans in enumerate(kore_match.home_launch_plans):
            for launch_plan in launch_plans:
                plan_class, target_x, target_y, polarity, construct = fleetplan_matching(
                    launch_plan)
                xpts.append(turn_idx)
                ypts.append(int(plan_class) + np.random.randn()/10)

        plt.scatter(xpts, ypts, color="blue", s=4, label=self.home_agent)

        xpts = []
        ypts = []

        for turn_idx, launch_plans in enumerate(kore_match.away_launch_plans):
            for launch_plan in launch_plans:
                plan_class, target_x, target_y, polarity, construct = fleetplan_matching(
                    launch_plan)
                xpts.append(turn_idx)
                ypts.append(int(plan_class) + np.random.randn()/10)

        plt.scatter(xpts, ypts, color="red", s=4, label=self.away_agent)

        plt.title("Distribution of flight plans classes over time")
        plt.xlim(-20, 400+20)
        plt.yticks([e.value for e in FlightPlanClass],
                   [e.name for e in FlightPlanClass])
        plt.legend()
        plt.show()

    def result(self):
        duration = len(self.match_info)
        print('duration '+str(duration))

        if duration < 400:
            if len(self.home_shipyards[duration-1]) > len(self.away_shipyards[duration-1]):
                return('home', duration)
            else:
                return('away', duration)
        if duration == 400:
            if self.home_kore_stored[duration-1] > self.away_kore_stored[duration-1]:
                return('home', duration)
            else:
                return('away', duration)


def gameAnalyzer(env):
    # print([env.steps.status for state in env.steps[-1]])
    # print(env.steps[-1]['observation'])
    print(env.steps[-1][0]['reward'], env.steps[-1][1]['reward'])


pairs = list(combinations(agents['agents'], 2))

for pair in pairs:
    home = pair[0]['name']
    away = pair[1]['name']
    game_name = pair[0]['name']+'-'+pair[1]['name']
    print(game_name)
    pair[0]['source'], pair[1]['source']
    env.run([pair[0]['source'], pair[1]['source']])
    # Render an html ipython replay of the tictactoe game.
    output = env.render(mode="html")
    with open("games/"+game_name+".html", "w") as file:
        file.write(output)
    output = env.render(mode="json")
    with open("games/"+game_name+".json", "w") as file:
        file.write(output)
    kore_match = KoreMatch(env.steps)
    (winner, duration) = kore_match.result()
    winner_name = home if winner == 'home' else away
    looser_name = away if winner == 'home' else home
    print('winner ', winner_name, ' looser ', looser_name)
    # add extra field to logstash message
    extra = {
        'agentName': winner_name,
        'opponent': looser_name,
        'duration': duration,
        'result': 1,
    }

    test_logger.info('game result', extra=extra)
    extra = {
        'agentName': looser_name,
        'opponent': winner_name,
        'duration': duration,
        'result': 0,
    }

    test_logger.info('game result', extra=extra)

    # duration=len(env.steps)
    # print("duration : " + str(duration))
    # print(len(kore_match.home_shipyards[duration-1]))
    # print(len(kore_match.away_shipyards[duration-1]))

    # gameAnalyzer(env)
