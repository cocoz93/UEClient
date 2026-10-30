"""Gate PIE copying on usable EditorWorld navigation, without saving assets."""
import unreal


def projected_point(world, point):
    result = unreal.NavigationSystemV1.project_point_to_navigation(world,
        unreal.Vector(x=point[0], y=point[1], z=point[2]),
        nav_data=None, filter_class=None, query_extent=unreal.Vector(x=100, y=100, z=250))
    if isinstance(result, unreal.Vector):
        return result
    if isinstance(result, tuple):
        if any(isinstance(item, bool) and not item for item in result):
            return None
        return next((item for item in result if isinstance(item, unreal.Vector)), None)
    return None


def editor_navigation_ready():
    world = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world()
    if not world:
        return False
    # The current field starts on the raised cylinder and uses the north ramp for movement.
    start = projected_point(world, (0, 0, 212))
    goal = projected_point(world, (0, 650, 125))
    if start is None or goal is None:
        return False
    path = unreal.NavigationSystemV1.find_path_to_location_synchronously(world, start, goal)
    return path is not None and path.is_valid() and not path.is_partial()
