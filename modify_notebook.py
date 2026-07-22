import json

with open('/home/pmc/worldmaker/traveller_world_generator.ipynb', 'r') as f:
    notebook = json.load(f)

# 1. Add name attribute to PlanetaryBody
for cell in notebook['cells']:
    if cell['cell_type'] == 'code':
        source = cell['source']
        for i, line in enumerate(source):
            if 'class PlanetaryBody:' in line:
                if 'name: str' not in source[i+1]:
                    source.insert(i + 1, '    name: str = ""
')
                break
        cell['source'] = source
        break

# 2. Add generate_world_name function
for cell in notebook['cells']:
    if cell['cell_type'] == 'code' and 'def _interpolate_stellar_data' in ''.join(cell['source']):
        source = cell['source']
        if 'def generate_world_name():' not in ''.join(source):
            generate_world_name_func = [
                'def generate_world_name():\n',
                '    prefixes = ["Ard", "Bor", "Cor", "Den", "Eth", "Fen", "Gor", "Hen", "Ish", "Jen", "Kel", "Lor", "Mor", "Nor", "Orr", "Per", "Quor", "Ren", "Sor", "Tor", "Ur", "Ver", "Wor", "Xen", "Yor", "Zor"]
',
                '    suffixes = ["ia", "os", "a", "us", "is", "en", "or", "an", "el", "ar"]
',
                '    return random.choice(prefixes) + random.choice(suffixes)
',
                '\n'
            ]
            cell['source'] = generate_world_name_func + source
        break

# 3. Call generate_world_name
for cell in notebook['cells']:
    if cell['cell_type'] == 'code' and 'def place_worlds' in ''.join(cell['source']):
        source = cell['source']
        if 'name=generate_world_name(),' not in ''.join(source):
            for i, line in enumerate(source):
                if 'body = PlanetaryBody(' in line:
                    source.insert(i + 1, '            name=generate_world_name(),\n')
                    break
        cell['source'] = source
        break

# 4. Modify the last cell to print the name
last_cell = notebook['cells'][-1]
new_source = [
    "from IPython.display import SVG, display\n",
    "subsectors = []\n",
    "for i in range(16):\n",
    "    subsectors.append(generate_sector())\n",
    "    \n",
    "svg_data = generate_sector_svg(subsectors)\n",
    "with open(\"sector_map.svg\", \"w\") as f:\n",
    "    f.write(svg_data)\n",
    "print(\"Full sector map generated as sector_map.svg\")\n",
    "\n",
    "display(SVG(svg_data))\n",
    "\n",
    "for i, subsector in enumerate(subsectors):\n",
    "    print(f'--- Subsector {i+1} ---')\n",
    "    for hex_coord, system in subsector.systems.items():\n",
    "        print(f'-- System: {hex_coord} --')\n",
    "        for world in system.all_worlds:\n",
    "            print(f'Name: {world.name}, Designation: {world.designation}, Type: {world.body_type}, UWP: {world.uwp}')\n"
]
last_cell['source'] = new_source


with open('/home/pmc/worldmaker/traveller_world_generator.ipynb', 'w') as f:
    json.dump(notebook, f, indent=1)