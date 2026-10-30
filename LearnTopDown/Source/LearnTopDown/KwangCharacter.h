#pragma once

#include "CoreMinimal.h"
#include "TopDownCombatCharacter.h"
#include "KwangCharacter.generated.h"

class UCountessSkillComponent;

// 기존 캐릭터와 블루프린트 참조를 보존하는 카운테스 호환 클래스다.
UCLASS()
class LEARNTOPDOWN_API AKwangCharacter : public ATopDownCombatCharacter
{
	GENERATED_BODY()

public:
	AKwangCharacter(const FObjectInitializer& ObjectInitializer = FObjectInitializer::Get());
	UFUNCTION(BlueprintPure, Category = "Skills")
	UCountessSkillComponent* GetCountessSkills() const;
protected:
	virtual void BeginPlay() override;
};
