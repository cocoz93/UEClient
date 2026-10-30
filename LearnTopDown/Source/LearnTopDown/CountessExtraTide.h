#pragma once

#include "CoreMinimal.h"
#include "GameFramework/Actor.h"
#include "CountessExtraTide.generated.h"

class UMaterialInstanceDynamic;
class UMaterialInterface;
class UParticleSystem;
class UParticleSystemComponent;
class UStaticMesh;
class UStaticMeshComponent;
class USceneComponent;

// 추가 D의 판정과 잔상을 함께 소유한다. 기존 E 파동의 수명 규칙은 바꾸지 않는다.
UCLASS()
class LEARNTOPDOWN_API ACountessExtraTide : public AActor
{
	GENERATED_BODY()

public:
	ACountessExtraTide();
	void Initialize(const FVector& Direction, float InDamage, float InRange,
		UParticleSystem* Effect, UParticleSystem* InImpactEffect);
	virtual void Tick(float DeltaSeconds) override;

protected:
	virtual void EndPlay(const EEndPlayReason::Type EndPlayReason) override;

private:
	void SpawnSegment(const FVector& Location);
	void StopTravel();
	void CreateBody();
	int32 AddForm(UStaticMesh* Mesh, UMaterialInterface* Material);
	void PlaceForm(int32 Index, const FVector& Center, const FRotator& Rotation, const FVector& Scale, float Opacity);
	void UpdatePresentation();
	void SpawnImpact(const FVector& Location);
	struct FInkBurst
	{
		FVector Location;
		double StartedAt;
		int32 FirstForm;
	};
	UPROPERTY()
	TObjectPtr<USceneComponent> SceneRoot;
	UPROPERTY()
	TObjectPtr<UParticleSystem> SegmentEffect;
	UPROPERTY()
	TObjectPtr<UParticleSystem> ImpactEffect;
	UPROPERTY()
	TSoftObjectPtr<UParticleSystem> BodyEffect;
	TWeakObjectPtr<UParticleSystemComponent> BodyParticle;
	UPROPERTY()
	TSoftObjectPtr<UStaticMesh> BodyWing;
	UPROPERTY()
	TSoftObjectPtr<UStaticMesh> BodyBlade;
	UPROPERTY()
	TSoftObjectPtr<UMaterialInterface> BodyWingMaterial;
	UPROPERTY()
	TSoftObjectPtr<UMaterialInterface> BodyBladeMaterial;
	UPROPERTY()
	TArray<TObjectPtr<UStaticMeshComponent>> Forms;
	UPROPERTY()
	TArray<TObjectPtr<UMaterialInstanceDynamic>> FormMaterials;
	TArray<TWeakObjectPtr<UParticleSystemComponent>> Effects;
	TArray<FInkBurst> Bursts;
	TSet<TWeakObjectPtr<AActor>> DamagedActors;
	FVector TravelDirection = FVector::ForwardVector;
	float Damage = 40.0f;
	float RemainingRange = 900.0f;
	float DistanceSinceSegment = 0.0f;
	float GroundOffset = -70.0f;
	double StartedAt = 0.0;
	double StoppedAt = -1.0;
	bool bTraveling = false;
};
