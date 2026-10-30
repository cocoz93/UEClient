#if WITH_EDITOR && WITH_DEV_AUTOMATION_TESTS

#include "CharacterPipelineQA.h"
#include "../CharacterSkillComponent.h"
#include "../CountessSkillComponent.h"
#include "../KwangCharacter.h"
#include "../TopDownCombatCharacter.h"
#include "Dom/JsonObject.h"
#include "Misc/FileHelper.h"
#include "Serialization/JsonSerializer.h"

static TAutoConsoleVariable<FString> CVarCharacterPipelineOutput(
	TEXT("CharacterPipeline.OutputDirectory"), TEXT(""),
	TEXT("Editor QA output directory. Empty preserves historical QA locations."));

static FAutoConsoleCommand VerifyCharacterPipelineContract(
	TEXT("CharacterPipelineQA.Contract"), TEXT("Verify reusable skill and character contracts"),
	FConsoleCommandDelegate::CreateLambda([]()
	{
		const ATopDownCombatCharacter* Generic = GetDefault<ATopDownCombatCharacter>();
		const AKwangCharacter* Countess = GetDefault<AKwangCharacter>();
		UCharacterSkillComponent* GenericSkills = Generic->GetSkills();
		UCharacterSkillComponent* Skills = Countess->GetSkills();
		TSharedRef<FJsonObject> Json = MakeShared<FJsonObject>();
		const bool bGeneric = GenericSkills && GenericSkills->GetClass() == UCharacterSkillComponent::StaticClass() &&
			GenericSkills->GetSkillCount() == 0 && !GenericSkills->IsEnabled() && !GenericSkills->IsCasting() &&
			!GenericSkills->TryUseSkillSlot(0, FVector::ZeroVector, nullptr);
		const bool bCompatibility = Skills && Skills == Countess->GetCountessSkills() &&
			Skills->GetClass() == UCountessSkillComponent::StaticClass() && Skills->GetSkillCount() == 4 &&
			Skills->GetFName() == TEXT("CountessSkills");
		const bool bTargeting = Skills && Skills->GetSkillTargeting(0) == ECharacterSkillTargeting::Actor &&
			Skills->GetSkillTargeting(1) == ECharacterSkillTargeting::Self &&
			Skills->GetSkillTargeting(2) == ECharacterSkillTargeting::Direction &&
			Skills->GetSkillTargeting(3) == ECharacterSkillTargeting::Actor;
		const bool bInvalidSlots = Skills && !Skills->TryUseSkillSlot(-1, FVector::ZeroVector, nullptr) &&
			!Skills->TryUseSkillSlot(4, FVector::ZeroVector, nullptr);
		Json->SetBoolField(TEXT("generic_character_has_no_countess_component"), bGeneric);
		Json->SetBoolField(TEXT("legacy_character_and_subobject_compatible"), bCompatibility);
		Json->SetBoolField(TEXT("polymorphic_target_modes_match"), bTargeting);
		Json->SetBoolField(TEXT("invalid_slots_rejected"), bInvalidSlots);
		Json->SetBoolField(TEXT("passed"), bGeneric && bCompatibility && bTargeting && bInvalidSlots);
		FString Text;
		FJsonSerializer::Serialize(Json, TJsonWriterFactory<>::Create(&Text));
		FFileHelper::SaveStringToFile(Text, *(CharacterPipelineQA::GetOutputDirectory(TEXT("QA/CharacterPipeline")) / TEXT("contract.json")),
			FFileHelper::EEncodingOptions::ForceUTF8WithoutBOM);
	}));

#endif
