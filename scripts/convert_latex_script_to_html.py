# type: ignore

import sys
import re
from pathlib import Path
from argparse import Namespace, ArgumentParser

import TexSoup as TS
TS.data.TexText.__hash__ = lambda self: hash(str(self))

###############################################################################
# Global variables

DATA = Namespace(
    html = True,
    darkmode = False,
    act = 0,
    scene = 0,
    row = 0,
    roles = {},
    colors = {},
)

DATA.roles['all'] = '* * *'
DATA.roles['scenanv'] = ''


###############################################################################
# CSS stylesheet

STYLESHEET = '''
body { font-family: Palatino, "PT Serif", serif }
.manus { display: grid; grid-template-columns: auto auto auto; grid-gap: 10px }
.radnr { text-align: right }
.regi, .händelse, .kursiv, .värde { font-style: italic }
.sjunger, .Musik { font-variant: small-caps }
.Musik { font-size: 130% }
.händelse::before { content: "[" } .händelse::after { content: "]" }
.markera::before { content: "[" } .markera::after { content: "]" }
.citat::before { content: "«" } .citat::after { content: "»" }
'''


###############################################################################
# LaTeX commands

IGNORE_NODES = set('''
    kommentar TODO
    vspace vspace* title author date maketitle thispagestyle newpage
    tableofcontents makeatletter makeatother setlength
'''.split())

MODIFIERS = {
    'emph': 'kursiv',
    'textit': 'kursiv',
    'gr': 'händelse',
    'gör': 'händelse',
    'rekv': 'rekvisita',
    'rekvisita': 'rekvisita',
    'citat': 'citat',
    'markera': 'markera',
    'rentext': 'rentext',
}

ROLE_INVISIBLE = {
    '=in*': '',
    '=ut*': '',
    '=sub': '',
    '=subslut': '',
    'aktivera=': '',
    'deaktivera=': '',
}

ROLE_CLASSES = {
    '=sj': 'sjunger',
    '=gr': 'regi',
    '=in': 'regi',
    '=ut': 'regi',
}

ROLE_TEXTS = {
    '=in': lambda p: f'{p} kommer in på scen.',
    '=ut': lambda p: f'{p} går av scen.',
}


###############################################################################
# Color names

DEFINED_COLORS = {
    'apricot': '#fbb982', 'aquamarine': '#00b5be', 'bittersweet': '#c04f17', 'black': '#221e1f',
    'blue': '#2d2f92', 'bluegreen': '#00b3b8', 'blueviolet': '#473992', 'brickred': '#b6321c',
    'brown': '#792500', 'burntorange': '#f7921d', 'cadetblue': '#74729a', 'carnationpink': '#f282b4',
    'cerulean': '#00a2e3', 'cornflowerblue': '#41b0e4', 'cyan': '#00aeef', 'dandelion': '#fdbc42',
    'darkorchid': '#a4538a', 'emerald': '#00a99d', 'forestgreen': '#009b55', 'fuchsia': '#8c368c',
    'goldenrod': '#ffdf42', 'gray': '#949698', 'green': '#00a64f', 'greenyellow': '#dfe674',
    'junglegreen': '#00a99a', 'lavender': '#f49ec4', 'limegreen': '#8dc73e', 'magenta': '#ec008c',
    'mahogany': '#a9341f', 'maroon': '#af3235', 'melon': '#f89e7b', 'midnightblue': '#006795',
    'mulberry': '#a93c93', 'navyblue': '#006eb8', 'olivegreen': '#3c8031', 'orange': '#f58137',
    'orangered': '#ed135a', 'orchid': '#af72b0', 'peach': '#f7965a', 'periwinkle': '#7977b8',
    'pinegreen': '#008b72', 'plum': '#92268f', 'processblue': '#00b0f0', 'purple': '#99479b',
    'rawsienna': '#974006', 'red': '#ed1b23', 'redorange': '#f26035', 'redviolet': '#a1246b',
    'rhodamine': '#ef559f', 'royalblue': '#0071bc', 'royalpurple': '#613f99', 'rubinered': '#ed017d',
    'salmon': '#f69289', 'seagreen': '#3fbc9d', 'sepia': '#671800', 'skyblue': '#46c5dd',
    'springgreen': '#c6dc67', 'tan': '#da9d76', 'tealblue': '#00aeb3', 'thistle': '#d883b7',
    'turquoise': '#00b4ce', 'violet': '#58429b', 'violetred': '#ef58a0', 'white': '#ffffff',
    'wildstrawberry': '#ee2967', 'yellow': '#fff200', 'yellowgreen': '#98cc70', 'yelloworange': '#faa21a',
}


###############################################################################
# Functions for printing to HTML or Text

def print_stylesheet():
    print(STYLESHEET)
    if DATA.darkmode: print('body { background-color: black; color: white }')
    for role, color in DATA.colors.items():
        color = DEFINED_COLORS.get(color, color)
        if DATA.darkmode: color = f'color-mix(in srgb, white, {color})'
        print(f'.{role} {{ color: {color} }}')


def print_header():
    if DATA.html:
        print('<!DOCTYPE html>')
        print('<html><head><style>')
        print_stylesheet()
        print('</style></head>')
        print('<body>')
        print('<div class="manus">')


def print_footer():
    if DATA.html:
        print('</div>')
        print('</body>')
        print('</html>')


def get_text(node):
    if isinstance(node, (str, int, float)):
        text = str(node)
    else:
        text = ''
        parts = list(node.contents)
        while parts:
            part = parts.pop(0)
            if isinstance(part, (str, int, float)):
                text += str(part)
            elif part.name == 'BraceGroup':
                parts[0:0] = part.contents
            elif len(part.args) > 0:
                spanclass = MODIFIERS.get(part.name)
                text += html('span', get_text(part.args[-1]), cls=spanclass)
    return text.strip()


