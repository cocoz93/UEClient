#pragma once

#include "CoreMinimal.h"
#include "GameFramework/Actor.h"
#include "SparrowSharpVolley.generated.h"

class ATopDownCombatCharacter;
class USparrowSkillComponent;
class UAnimInstance;
class UAnimMontage;
class UStaticMeshComponent;
class UMaterialInstanceDynamic;
class UParticleSystemComponent;
class UStaticMesh;
class ASparrowArsenalStudyFX;

// S의 근거리 밀집 사격. 한 번의 방출이 공유하는 피해 집합과 실제 화살 충돌을 재사용한다.
UCLASS()
class LEARNTOPDOWN_API ASparrowSharpVolley : public AActor
{
	GENERATED_BODY()
public:
	ASparrowSharpVolley();
	bool Initialize(ATopDownCombatCharacter* Character, const FVector& Aim);
	void ReleaseRecoveryForMovement();
	UFUNCTION(BlueprintPure, Category = "Skills")
	bool IsCasting() const;
	UFUNCTION(BlueprintPure, Category = "Skills")
	int32 GetWavesFired() const { return WavesFired; }
	UFUNCTION(BlueprintPure, Category = "Skills")
	TArray<FVector> GetReleaseOrigins() const { return ReleaseOrigins; }
	UFUNCTION(BlueprintPure, Category = "Skills")
	float GetRemainingSeconds() const;
	virtual void Tick(float DeltaSeconds) override;
protected:
	virtual void BeginPlay() override;
	virtual void EndPlay(const EEndPlayReason::Type EndPlayReason) override;
private:
	void ReleaseWave();
	void UpdatePressure(float Age);
	bool InitializeArtPresentation(UStaticMesh* Plane);
	void UpdateArtPresentation(float Age, float Since, const FVector& Origin);
	TWeakObjectPtr<ATopDownCombatCharacter> Caster;
	TWeakObjectPtr<USparrowSkillComponent> Skills;
	TWeakObjectPtr<UAnimInstance> Animation;
	TWeakObjectPtr<ASparrowArsenalStudyFX> ArsenalStudy;
	UPROPERTY(Transient)
	TObjectPtr<UAnimMontage> Montage;
	UPROPERTY()
	TArray<TObjectPtr<UStaticMeshComponent>> PressureSurfaces;
	UPROPERTY()
	TArray<TObjectPtr<UStaticMeshComponent>> ChargeArrows;
	UPROPERTY()
	TArray<TObjectPtr<UStaticMeshComponent>> FlowSurfaces;
	UPROPERTY(Transient)
	TArray<TObjectPtr<UMaterialInstanceDynamic>> FlowMaterials;
	UPROPERTY()
	TArray<TObjectPtr<UStaticMeshComponent>> ArtSurfaces;
	UPROPERTY(Transient)
	TArray<TObjectPtr<UMaterialInstanceDynamic>> ArtMaterials;
	UPROPERTY(Transient)
	TObjectPtr<UMaterialInstanceDynamic> PressureMaterial;
	UPROPERTY(Transient)
	TArray<TObjectPtr<UMaterialInstanceDynamic>> PressureSurfaceMaterials;
	UPROPERTY()
	TObjectPtr<UStaticMeshComponent> ReleaseSurface;
	UPROPERTY(Transient)
	TObjectPtr<UMaterialInstanceDynamic> ReleaseMaterial;
	UPROPERTY()
	TArray<TObjectPtr<UParticleSystemComponent>> MuzzleParticles;
	FVector Direction = FVector::ForwardVector;
	TArray<FVector> ReleaseOrigins;
	TArray<float> VisualPathLengths;
	double StartedAt = 0.0;
	float LastReleaseAge = -1.0f;
	int32 WavesFired = 0;
	int32 PreviewStyle = 0;
	int32 DetailPreviewStyle = 0;
	int32 ReferenceStyle = 0;
	int32 ArsenalStudyCandidate = 0;
	bool bInitialized = false;
	bool bAnimationStarted = false;
	bool bMovementReleased = false;
	bool bAscended = false;
};
