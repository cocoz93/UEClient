using UnrealBuildTool;

public class LearnTopDownTarget : TargetRules
{
	public LearnTopDownTarget(TargetInfo Target) : base(Target)
	{
		Type = TargetType.Game;
		DefaultBuildSettings = BuildSettingsVersion.V7;
		IncludeOrderVersion = EngineIncludeOrderVersion.Unreal5_8;
		ExtraModuleNames.Add("LearnTopDown");
	}
}
