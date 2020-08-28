import json
from pathlib import Path
from tdw.tdw_utils import TDWUtils
from tdw.librarian import ModelLibrarian
from tdw.controller import Controller


"""
Convert initialization commands into a Sticky Mitten Avatar API scene recipe.

The commands must be a list located at: ~/tdw_config/init_commands.json

Output: a list of `commands.extend(self.get_add_object` calls.
"""


if __name__ == "__main__":
    lib = ModelLibrarian()
    path = Path.home().joinpath("tdw_config/init_commands.json")

    # Spaces used to format the output string.
    spaces = "                                    "

    output = ""
    # Load the commands.
    assert path.exists(), f"Not found: {path}"
    raw_txt = '{"commands":' + path.read_text(encoding="utf-8") + '}'
    commands = json.loads(raw_txt)["commands"]

    for i in range(len(commands)):
        cmd = commands[i]
        if cmd["$type"] == "add_object":
            name = cmd["name"]
            output += f'commands.extend(self.get_add_object("{name}",\n{spaces}'
            output += f"position={json.dumps(cmd['position'])},\n{spaces}"
            # The next command is a rotation command.
            # Convert the rotation to Euler angles.
            rotation = TDWUtils.vector4_to_array(commands[i + 1]["rotation"])
            rotation = TDWUtils.quaternion_to_euler_angles(rotation)
            rotation = TDWUtils.array_to_vector3(rotation)
            output += f"rotation={json.dumps(rotation)},\n{spaces}"
            output += f"scale={json.dumps(commands[i + 2]['scale_factor'])},\n{spaces}"
            output += "object_id=self.get_uniqueID()))\n"
    print(output)
