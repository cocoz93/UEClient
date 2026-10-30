using UnrealBuildTool;

public class LearnTopDown : ModuleRules
{
	public LearnTopDown(ReadOnlyTargetRules Target) : base(Target)
	{
		PCHUsage = PCHUsageMode.UseExplicitOrSharedPCHs;
		PublicDependencyModuleNames.AddRange(new string[] {
			"Core", "CoreUObject", "Engine", "InputCore", "AIModule", "NavigationSystem", "UMG"
		});
		PrivateDependencyModuleNames.AddRange(new string[] { "ChaosCloth", "ClothingSystemRuntimeInterface", "ClothingSystemRuntimeCommon", "SlateCore" });
		if (Target.bBuildEditor)
		{
			PrivateDependencyModuleNames.AddRange(new string[] {
				"Slate", "AnimGraph", "BlueprintGraph", "UnrealEd", "Json"
			});
		}
	}
}
