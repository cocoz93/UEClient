#include "CharacterSkillComponent.h"

#include "GameFramework/Pawn.h"

UCharacterSkillComponent::UCharacterSkillComponent()
{
	PrimaryComponentTick.bCanEverTick = false;
}

bool UCharacterSkillComponent::IsSkillTargetValid(int32 Slot, const AActor* Target, const AActor* Caster) const
{
	return IsValid(Target) && Target != Caster && Target->CanBeDamaged() && Target->IsA<APawn>();
}
