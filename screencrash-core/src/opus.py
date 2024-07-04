from __future__ import annotations
import asyncio
from dataclasses import dataclass, field
import hashlib
from typing import Any, Dict, List, Optional, Tuple, Union
from copy import deepcopy
from pathlib import Path
import re
import sys
import aiofiles
import fitz
import yaml
import jsonpath_ng


@dataclass
class Asset:
    """An asset contains a resource"""
    path: str
    data: Optional[bytes]
    checksum: Optional[str]
    targets: List[str]


@dataclass
class ActionTemplate:
    """An Action is a command triggered by a node"""
    id: str
    target: str
    cmd: str
    desc: Optional[str] = None
    assets: List[str] = field(default_factory=list)
    params: Dict[str, Any] = field(default_factory=dict)
    subactions: List[ActionTemplate] = field(default_factory=list)


@dataclass
class NodeChoice:
    """One choice of node when the opus branches"""
    node: str
    description: str
    actions: List[str] = field(default_factory=list)


@dataclass
class Node:
    """A Node is a single location in the script."""
    next: Optional[Union[str, List[NodeChoice]]]
    prompt: str
    pdfPage: int
    pdfLocationOnPage: float
    actions: List[str] = field(default_factory=list)
    lineNumber: Optional[int] = None


@dataclass
class UIShortcut:
    title: str
    actions: List[ActionTemplate]
    hotkey: Optional[str] = None

@dataclass
class UIConfig:
    shortcuts: List[UIShortcut]


@dataclass
class Opus:
    """An Opus has all the information required for a performance."""
    nodes: Dict[str, Node]
    action_templates: Dict[str, ActionTemplate]
    assets: Dict[str, Asset]
    ui_config: UIConfig
    start_node: str
    script: bytes


async def load_opus(opus_path: Path, read_asset_data: bool, exit_on_validation_failure: bool):
    """Load an opus from a file."""
    parent = opus_path.parent
    async with aiofiles.open(opus_path, mode="r", encoding="utf-8") as f:
        opus_string = await f.read()
        opus_dict = yaml.safe_load(opus_string)
        nodes, inlined_actions_dict = await load_nodes(opus_dict["nodes"], parent / opus_dict["assets"]["script"]["path"])
        ui_config, inlined_actions_dict_ui = await load_ui_config(opus_dict.get("ui"))
        action_templates, inlined_assets_dict = load_actions(
            {**opus_dict["action_templates"], **inlined_actions_dict, **inlined_actions_dict_ui})
        assets = dict(await asyncio.gather(
            *[load_asset(key, asset["path"], action_templates, opus_path, read_asset_data)
              for key, asset in [*opus_dict["assets"].items(), *inlined_assets_dict.items()]]
        ))
        if assets.get("script") is None:
            raise RuntimeError(
                "Warning: Asset 'script' not found. This is required.")
        start_node = opus_dict["startNode"]

    async with aiofiles.open(parent / assets["script"].path, mode="rb") as f:
        script = await f.read()

    opus = Opus(nodes, action_templates, assets, ui_config, start_node, script)
    validate_references(opus, exit_on_validation_failure)
    return opus


async def load_asset(key: str, path: str, action_templates: Dict[str, ActionTemplate], opus_path: Path, read_asset_data: bool):
    """
    Load an asset from a file.

    Parameters
    ----------
    key
        The ID of the asset. Used for checking where it is used.
    path
        The path to the file, relative to the opus path
    action_templates
        All action templates in the opus. Used for checking where the asset is used.
    opus_path
        The path to the opus file
    read_asset_data
        Whether to read the asset data from the file

    Returns
    -------
    A list of tuples (key, asset)
    """
    def fill_targets_from_action(action, result):
        if key in action.assets:
            result.add(action.target)
        for subaction in action.subactions:
            fill_targets_from_action(subaction, result)

    targets = set()
    for action in action_templates.values():
        fill_targets_from_action(action, targets)

    data = None
    checksum = None
    if read_asset_data and not path.startswith("http://") and not path.startswith("https://"):
        async with aiofiles.open(opus_path.parent / path, mode="rb") as f:
            data = await f.read()
        checksum = hashlib.md5(data).hexdigest()
    return (key, Asset(path=path, data=data, checksum=checksum, targets=targets))


def is_parametrized_action(action_dict: dict) -> bool:
    """
    Helper function for load_actions, checks if action is a parametrized action,
    based on the action dictionary containing data about it.

    Parameters
    ----------
    action_dict
        Dict for action, as found in the opus

    Returns
    -------
    True if the given action is a parametrized one, False otherwise
    """
    return "actions" in action_dict and "parameters" in action_dict


