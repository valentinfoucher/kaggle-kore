from kaggle_environments import make
env = make("kore_fleets")

# The list of available default agents.
agents=["random" "miner" "do_nothing" "balanced" "attacker"]



print(env.run(["balanced", "miner"]))
# Render an html ipython replay of the tictactoe game.
# output=env.render(mode="html")
# with open("output.html", "w") as file:
#     file.write(output)

