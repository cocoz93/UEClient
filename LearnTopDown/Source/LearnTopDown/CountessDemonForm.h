#pragma once

#include "CoreMinimal.h"
#include "GameFramework/Actor.h"
#include "CountessDemonForm.generated.h"

class ATopDownCombatCharacter;
class UMaterialInterface;
class UMaterialInstanceDynamic;
class UParticleSystem;
class UParticleSystemComponent;
class USkeletalMeshComponent;
class UStaticMeshComponent;

// 지속 외형만 소유한다. S의 시전 잠금/피해 배율과 본체 이동/애니메이션은 호출자가 관리한다.
UCLASS()
class LEARNTOPDOWN_API ACountessDemonForm : public AActor
{
	GENERATED_BODY()
public:
	ACountessDemonForm();
	// Duration에는 첫 0.5초의 변신 진입을 포함한다.
	bool Initialize(ATopDownCombatCharacter* Source, float Duration = 24.0f);
	void StopForm();
	UFUNCTION(BlueprintPure, Category = "Skills")
	float GetFormRemaining() const;
	UFUNCTION(BlueprintPure, Category = "Skills")
	float GetVisualAge() const;
	virtual void Tick(float DeltaSeconds) override;
protected:
	virtual void EndPlay(const EEndPlayReason::Type EndPlayReason) override;
private:
	UParticleSystemComponent* SpawnFormEffect(UParticleSystem* Template, FName Socket,
		const FVector& Offset, float Scale, float Lifetime, bool bTrail = false);
	void SpawnEntryPhase(int32 Phase);
	void UpdateMantle(float Age, bool bVisible);
	void UpdateEntryShroud(float Age, bool bVisible);
	void RestoreSource();
	FName FindBodySocket() const;
	struct FEffectLease
	{
		TWeakObjectPtr<UParticleSystemComponent> Particle;
		float Until = 0.0f;
		bool bTrail = false;
	};
	TArray<FEffectLease> Effects;
	TWeakObjectPtr<ATopDownCombatCharacter> SourceCharacter;
	TWeakObjectPtr<USkeletalMeshComponent> SourceMesh;
	UPROPERTY(Transient)
	TArray<TObjectPtr<UMaterialInterface>> OriginalMaterials;
	UPROPERTY(Transient)
	TArray<TObjectPtr<UMaterialInstanceDynamic>> BodyMaterials;
	UPROPERTY(Transient)
	TArray<TObjectPtr<UStaticMeshComponent>> MantleParts;
	UPROPERTY(Transient)
	TArray<TObjectPtr<UMaterialInstanceDynamic>> MantleMaterials;
	UPROPERTY(Transient)
	TArray<TObjectPtr<UStaticMeshComponent>> EntryShrouds;
	UPROPERTY(Transient)
	TArray<TObjectPtr<UMaterialInstanceDynamic>> EntryShroudMaterials;
	TWeakObjectPtr<UParticleSystemComponent> InhaleEffect;
	UPROPERTY(Transient)
	TObjectPtr<UParticleSystem> EntryGather;
	UPROPERTY(Transient)
	TObjectPtr<UParticleSystem> EntryBurst;
	UPROPERTY(Transient)
	TObjectPtr<UParticleSystem> EntryGround;
	UPROPERTY(Transient)
	TObjectPtr<UParticleSystem> ShadowBurst;
	UPROPERTY(Transient)
	TObjectPtr<UParticleSystem> EyeLoop;
	UPROPERTY(Transient)
	TObjectPtr<UParticleSystem> BladeTrail;
	UPROPERTY(Transient)
	TObjectPtr<UMaterialInterface> BladeTrailMaterial;
	double StartedAt = 0.0;
	float FormSeconds = 0.0f;
	int32 EntryPhase = 0;
	uint8 VisualAuditMask = 0;
	bool bInitialized = false;
	bool bStopped = false;
};