def get_action_desc(action: ActionTemplate) -> str:
    """
    Helper function for load_actions, retrieves the description
    of an action based on its contents. If a description is not
    explicitly set this method will construct one for it.

    Parameters
    ----------
    action
        Action from opus as parsed ActionTemplate

    Returns
    -------
    The description of the action as a string
    """
    if action.desc:
        return action.desc
    elif "entityId" in action.params:
        return f"{action.target}:{action.cmd} {action.params['entityId']}"
    else:
        return f"{action.target}:{action.cmd}"


def create_action_and_inline_assets(action_dict: Dict[str, dict], key: str, assets: Dict[str, str]) -> ActionTemplate:
    typed_action_dict = deepcopy(action_dict)
    if "assets" in typed_action_dict:
        for i, asset in enumerate(typed_action_dict["assets"]):
            if isinstance(asset, dict):
                asset_id = f"{key}_asset_{i}"
                assets[asset_id] = asset
                typed_action_dict["assets"][i] = asset_id
    return ActionTemplate(id=key, **typed_action_dict)

def load_actions(actions_dict: Dict[str, dict]) -> Tuple[Dict[str, ActionTemplate], Dict[str, dict]]:
    """
    Load actions, and pick out inlined assets.

    Parameters
    ----------
    actions_dict
        Dict of actions, as found in the opus

    Returns
    -------
    Dict of actions, converted to ActionTemplates, and a dict of inlined assets
    """
    parametrized_action_templates = dict(filter(lambda action_tuple: is_parametrized_action(action_tuple[1]), actions_dict.items()))
    param_action_template_indexes = {}

    actions = {}
    assets = {}
    for key, action_data in actions_dict.items():
        if type(action_data) == list:
            # Composite action
            subactions = []
            action_index = param_action_template_indexes.get(key, 1)
            for subaction_dict in action_data:
                if type(subaction_dict) == str:
                    raise RuntimeError("Named actions are not allowed here. Yet.")
                else:
                    subaction_key = f"{key}_{action_index}"
                    subactions.append(create_action_and_inline_assets(subaction_dict, subaction_key, assets))
                action_index += 1
            param_action_template_indexes[key] = action_index

            desc = ", ".join([get_action_desc(action) for action in subactions])
            actions[key] = ActionTemplate(id=key, target="internal", cmd="nop", desc=desc, assets=[], params={}, subactions=subactions)
        elif is_parametrized_action(action_data):
            # These are only virtual until filled with parameters
            continue
        elif "action" in action_data:
            # Parameterized action
            action_dict = action_data
            template = parametrized_action_templates.get(action_dict["action"])
            if not template:
                raise RuntimeError(f"Could not find parametrized action template {action_dict['action']}")
            subactions_list = deepcopy(template.get("actions"))
            for parameter, change_list in template.get("parameters", {}).items():
                parameter_var = f"${parameter}"
                for change_order in change_list:
                    expr = jsonpath_ng.parse(change_order["path"])
                    orig_value = expr.find(subactions_list)
                    if len(orig_value) > 0:
                        if type(orig_value[0].value) == str and parameter_var in orig_value[0].value:
                            new_value = orig_value[0].value.replace(parameter_var, str(action_dict["parameters"][parameter]))
                        else:
                            new_value = action_dict["parameters"][parameter]
                    else:
                        raise RuntimeError(f"Invalid JSON path for parameter: {change_order['path']}")
                    expr.update(subactions_list, new_value)

            subactions = []
            action_index = param_action_template_indexes.get(action_dict["action"], 1)
            for subaction_dict in subactions_list:
                if type(subaction_dict) == str:
                    subaction_name = subaction_dict
                    subactions.append(ActionTemplate(**actions[subaction_name].__dict__))
                else:
                    subaction_key = f"{action_dict['action']}_{action_index}"
                    subactions.append(create_action_and_inline_assets(subaction_dict, subaction_key, assets))
                action_index += 1
            param_action_template_indexes[action_dict["action"]] = action_index

            desc = ", ".join([get_action_desc(action) for action in subactions])
            actions[key] = ActionTemplate(id=key, target="internal", cmd="nop", desc=desc, assets=[], params={}, subactions=subactions)
        else:
            # "Normal" action
            action_dict = action_data
            actions[key] = create_action_and_inline_assets(action_dict, key, assets)
    return actions, assets


