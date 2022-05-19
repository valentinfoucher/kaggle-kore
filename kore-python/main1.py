from kaggle_environments import make
env = make("kore_fleets")
import json
from itertools import combinations
# The list of available default agents.
f= open('agents.json')
agents=json.load(f)
f.close()

pairs = list(combinations(agents['agents'],2))

for pair in pairs:
    game_name=pair[0]['name']+'-'+pair[1]['name']
    print(game_name)
    pair[0]['source'],pair[1]['source']
    env.run([pair[0]['source'], pair[1]['source']])
    # Render an html ipython replay of the tictactoe game.
    output=env.render(mode="html")
    with open("games/"+game_name+".html", "w") as file:
        file.write(output)

