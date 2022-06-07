from kaggle_environments.envs.kore_fleets.helpers import *
from kaggle_environments import make

env = make("kore_fleets", debug=True)
starter_agent_path = "starter.py"
env.run([starter_agent_path, starter_agent_path,
        starter_agent_path, starter_agent_path])
output = env.render(mode="html")
with open("tmp.html", "w") as file:
    file.write(output)
output = env.render(mode="json")