async def load_nodes(nodes_dict: Dict[str, dict], script_path: Path) -> Tuple[Dict[str, Node], Dict[str, dict]]:
    """
    Load the nodes, find their locations on the page, and pick out inlined actions.

    If a node does not already have a defined lineNumber, it will be given one.
    Then we assume the node ID begins with the line number, e.g. "12" or "13a".

    If a node does not already have defined pdfPage and pdfLocationOnPage,
    we will try to find it in the PDF based on the line number.

    Parameters
    ----------
    nodes_dict
        The nodes from the opus file
    script_path
        Path to the script PDF

    Returns
    -------
    The nodes and the inlined actions
    """
    # Get line numbers
    for key, node in nodes_dict.items():
        if "lineNumber" not in node:
            try:
                line_number = re.match(r"[0-9]+", key).group(0)
                node["lineNumber"] = int(line_number)
            except AttributeError:
                pass  # lineNumber is not mandatory

    doc = fitz.open(script_path)
    first_page_line_number_end, second_page_line_number_end = find_line_number_ends(doc)
    # Get all node keys where we need to discover the location.
    node_keys = [
        key for key, value in nodes_dict.items()
        if "pdfPage" not in value or "pdfLocationOnPage" not in value
    ]
    if len(node_keys) > 0:
        try:
            with_line_numbers = [(key, nodes_dict[key]["lineNumber"])
                                 for key in node_keys]
        except KeyError:
            raise RuntimeError(
                "Nodes without specified PDF locations must have IDs beginning with numbers, "
                "or defined lineNumber. "
                f"Offenders: {[key for key in node_keys if 'lineNumber' not in nodes_dict[key]]}"
            )
        sorted_keys_and_numbers = sorted(
            with_line_numbers, key=lambda x: int(x[1]))
        next_pair = sorted_keys_and_numbers.pop(0)
        # Searching for e.g. "12" will find both "12" and "112". Since the wanted line numbers
        # are sorted, the first occurrence we find is correct.
        for page in doc:
            while True:
                key, line_number = next_pair
                found = [
                    rect for rect in page.search_for(str(line_number))
                    if (first_page_line_number_end[0] < rect.x1 < first_page_line_number_end[1])
                    or (second_page_line_number_end[0] < rect.x1 < second_page_line_number_end[1])
                ]
                if len(found) == 0:
                    # We won't find anything more on this page, since the wanted line numbers are sorted
                    break
                nodes_dict[key]["pdfPage"] = page.number
                y = (found[0].y0 + found[0].y1) / 2
                nodes_dict[key]["pdfLocationOnPage"] = y / page.rect.y1
                if len(sorted_keys_and_numbers) == 0:
                    next_pair = None
                    break
                next_pair = sorted_keys_and_numbers.pop(0)
            if next_pair is None:
                break

    # Convert nodes from dicts to Node objects, and pick out all inlined actions.
    # We make up action IDs.
    nodes = {}
    actions_dict = {}
    for key, node in nodes_dict.items():
        typed_node = node.copy()
        if isinstance(typed_node.get("next"), list):
            for i, choice in enumerate(typed_node["next"]):
                if "actions" in choice:
                    for j, action in enumerate(choice["actions"]):
                        if isinstance(action, dict):
                            action_id = f"{key}_choice_{i}_action_{j}"
                            actions_dict[action_id] = action
                            choice["actions"][j] = action_id
                typed_node["next"][i] = NodeChoice(**choice)
        if "actions" in typed_node:
            for i, action in enumerate(typed_node["actions"]):
                if isinstance(action, dict):
                    action_id = f"{key}_action_{i}"
                    actions_dict[action_id] = action
                    typed_node["actions"][i] = action_id

        nodes[key] = Node(**typed_node)

    return nodes, actions_dict

def find_line_number_ends(doc: fitz.Document) -> Tuple[Tuple[float, float], Tuple[float, float]]:
    # Find the x coordinates where the line numbers end by finding enough
    # numbers on the pages. Skip one-digit numbers since they appear in
    # larger numbers too often. We select the most common end coordinates,
    # so there can be some anomalies.
    line_numbers_to_find = list(range(10, 100))
    all_found_number_rects = []
    line_number = line_numbers_to_find.pop(0)
    for page in doc:
        while True:
            found_instances = page.search_for(str(line_number))
            all_found_number_rects.extend(found_instances)
            if len(found_instances) > 0 and len(line_numbers_to_find) > 0:
                line_number = line_numbers_to_find.pop(0)
            else:
                break
        if len(line_numbers_to_find) == 0:
            break
    end_coords = [rect.x1 for rect in all_found_number_rects]
    most_common = max(set(end_coords), key=end_coords.count)
    all_except_most_common = [x for x in end_coords if x != most_common]
    second_most_common = max(set(all_except_most_common), key=all_except_most_common.count)

    # Return ranges for the end-coordinates of numbers on odd and even pages.
    # The order does not matter.
    return (
        (most_common - 0.5, most_common + 0.5),
        (second_most_common - 0.5, second_most_common + 0.5)
    )

def get_shortcut_key(hotkey: dict) -> str:
    if hotkey:
        if hotkey.get("modifiers"):
            hotkey_key = hotkey["key"]
            if "shift" in hotkey["modifiers"]:
                hotkey_key = hotkey_key.upper()
            return '+'.join(sorted(hotkey["modifiers"])) + '+' + hotkey_key
        else:
            return hotkey["key"]
    return None

