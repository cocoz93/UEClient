"""Author the small map selector using UE 5.8 Blueprint and UMG APIs only.

Run inside the editor. This module owns only /Game/TopDown/TrialTower/UI.
Installing the new controller on a shared GameMode is a separate explicit call.
"""
from __future__ import annotations

import json
from pathlib import Path

import unreal

ROOT = "/Game/TopDown/TrialTower/UI"
WIDGET = ROOT + "/WBP_MapSelector"
CONTROLLER = ROOT + "/BP_MapTravelController"
TRAINING_MAP = "/Game/TopDown/TrainingRoom/Maps/Lvl_DarkTrainingRoom"
TOWER_MAP = "/Game/TopDown/TrialTower/Maps/Lvl_TrialTower"
B = unreal.BlueprintEditorLibrary


def require(value, message):
    if not value:
        raise RuntimeError(message)
    return value


def node_call(editor, path):
    return require(editor.add_call_function_node(path), "Missing function " + path)


def pin(node, name, output=False):
    result = node.find_output_pin(name) if output else node.find_input_pin(name)
    if not result.is_valid():
        available = [str(p.get_pin_name()) for p in node.list_all_pins()]
        raise RuntimeError(f"Missing {name} on {node.get_name()}; pins={available}")
    return result


def wire(source, dest):
    require(source.try_create_connection(dest),
            f"Cannot connect {source.get_pin_name()} to {dest.get_pin_name()}")


def value(node, name, literal):
    require(pin(node, name).set_pin_value(str(literal)), f"Invalid {name}={literal}")


def execute(source, target):
    wire(source.find_then_pin(), target.find_execute_pin())


def member(editor, name):
    return require(editor.add_get_member_variable_node(name), "Missing member " + name)


def event_graph(bp):
    return require(unreal.BlueprintGraphEditor.get_graph_editor_by_name(bp, "EventGraph"),
                   "Missing EventGraph")


def compile_bp(bp):
    if not B.compile_blueprint(bp):
        errors = []
        for graph in B.list_graphs(bp):
            editor = unreal.BlueprintGraphEditor.get_graph_editor(graph)
            errors.extend(str(n.get_editor_property("ErrorMsg")) for n in editor.list_nodes_with_errors())
        raise RuntimeError(f"Compile failed: {bp.get_path_name()} {errors}")


def load_or_create_widget():
    if unreal.EditorAssetLibrary.does_asset_exist(WIDGET):
        existing = unreal.load_asset(WIDGET)
        existing_tree = unreal.find_object(existing, "WidgetTree")
        if existing_tree and find_root_canvas(existing_tree):
            return existing
        raise RuntimeError("Existing selector has no root CanvasPanel; inspect rather than deleting it")
    factory = unreal.WidgetBlueprintFactory()
    factory.set_editor_property("parent_class", unreal.UserWidget)
    settings_class = unreal.load_class(None, "/Script/UMGEditor.UMGEditorProjectSettings")
    settings = unreal.get_default_object(require(settings_class, "UMG project settings class unavailable"))
    old_root = settings.get_editor_property("DefaultRootWidget")
    old_selector = settings.get_editor_property("bUseWidgetTemplateSelector")
    try:
        settings.set_editor_property("DefaultRootWidget", unreal.CanvasPanel)
        settings.set_editor_property("bUseWidgetTemplateSelector", False)
        return require(unreal.AssetToolsHelpers.get_asset_tools().create_asset(
            "WBP_MapSelector", ROOT, unreal.WidgetBlueprint, factory), "Widget creation failed")
    finally:
        # Do not persist editor preferences: the factory only needs these during creation.
        settings.set_editor_property("DefaultRootWidget", old_root)
        settings.set_editor_property("bUseWidgetTemplateSelector", old_selector)


def clear_graphs(bp):
    for graph in B.list_graphs(bp):
        editor = unreal.BlueprintGraphEditor.get_graph_editor(graph)
        editor.remove_nodes(editor.list_all_nodes())


