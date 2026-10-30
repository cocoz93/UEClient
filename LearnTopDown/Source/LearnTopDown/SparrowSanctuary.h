#pragma once

#include "CoreMinimal.h"
#include "GameFramework/Actor.h"
#include "SparrowSanctuary.generated.h"

class ACharacter;
class AKwangTrainingDummy;
class UCharacterMovementComponent;
class UMaterialInstanceDynamic;
class UParticleSystem;
class UParticleSystemComponent;
class UStaticMeshComponent;

// S와 F는 V의 내부 slot9 시전 상태와 분리된다. 각 효과가 표적/투사체와 복구 수명을 소유한다.
UCLASS()
class LEARNTOPDOWN_API ASparrowSanctuary : public AActor
{
	GENERATED_BODY()
public:
	ASparrowSanctuary();
	bool Initialize(ACharacter* Character, int32 Slot, const FVector& Aim, AActor* Target);
	bool IsCasting() const;
	int32 GetSlot() const { return SkillSlot; }
	UFUNCTION(BlueprintPure, Category = "Skills")
	float GetRemainingSeconds() const;
	UFUNCTION(BlueprintPure, Category = "Skills")
	bool HasCommitted() const { return bCommitted; }
	UFUNCTION(BlueprintPure, Category = "Skills")
	int32 GetBlockedProjectileCount() const { return BlockedProjectiles; }
	UFUNCTION(BlueprintPure, Category = "Skills")
	int32 GetCounterShotCount() const { return CounterShots; }
	UFUNCTION(BlueprintPure, Category = "Skills")
	AActor* GetBoundTarget() const { return BoundTarget.Get(); }
	static ASparrowSanctuary* FindInterception(AActor* Projectile, const FVector& Start, const FVector& End,
		float& Fraction, FVector& Contact);
	bool TryIntercept(AActor* Projectile, const FVector& Contact);
	virtual void Tick(float DeltaSeconds) override;
protected:
	virtual void BeginPlay() override;
	virtual void EndPlay(const EEndPlayReason::Type EndPlayReason) override;
private:
	void ApplyBinding();
	void ReleaseBinding();
	bool CanInterceptProjectile(const AActor* Projectile) const;
	void UpdateBindingVisual(float Age);
	void UpdateBarrierVisual(float Age);
	UStaticMeshComponent* CreatePlane(const TCHAR* Material, bool bLine);
	void PlaceRing(int32 Index, const FVector& Position, const FVector& Normal, float Spin,
		const FVector& Scale, float Strength);
	void PlaceLine(int32 Index, const FVector& Start, const FVector& End, float Width, float Strength);
	void Pulse(const FVector& Position, const FVector& Direction, float Scale, bool bRelease = false);
	UPROPERTY(Transient)
	TArray<TObjectPtr<UStaticMeshComponent>> RingMeshes;
	UPROPERTY(Transient)
	TArray<TObjectPtr<UMaterialInstanceDynamic>> RingMaterials;
	UPROPERTY(Transient)
	TArray<TObjectPtr<UStaticMeshComponent>> LineMeshes;
	UPROPERTY(Transient)
	TArray<TObjectPtr<UMaterialInstanceDynamic>> LineMaterials;
	struct FPulse
	{
		TWeakObjectPtr<UParticleSystemComponent> Particle;
		float Until = 0.0f;
	};
	TArray<FPulse> Pulses;
	TWeakObjectPtr<ACharacter> Caster;
	TWeakObjectPtr<AActor> BoundTarget;
	TWeakObjectPtr<UCharacterMovementComponent> BoundMovement;
	TWeakObjectPtr<AKwangTrainingDummy> StatusDummy;
	FVector CastDirection = FVector::ForwardVector;
	FVector CastOrigin = FVector::ZeroVector;
	FVector BarrierCenter = FVector::ZeroVector;
	double StartedAt = 0.0;
	float LastPulseAt = -10.0f;
	float CounterPulseUntil = 0.0f;
	int32 SkillSlot = INDEX_NONE;
	int32 BlockedProjectiles = 0;
	int32 CounterShots = 0;
	bool bCommitted = false;
	bool bBindingLease = false;
	bool bDummyStatusOwned = false;
	bool bReleased = false;
};

