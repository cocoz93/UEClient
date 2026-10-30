#pragma once

#include "CoreMinimal.h"
#include "GameFramework/Actor.h"
#include "SparrowGatherShot.generated.h"

class ATopDownCombatCharacter;
class ASparrowHarmonyFX;
class ASparrowArrow;
class UStaticMeshComponent;
class UMaterialInstanceDynamic;

// D/F의 준비와 방출만 그린다. 피해와 벽 충돌은 원래 화살이 소유한다.
UCLASS()
class LEARNTOPDOWN_API ASparrowGatherShot : public AActor
{
	GENERATED_BODY()
public:
	ASparrowGatherShot();
	bool Initialize(ATopDownCombatCharacter* Character, const FVector& Aim, bool bCrystal, float ChargeSeconds);
	bool InitializeDesignImpact(ATopDownCombatCharacter* Character, int32 Style, const FVector& Point, const FVector& ShotDirection);
	void PrepareArrowPresentation(ASparrowArrow* Arrow) const;
	void Release(ASparrowArrow* Arrow);
	void ReleaseVolley(const TArray<ASparrowArrow*>& Arrows);
	bool HasReleased() const { return ReleasedAt >= 0.0f; }
	virtual void Tick(float DeltaTime) override;
private:
	TWeakObjectPtr<ASparrowHarmonyFX> HarmonyFX;
	bool InitializeDesignSurfaces();
	void TickDesign(float Progress, float Since);
	void TickDesignImpact();
	UPROPERTY(Transient) TArray<TObjectPtr<UStaticMeshComponent>> Surfaces;
	UPROPERTY(Transient) TArray<TObjectPtr<UMaterialInstanceDynamic>> Materials;
	TWeakObjectPtr<ATopDownCombatCharacter> Caster;
	TArray<TWeakObjectPtr<ASparrowArrow>> ReleasedArrows;
	TArray<FVector> ReleaseOrigins;
	FVector Direction = FVector::ForwardVector;
	FVector Origin = FVector::ZeroVector;
	float Age = 0.0f;
	float ReleasedAt = -1.0f;
	float Charge = .52f;
	bool bCrystals = false;
	bool bAscended = false;
	int32 FDesignStyle = 0;
	bool bDesignImpact = false;
};
