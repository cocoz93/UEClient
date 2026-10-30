#pragma once

#include "CoreMinimal.h"
#include "GameFramework/HUD.h"
#include "CharacterSkillHUD.generated.h"

UCLASS()
class LEARNTOPDOWN_API ACharacterSkillHUD : public AHUD
{
	GENERATED_BODY()

public:
	virtual void DrawHUD() override;
};