def html(entity, *texts, **xargs):
    text = ' '.join(get_text(text) for text in texts)
    # 'class' is a Python keyword, so we use 'cls' instead
    classes = xargs.get('cls', '')
    if classes:
        xargs['class'] = classes
        del xargs['cls']
    if DATA.html:
        args = ''.join(f' {key}="{value}"' for key, value in xargs.items())
        return f'<{entity}{args}>{text}</{entity}>'
    else:
        return text


def print_hdr(hdr, *texts, **xargs):
    print(html('div') + html('div') + html(hdr, *texts, **xargs))


def print_row(role, person, textclass, text):
    if DATA.html:
        print(
            html('div', DATA.row, id=f'rad-{DATA.row}', cls='radnr'),
            html('div', person, cls=f'roll {role}'),
            html('div', text, cls=f'innehåll {textclass} {role}'),
        )
    else:
        print(f'{DATA.row:5d}  {person:15s}  {get_text(text)}')


def print_env(**env):
    if DATA.html:
        print(
            html('div', DATA.row, cls='radnr'),
            html('div', cls='roll'),
            html('div', '<br>'.join(
                html('span', html('span', key, cls='nyckel') + ': ' + html('span', value, cls='värde'), cls=key)
                for key, value in env.items() if value
            ), cls='innehåll'),
        )
    else:
        print(f'{DATA.row:5d}', ' '*17, ('\n'+' '*24).join(
            get_text(key) + ': ' + get_text(value)
            for key, value in env.items() if value
        ))


###############################################################################
# Handle toplevel commands

def handle_command(node):
    if node.name in IGNORE_NODES:
        return

    if node.name == 'setcounter':
        if node.args[0].string == 'manus@radnummer':
            DATA.row = int(node.args[1].string)
        return

    if node.name == 'namnbyte':
        role, newname = list(node.args)
        DATA.roles[role.string] = newname.string
        return

    if node.name == 'akt':
        DATA.act += 1
        print_hdr('h1', f'Akt {DATA.act}', id=f'akt-{DATA.act}', cls='akt')
        DATA.scene = int(node.args[0].string)-1 if node.args else 0
        return

    if node.name == 'scen':
        DATA.scene += 1
        id = f'scen-{DATA.act}-{DATA.scene}'
        print_hdr('h2', f'Scen {DATA.scene}:', node.args[0], id=id, cls='scen')
        return

    if node.name == 'musik':
        DATA.row += 1
        print_env(
            Musik = node.titel,
            Deltagare = node.deltagare,
            Beskrivning = node.beskrivning,
            Melodi = node.melodi,
        )
        return

    for role in DATA.roles:
        if role in node.name:
            template = node.name.replace(role, '=')
            if template in ROLE_INVISIBLE:
                # TODO: Add vertical bars showing which characters are on stage
                pass
            else:
                person = DATA.roles.get(role, role)
                textclass = ROLE_CLASSES.get(template, '')
                text = (
                    ROLE_TEXTS[template](person) if template in ROLE_TEXTS
                    else node if len(node.args) == 1 else ''
                )
                DATA.row += 1
                print_row(role, person, textclass, text)
            return

    print('? Skipping unknown node:', str(node).replace('\n', ' '), file=sys.stderr)


###############################################################################
# Reading LaTeX files into a string

def read_latex(*files) -> str:
    latex = ''
    for file in files:
        file = Path(file)
        with open(file) as f:
            latex = f.read()
            latex = re.sub('%.*\n?', '', latex)  # Remove line comments
            latex = re.sub(  # Read additional latex files
                r'\\input{([\w/.]+)}',
                lambda m: read_latex(file.parent / Path(m[1]).with_suffix('.tex')),
                latex,
            )
            if not latex.endswith('\n'):
                latex += '\n'  # Add newline to end of file
    # More cleaning:
    latex = latex.replace(r'\-', '').replace('---', '—').replace('--', '–')
    return latex


###############################################################################
# Main function for converting a script into HMTL/text

def convert_script(args):
    DATA.html = not args.text
    DATA.darkmode = args.dark
    script = TS.TexSoup(read_latex(args.file))

    for node in script.find_all('definecolor'):
        color, model, code = [a.string for a in node.args]
        if model.lower() != 'html':
            print('! Unknown color model:', model, file=sys.stderr)
            continue
        if color in DEFINED_COLORS:
            print('! Color already defined:', color, file=sys.stderr)
            continue
        DEFINED_COLORS[color] = '#' + code

    for node in script.find_all(['nyroll', 'nyhjalproll']):
        role, name, color = make_role(node)
        DATA.roles[role] = name
        if color: DATA.colors[role] = color.lower()

    print_header()
    for node in script.document.children:
        handle_command(node)
    print_footer()


def make_role(node):
    assert 1 <= len(node.args) <= 3, node
    role = name = color = None
    for arg in node.args:
        if arg.name == 'BracketGroup' and not role:
            color = arg.string
        elif arg.name == 'BraceGroup':
            role = arg.string
            name = role
        else:
            name = arg.string
    return role, name, color


###############################################################################
# Calling from the command line

parser = ArgumentParser(description = 'Convert a LaTeX script/manus into HTML or text')
parser.add_argument('--text', action='store_true', help='Output plain text (default: HTML)')
parser.add_argument('--dark', action='store_true', help='Output dark background (default: light)')
parser.add_argument('file', type=Path, help='LaTeX file')

if __name__ == '__main__':
    args = parser.parse_args()
    convert_script(args)

