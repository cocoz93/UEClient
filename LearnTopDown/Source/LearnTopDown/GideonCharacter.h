#pragma once

#include "CoreMinimal.h"
#include "TopDownCombatCharacter.h"
#include "GideonCharacter.generated.h"

class UCameraComponent;
class UGideonSkillComponent;
class USpringArmComponent;

// 마법사 몸(기본 스킨). 평타는 원본 3타 몽타주로 손 투사체를 쏘고, 스킬 다섯은 UGideonSkillComponent가 소유한다.
UCLASS()
class LEARNTOPDOWN_API AGideonCharacter : public ATopDownCombatCharacter
{
	GENERATED_BODY()

public:
	AGideonCharacter(const FObjectInitializer& ObjectInitializer = FObjectInitializer::Get());
	UFUNCTION(BlueprintPure, Category = "Skills")
	UGideonSkillComponent* GetGideonSkills() const;
	// 원본 애니 BP는 조준 방향과 몸 방향의 차이로 고개를 돌린다. 쿼터뷰의 조준 방향은 카메라라서 몸 정면을 돌려준다.
	virtual FRotator GetBaseAimRotation() const override;

protected:
	// 평타 3타 재생 속도(1 = 원본). 10-19 「공속을 좀 낮춰」로 원본보다 느리게.
	static constexpr float BasicAttackPlayRate = 0.8f;

	virtual void BeginPlay() override;
	virtual void ExecuteBasicAttackHit() override;

	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "Camera")
	TObjectPtr<USpringArmComponent> CameraBoom;
	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "Camera")
	TObjectPtr<UCameraComponent> TopDownCamera;
};
