using UnrealBuildTool;

public class LearnTopDownEditorTarget : TargetRules
{
	public LearnTopDownEditorTarget(TargetInfo Target) : base(Target)
	{
		Type = TargetType.Editor;
		DefaultBuildSettings = BuildSettingsVersion.V7;
		IncludeOrderVersion = EngineIncludeOrderVersion.Unreal5_8;
		ExtraModuleNames.Add("LearnTopDown");
	}
}
