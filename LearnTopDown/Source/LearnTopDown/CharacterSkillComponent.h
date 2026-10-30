#pragma once

#include "CoreMinimal.h"
#include "Components/ActorComponent.h"
#include "CharacterSkillComponent.generated.h"

UENUM(BlueprintType)
enum class ECharacterSkillTargeting : uint8
{
	Self,
	Direction,
	Actor,
	Ground
};

// 입력과 HUD가 공유하는 계약이다. 고유 스킬의 판정과 표현은 파생 컴포넌트가 소유한다.
UCLASS(ClassGroup = (Combat), meta = (BlueprintSpawnableComponent))
class LEARNTOPDOWN_API UCharacterSkillComponent : public UActorComponent
{
	GENERATED_BODY()

public:
	UCharacterSkillComponent();
	UFUNCTION(BlueprintCallable, Category = "Skills")
	virtual bool TryUseSkillSlot(int32 Slot, const FVector& AimLocation, AActor* Target) { return false; }
	UFUNCTION(BlueprintPure, Category = "Skills")
	virtual bool IsCasting() const { return false; }
	UFUNCTION(BlueprintPure, Category = "Skills")
	virtual bool IsEnabled() const { return false; }
	UFUNCTION(BlueprintPure, Category = "Skills")
	virtual int32 GetActiveSkillNumber() const { return 0; }
	UFUNCTION(BlueprintPure, Category = "Skills")
	virtual int32 GetSkillCount() const { return 0; }
	virtual FText GetSkillDisplayName(int32 Slot) const { return FText::GetEmpty(); }
	virtual bool IsSkillPassive(int32 Slot) const { return false; }
	virtual FText GetSkillStatusText(int32 Slot) const { return FText::GetEmpty(); }
	virtual ECharacterSkillTargeting GetSkillTargeting(int32 Slot) const { return ECharacterSkillTargeting::Direction; }
	virtual bool IsSkillTargetValid(int32 Slot, const AActor* Target, const AActor* Caster) const;
	virtual float GetSlotCooldownRemaining(int32 Slot) const { return 0.0f; }
	virtual float GetSlotRecastRemaining(int32 Slot) const { return 0.0f; }
	UFUNCTION(BlueprintPure, Category = "Skills")
	virtual FString GetInputFeedback() const { return FString(); }
	virtual bool IgnoresCooldowns() const { return false; }
	virtual void CancelSkill() {}
	// true면 HUD 왼쪽 묶음 아랫줄에 A S D F(칸 8~11), 오른쪽 묶음 윗줄에 1 2 3 4(칸 4~7)를 그려 QWER+ASDF 스킬을 왼쪽에 모은다.
	virtual bool PlacesLetterKeysOnLeftHud() const { return false; }
};
