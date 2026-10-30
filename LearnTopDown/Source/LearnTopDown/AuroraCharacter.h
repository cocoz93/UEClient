#pragma once

#include "CoreMinimal.h"
#include "TopDownCombatCharacter.h"
#include "AuroraCharacter.generated.h"

class UAuroraSkillComponent;
class UCameraComponent;
class USpringArmComponent;

// 얼음 검사 몸(기본 스킨). 평타는 원본 3타 몽타주의 근접 베기, 스킬 넷은 UAuroraSkillComponent가 소유한다.
UCLASS()
class LEARNTOPDOWN_API AAuroraCharacter : public ATopDownCombatCharacter
{
	GENERATED_BODY()

public:
	AAuroraCharacter(const FObjectInitializer& ObjectInitializer = FObjectInitializer::Get());
	UFUNCTION(BlueprintPure, Category = "Skills")
	UAuroraSkillComponent* GetAuroraSkills() const;
	// 원본 애니 BP는 조준 방향과 몸 방향의 차이로 고개를 돌린다. 쿼터뷰의 조준 방향은 카메라라서 몸 정면을 돌려준다.
	virtual FRotator GetBaseAimRotation() const override;
	// 서리 가속(S) 장판 안: 평타 재생 속도·이동 속도 배율(1 = 기본).
	void SetSpeedScale(float AttackScale, float MoveScale);
	// 얼음 갑옷(A)이 켜져 있으면 받는 피해를 줄인다. 들어온 값과 줄인 값을 AURORA_TAKE 로그로 남긴다.
	virtual float TakeDamage(float DamageAmount, const FDamageEvent& DamageEvent, AController* EventInstigator, AActor* DamageCauser) override;

	static constexpr float BaseAttackPlayRate = 1.35f;
	static constexpr float BaseWalkSpeed = 600.0f;

protected:
	virtual void BeginPlay() override;
	virtual void ExecuteBasicAttackHit() override;

	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "Camera")
	TObjectPtr<USpringArmComponent> CameraBoom;
	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "Camera")
	TObjectPtr<UCameraComponent> TopDownCamera;
};
