#pragma once

#include "CoreMinimal.h"
#include "CharacterSkillHUD.h"
#include "CountessSkillHUD.generated.h"

UCLASS()
class LEARNTOPDOWN_API ACountessSkillHUD : public ACharacterSkillHUD
{
	GENERATED_BODY()

public:
	virtual void DrawHUD() override;
};
