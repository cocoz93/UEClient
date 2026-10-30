"""Build only the tower minion's locomotion/slot AnimBlueprint in the editor.

The original minion skeleton, BlendSpace and sequences are referenced, never
saved or edited. Monster Blueprint binding belongs to the caller.
"""
from __future__ import annotations

import json
from pathlib import Path

import unreal

DEST = '/Game/TopDown/TrialTower/Combat'
ASSET = DEST + '/ABP_TrialTowerMinion'
PACK = '/Game/ParagonMinions/Characters/Minions/Down_Minions/'
MESH = PACK + 'Meshes/Minion_Lane_Melee_Dawn'
BLENDSPACE = PACK + 'Animations/Melee/Blendspaces/IdleToRun_A_Combat'
PARENT = '/Script/LearnTopDown.TrialTowerAnimInstance'
B = unreal.BlueprintEditorLibrary


def require(value, message):
    if not value:
        raise RuntimeError(message)
    return value


def pin(node, name, output=False):
    result = node.find_output_pin(name) if output else node.find_input_pin(name)
    if not result.is_valid():
        names = [str(item.get_pin_name()) for item in node.list_all_pins()]
        raise RuntimeError(f'Missing {name} on {node.get_name()}: {names}')
    return result


def connect(source, target):
    require(source.try_create_connection(target),
            f'Could not connect {source.get_pin_name()} to {target.get_pin_name()}')


def compile_blueprint(bp):
    if not B.compile_blueprint(bp):
        errors = []
        for graph in B.list_graphs(bp):
            editor = unreal.BlueprintGraphEditor.get_graph_editor(graph)
            errors.extend(str(node.get_editor_property('ErrorMsg'))
                          for node in editor.list_nodes_with_errors())
        raise RuntimeError('Minion animation Blueprint failed to compile: ' + repr(errors))


def action_for(actions, kind):
    # The action database uses localized menu names. Restrict by the asset name
    # and actual node kind, then validate the created class before editing it.
    if kind == 'blendspace':
        matches = [value for value in actions if "'IdleToRun_A_Combat'" in value and
                   ('player' in value.lower() or '플레이어' in value)]
    else:
        matches = [value for value in actions if value.split('|')[-1] == "Slot'DefaultSlot'"]
    require(matches, f'Missing animation graph action: {kind}')
    return matches[0]


def build(output=None):
    assets = unreal.EditorAssetLibrary
    parent = require(unreal.load_class(None, PARENT), 'Build TrialTowerAnimInstance before authoring the AnimBlueprint')
    mesh = require(unreal.load_asset(MESH), 'Minion mesh unavailable')
    blendspace = require(unreal.load_asset(BLENDSPACE), 'Minion locomotion BlendSpace unavailable')
    skeleton = mesh.get_editor_property('skeleton')
    require(blendspace.get_editor_property('skeleton') == skeleton, 'Locomotion skeleton mismatch')
    assets.make_directory(DEST)
    bp = unreal.load_asset(ASSET) if assets.does_asset_exist(ASSET) else None
    if not bp:
        factory = unreal.AnimBlueprintFactory()
        factory.set_editor_property('parent_class', parent)
        factory.set_editor_property('target_skeleton', skeleton)
        factory.set_editor_property('preview_skeletal_mesh', mesh)
        bp = require(unreal.AssetToolsHelpers.get_asset_tools().create_asset(
            'ABP_TrialTowerMinion', DEST, unreal.AnimBlueprint, factory), 'Could not create minion AnimBlueprint')
    require(isinstance(bp, unreal.AnimBlueprint), 'Owned animation asset has unexpected type')
    bp.modify()
    B.reparent_blueprint(bp, parent)
    compile_blueprint(bp)
    editor = require(unreal.BlueprintGraphEditor.get_graph_editor_by_name(bp, 'AnimGraph'), 'AnimGraph missing')
    nodes = editor.list_all_nodes()
    roots = [node for node in nodes if node.get_class().get_name() == 'AnimGraphNode_Root']
    require(len(roots) == 1, 'Expected one output pose node')
    root = roots[0]
    editor.remove_nodes([node for node in nodes if node != root])
    actions = [str(value) for value in editor.list_available_nodes([])]
    player = require(editor.create_node_from_name(action_for(actions, 'blendspace'),
        unreal.Vector2D(-580, 0), []), 'Could not create locomotion player')
    require(player.get_class().get_name() == 'AnimGraphNode_BlendSpacePlayer', 'Unexpected locomotion node type')
    # Melee and ranged packs contain identically named assets. Explicitly bind
    # the verified melee asset rather than relying on action database order.
    player_data = player.get_editor_property('node')
    player_data.set_editor_property('blend_space', blendspace)
    player_data.set_editor_property('loop', True)
    player.set_editor_property('node', player_data)
    require(player.get_editor_property('node').get_editor_property('blend_space') == blendspace,
            'Locomotion player did not retain the melee BlendSpace')
    require(pin(player, 'X').set_pin_value('0.0'), 'Could not set forward locomotion direction')
    speed = require(editor.add_get_member_variable_node('Speed'), 'Native Speed property unavailable')
    speed.set_node_pos(unreal.IntPoint(-830, 100))
    connect(speed.find_result_pin(), pin(player, 'Y'))
    slot = require(editor.create_node_from_name(action_for(actions, 'slot'),
        unreal.Vector2D(-260, 0), []), 'Could not create full-body montage slot')
    require(slot.get_class().get_name() == 'AnimGraphNode_Slot', 'Unexpected montage node type')
    slot_data = slot.get_editor_property('node')
    slot_data.set_editor_property('slot_name', 'DefaultSlot')
    slot_data.set_editor_property('always_update_source_pose', True)
    slot.set_editor_property('node', slot_data)
    root.set_node_pos(unreal.IntPoint(0, 0))
    connect(pin(player, 'Pose', True), pin(slot, 'Source'))
    connect(pin(slot, 'Pose', True), pin(root, 'Result'))
    unreal.SystemLibrary.execute_console_command(None, 'TrialTowerAnimationQA.InstallHitLayer')
    hit_nodes = editor.list_all_nodes()
    require(any(node.get_name().startswith('TowerHitUpperBody') for node in hit_nodes) and
            all(any(node.get_name().startswith('TowerGet' + variable) and
                    len(node.find_result_pin().list_connected_pins()) == 1 for node in hit_nodes)
                for variable in ('HitReactionSequence', 'HitReactionTime', 'HitReactionWeight')),
            'Build the native tower hit-layer authoring command before saving the animation graph')
    compile_blueprint(bp)
    require(assets.save_loaded_asset(bp, False), 'Could not save tower-owned minion AnimBlueprint')
    generated = require(assets.load_blueprint_class(ASSET), 'Compiled minion animation class unavailable')
    report = {
        'passed': True, 'asset': ASSET, 'parent': PARENT,
        'generated_class': generated.get_path_name(), 'blendspace': BLENDSPACE,
        'graph': 'Speed -> BlendSpace Y; DefaultSlot -> cached combat pose -> spine_01 additive hit layer -> OutputPose',
        'hit_layer': 'Directional additive sequence, explicit time and smooth weight from native AnimInstance; lower body preserved',
        'direction_x': 0.0, 'speed_y': 'Native Speed maps 0..MaxWalkSpeed to 0..420',
        'always_update_locomotion': True, 'source_assets_saved': False,
        'monster_defaults_modified': False,
    }
    if output:
        folder = Path(output)
        folder.mkdir(parents=True, exist_ok=True)
        (folder/'combat-animation-build.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
    return report