def find_root_canvas(tree):
    # RootWidget has neither Edit nor BlueprintVisible flags, so Python denies
    # even reads. The factory-created root is the sole canvas directly in this tree.
    roots = [obj for obj in unreal.ObjectIterator(unreal.CanvasPanel)
             if obj.get_outer() == tree]
    require(len(roots) <= 1, "Unexpected extra CanvasPanel in selector tree")
    return roots[0] if roots else None


def make_widget_tree(bp):
    # WidgetTree/RootWidget are reflected but not script-name mapped properties.
    tree = unreal.find_object(bp, "WidgetTree")
    require(tree, "WidgetTree is unavailable")
    # The factory constructs the root; RootWidget is a protected reflected property.
    def create(cls, name, variable=False):
        old = unreal.find_object(tree, name)
        if old:
            return old
        obj = unreal.new_object(cls, outer=tree, name=name)
        # Native UButton defaults bIsVariable=true; panels/text default false.
        # Compilation below verifies all four button getters are available.
        return obj

    root = require(find_root_canvas(tree), "Factory did not construct the root panel")
    require(isinstance(root, unreal.CanvasPanel), "Selector requires a CanvasPanel root")
    root.clear_children()
    root.set_visibility(unreal.SlateVisibility.SELF_HIT_TEST_INVISIBLE)

    def canvas(child, x, y, width, height):
        slot = root.add_child_to_canvas(child)
        slot.set_anchors(unreal.Anchors(unreal.Vector2D(1, 0), unreal.Vector2D(1, 0)))
        slot.set_alignment(unreal.Vector2D(1, 0))
        slot.set_position(unreal.Vector2D(x, y))
        slot.set_size(unreal.Vector2D(width, height))
        return slot

    def text(name, label, size=16):
        t = create(unreal.TextBlock, name)
        t.set_text(label)
        font = t.get_editor_property("font")
        font.set_editor_property("size", size)
        t.set_font(font)
        t.set_color_and_opacity(unreal.SlateColor(specified_color=unreal.LinearColor(.92, .87, .73, 1)))
        t.set_editor_property("justification", unreal.TextJustify.CENTER)
        return t

    def button(name, label):
        b = create(unreal.Button, name, True)
        b.clear_children()
        b.set_editor_property("is_focusable", False)
        b.set_background_color(unreal.LinearColor(.16, .13, .095, .98))
        child = b.add_child(text(name + "Label", label))
        child.set_padding(unreal.Margin(12, 7, 12, 7))
        child.set_horizontal_alignment(unreal.HorizontalAlignment.H_ALIGN_CENTER)
        child.set_vertical_alignment(unreal.VerticalAlignment.V_ALIGN_CENTER)
        return b

    toggle = button("ToggleTravel", "맵 이동")
    canvas(toggle, -24, 24, 128, 38)

    panel = create(unreal.Border, "TravelPanel")
    panel.clear_children()
    panel.set_brush_color(unreal.LinearColor(.035, .03, .025, .97))
    panel.set_padding(unreal.Margin(8, 8, 8, 8))
    panel.set_visibility(unreal.SlateVisibility.COLLAPSED)
    canvas(panel, -24, 68, 176, 154)
    column = create(unreal.VerticalBox, "TravelChoices")
    column.clear_children()
    panel.set_content(column)
    for name, label in (("GoTraining", "수련장"), ("GoTower", "시험의 탑"), ("CloseTravel", "닫기")):
        b = button(name, label)
        slot = column.add_child_to_vertical_box(b)
        slot.set_padding(unreal.Margin(0, 2, 0, 2))
        slot.set_horizontal_alignment(unreal.HorizontalAlignment.H_ALIGN_FILL)
        slot.set_vertical_alignment(unreal.VerticalAlignment.V_ALIGN_FILL)
    return tree


def set_visibility(editor, target, visibility):
    n = node_call(editor, "/Script/UMG.Widget.SetVisibility")
    wire(widget_target(editor, target), n.find_self_pin())
    value(n, "InVisibility", visibility)
    return n


