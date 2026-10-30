#include "KwangCharacter.h"
#include "CharacterClothPresentation.h"

#include "CountessSkillComponent.h"

AKwangCharacter::AKwangCharacter(const FObjectInitializer& ObjectInitializer)
	: Super(ObjectInitializer.SetDefaultSubobjectClass<UCountessSkillComponent>(SkillComponentName))
{
}

UCountessSkillComponent* AKwangCharacter::GetCountessSkills() const
{
	return Cast<UCountessSkillComponent>(GetSkills());
}

void AKwangCharacter::BeginPlay()
{
	Super::BeginPlay();
	ConfigureTopDownCloth(GetMesh(), false);
}