async def load_ui_config(ui_config: Optional[Dict[str, Any]]) -> Tuple[UIConfig, Dict[str, dict]]:
    if ui_config is None:
        return UIConfig([])

    shortcuts = []
    actions_dict = {}
    for i, shortcut_dict in enumerate(ui_config.get("shortcuts", [])):
        title = shortcut_dict["title"]
        hotkey = get_shortcut_key(shortcut_dict.get("hotkey"))
        actions = []
        for j, action in enumerate(shortcut_dict["actions"]):
            if isinstance(action, str):
                actions.append(action)
            elif isinstance(action, dict):
                action_id = f"ui_shortcut_{i}_action_{j}"
                actions_dict[action_id] = action
                actions.append(action_id)
            else:
                raise RuntimeError("Illegal action type in ui config shortcuts")
        shortcuts.append(UIShortcut(title, actions, hotkey))

    return (UIConfig(shortcuts), actions_dict)


def validate_references(opus: Opus, exit_on_failure: bool):
    """
    Validate that we only refer to existing nodes, assets and actions.

    Exits the program if validation fails.

    Parameters
    ----------
    opus
        The opus
    exit_on_failure
        Whether to exit the program if validation fails
    """
    # Nodes
    referred_nodes = set([opus.start_node])
    for node in opus.nodes.values():
        if isinstance(node.next, str):
            referred_nodes.add(node.next)
        elif isinstance(node.next, list):
            for choice in node.next:
                referred_nodes.add(choice.node)
    actual_nodes = set(opus.nodes.keys())
    if referred_nodes != actual_nodes:
        nonexistent_nodes = referred_nodes - actual_nodes
        unreferred_nodes = actual_nodes - referred_nodes
        print("Malformed opus!")
        if nonexistent_nodes:
            print("References to nonexistent nodes:")
            print('\n'.join(nonexistent_nodes))
        if unreferred_nodes:
            print("Nodes never referred to:")
            print('\n'.join(unreferred_nodes))
        if exit_on_failure:
            print("Aborting!")
            sys.exit(1)

    # Assets
    referred_assets = set(["script"])
    for action in opus.action_templates.values():
        referred_assets.update(set(action.assets))
    actual_assets = set(opus.assets.keys())
    if referred_assets != actual_assets:
        nonexistent_assets = referred_assets - actual_assets
        unreferred_assets = actual_assets - referred_assets
        print("Malformed opus!")
        if nonexistent_assets:
            print("References to nonexistent assets:")
            print('\n'.join(nonexistent_assets))
        if unreferred_assets:
            print("Assets never referred to:")
            print('\n'.join(unreferred_assets))
        if exit_on_failure:
            print("Aborting!")
            sys.exit(1)

    # Actions
    referred_actions = set()
    def update_referred_action(action: ActionTemplate):
        if action:
            referred_actions.add(action.id)
            for subaction in action.subactions:
                if subaction.id in opus.action_templates:
                    # Don't add autogenerated subactions
                    update_referred_action(subaction)

    for node in opus.nodes.values():
        if node.actions is not None:
            for action_name in node.actions:
                action = opus.action_templates.get(action_name)
                if action:
                    update_referred_action(action)
                else:
                    referred_actions.add(action_name) # add even if not exists
        if isinstance(node.next, list):
            for choice in node.next:
                if choice.actions is not None:
                    referred_actions.update(set(choice.actions))
    for shortcut in opus.ui_config.shortcuts:
        referred_actions.update(set(shortcut.actions))
    actual_actions = set(opus.action_templates.keys())
    if referred_actions != actual_actions:
        nonexistent_actions = referred_actions - actual_actions
        unreferred_actions = actual_actions - referred_actions
        print("Malformed opus!")
        if nonexistent_actions:
            print("References to nonexistent actions:")
            print('\n'.join(nonexistent_actions))
        if unreferred_actions:
            print("Actions never referred to:")
            print('\n'.join(unreferred_actions))
        if exit_on_failure:
            print("Aborting!")
            sys.exit(1)

    # UI shortcuts
    DISALLOWED_HOTKEYS = [
        "ctrl+t", "ctrl+n", "ctrl+w", "ctrl+r",                         # Browser specific
        "a", "s", " ", "Up", "ArrowUp", "Down", "ArrowDown", "Enter"    # UI specific
    ]
    used_disallowed_hotkeys = []
    for shortcut in opus.ui_config.shortcuts:
        if shortcut.hotkey in DISALLOWED_HOTKEYS:
            used_disallowed_hotkeys.append(f"  {shortcut.title} ({shortcut.hotkey})")
    if used_disallowed_hotkeys:
        print("Malformed opus!")
        print("Illegal hotkeys used:")
        print("\n".join(used_disallowed_hotkeys))
        if exit_on_failure:
            print("Aborting!")
            sys.exit(1)