def widget_target(editor, name):
    if name != "TravelPanel":
        return member(editor, name).find_result_pin()
    # Border is not exposed as a member by default. Traverse the fixed authored
    # hierarchy instead of changing the protected bIsVariable editor flag.
    button = member(editor, "GoTraining")
    column = node_call(editor, "/Script/UMG.Widget.GetParent")
    wire(button.find_result_pin(), column.find_self_pin())
    panel = node_call(editor, "/Script/UMG.Widget.GetParent")
    wire(column.find_result_pin(), panel.find_self_pin())
    return panel.find_result_pin()


def bind_clicked(editor, widget_name, handler, previous):
    get_button = member(editor, widget_name)
    context = [get_button.find_result_pin()]
    actions = editor.list_available_nodes(context)
    matches = [str(a) for a in actions if "bindeventtoonclicked" in str(a).replace(" ", "").lower()]
    require(matches, "OnClicked bind action unavailable: " + repr([str(a) for a in actions if "click" in str(a).lower()]))
    n = require(editor.create_node_from_name(matches[0], unreal.Vector2D(0, 0), context, unreal.Button),
                "OnClicked bind creation failed")
    delegate_out = [p for p in handler.list_output_pins() if "delegate" in str(p.get_pin_name()).lower()]
    delegate_in = [p for p in n.list_input_pins() if "delegate" in str(p.get_pin_name()).lower()]
    require(len(delegate_out) == 1 and len(delegate_in) == 1,
            "Delegate pins: " + repr([str(p.get_pin_name()) for p in n.list_all_pins()]))
    wire(delegate_out[0], delegate_in[0])
    execute(previous, n)
    return n


def build_widget_logic(bp):
    clear_graphs(bp)
    compile_bp(bp)  # Generate the named-widget variables before creating getter nodes.
    editor = event_graph(bp)
    initialized = B.add_event_override(bp, "OnInitialized", unreal.IntPoint(0, 0))
    require(initialized, "OnInitialized event is unavailable")

    toggle = editor.add_custom_event_node("ToggleMapTravel")
    visible = node_call(editor, "/Script/UMG.Widget.IsVisible")
    wire(widget_target(editor, "TravelPanel"), visible.find_self_pin())
    branch = editor.add_branch_node()
    execute(toggle, branch)
    wire(visible.find_result_pin(), branch.find_condition_pin())
    hide = set_visibility(editor, "TravelPanel", "Collapsed")
    show = set_visibility(editor, "TravelPanel", "Visible")
    wire(branch.find_then_pin(), hide.find_execute_pin())
    wire(branch.find_else_pin(), show.find_execute_pin())

    close = editor.add_custom_event_node("CloseMapTravel")
    execute(close, set_visibility(editor, "TravelPanel", "Collapsed"))

    handlers = [("ToggleTravel", toggle), ("CloseTravel", close)]
    for name, destination in (("GoTraining", TRAINING_MAP), ("GoTower", TOWER_MAP)):
        handler = editor.add_custom_event_node("TravelTo" + name[2:])
        travel = node_call(editor, "/Script/Engine.GameplayStatics.OpenLevel")
        value(travel, "LevelName", destination)
        value(travel, "bAbsolute", "true")
        execute(handler, travel)
        handlers.append((name, handler))

    last = initialized
    for name, handler in handlers:
        last = bind_clicked(editor, name, handler, last)

    # Prevent an accidental reload of the currently active map.
    current = node_call(editor, "/Script/Engine.GameplayStatics.GetCurrentLevelName")
    value(current, "bRemovePrefixString", "true")
    execute(last, current)
    last = current
    for name, short_name in (("GoTraining", "Lvl_DarkTrainingRoom"), ("GoTower", "Lvl_TrialTower")):
        different = node_call(editor, "/Script/Engine.KismetStringLibrary.NotEqual_StrStr")
        wire(current.find_result_pin(), pin(different, "A"))
        value(different, "B", short_name)
        enable = node_call(editor, "/Script/UMG.Widget.SetIsEnabled")
        wire(member(editor, name).find_result_pin(), enable.find_self_pin())
        wire(different.find_result_pin(), pin(enable, "bInIsEnabled"))
        execute(last, enable)
        last = enable

    for i, n in enumerate(editor.list_all_nodes()):
        n.set_node_pos(unreal.IntPoint((i % 6) * 290, (i // 6) * 190))
    compile_bp(bp)
    cdo = unreal.get_default_object(bp.generated_class())
    cdo.set_editor_property("visibility", unreal.SlateVisibility.SELF_HIT_TEST_INVISIBLE)
    cdo.set_editor_property("is_focusable", False)
    require(unreal.EditorAssetLibrary.save_loaded_asset(bp, False), "Widget save failed")


def build_controller(widget_bp):
    if unreal.EditorAssetLibrary.does_asset_exist(CONTROLLER):
        bp = unreal.load_asset(CONTROLLER)
    else:
        bp = B.create_blueprint_asset_with_parent(CONTROLLER,
                unreal.load_class(None, "/Script/LearnTopDown.KwangPlayerController"))
    require(bp, "Controller BP creation failed")
    clear_graphs(bp)
    compile_bp(bp)
    editor = event_graph(bp)
    begin = B.add_event_override(bp, "ReceiveBeginPlay", unreal.IntPoint(0, 0))
    require(begin, "Controller BeginPlay event missing")
    create = node_call(editor, "/Script/UMG.WidgetBlueprintLibrary.Create")
    value(create, "WidgetType", widget_bp.generated_class().get_path_name())
    pc = node_call(editor, "/Script/Engine.GameplayStatics.GetPlayerController")
    value(pc, "PlayerIndex", 0)
    wire(pc.find_result_pin(), pin(create, "OwningPlayer"))
    execute(begin, create)
    add = node_call(editor, "/Script/UMG.UserWidget.AddToViewport")
    value(add, "ZOrder", 30)
    wire(create.find_result_pin(), add.find_self_pin())
    execute(create, add)
    for i, n in enumerate(editor.list_all_nodes()):
        n.set_node_pos(unreal.IntPoint(i * 280, 0))
    compile_bp(bp)
    require(unreal.EditorAssetLibrary.save_loaded_asset(bp, False), "Controller save failed")
    return bp


def build(output=None):
    unreal.EditorAssetLibrary.make_directory(ROOT)
    bp = load_or_create_widget()
    make_widget_tree(bp)
    build_widget_logic(bp)
    controller = build_controller(bp)
    result = {"widget": bp.get_path_name(), "controller": controller.get_path_name(),
              "maps": [TRAINING_MAP, TOWER_MAP], "shared_game_mode_modified": False}
    if output:
        out = Path(output)
        out.mkdir(parents=True, exist_ok=True)
        (out / "ui-build.json").write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    unreal.log("TRIAL_TOWER_UI " + json.dumps(result, ensure_ascii=False))
    return result


def install_on_game_mode(game_mode_path):
    """Parent calls after backing up the one explicitly authorized shared GameMode."""
    require(game_mode_path == "/Game/TopDown/Blueprints/BP_CountessGameMode",
            "Only the explicitly authorized shared Countess GameMode may be changed")
    controller = unreal.EditorAssetLibrary.load_blueprint_class(CONTROLLER)
    require(controller, "Build the controller before installing it")
    bp = unreal.load_asset(game_mode_path)
    cdo = unreal.get_default_object(bp.generated_class())
    before = cdo.get_editor_property("player_controller_class")
    require(before.get_path_name() in ("/Script/LearnTopDown.KwangPlayerController", controller.get_path_name()),
            "Unexpected existing controller; inspect before replacing: " + before.get_path_name())
    cdo.set_editor_property("player_controller_class", controller)
    compile_bp(bp)
    require(unreal.EditorAssetLibrary.save_loaded_asset(bp, False), "GameMode save failed")
    return {"game_mode": game_mode_path, "before": before.get_path_name(), "after": controller.get_path_name()}


if __name__ == "__main__":
    build()
