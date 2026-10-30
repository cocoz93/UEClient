#pragma once

#include "CoreMinimal.h"
#include "GameFramework/Actor.h"
#include "CountessDarkTide.generated.h"

class UParticleSystem;
class UParticleSystemComponent;
class USceneComponent;
class USoundBase;

// E는 시전 종료 후에도 진행한다. 이동 구간을 스윕하여 낮은 프레임에서도 적을 놓치지 않는다.
UCLASS()
class LEARNTOPDOWN_API ACountessDarkTide : public AActor
{
	GENERATED_BODY()

public:
	ACountessDarkTide();
	void Initialize(const FVector& Direction, float InDamage, float InRange,
		UParticleSystem* Effect, UParticleSystem* InImpactEffect);
	virtual void Tick(float DeltaTime) override;

private:
	UPROPERTY()
	TObjectPtr<USceneComponent> SceneRoot;
	UPROPERTY()
	TObjectPtr<UParticleSystemComponent> Particle;
	UPROPERTY()
	TObjectPtr<UParticleSystem> ImpactEffect;
	UPROPERTY()
	TObjectPtr<UParticleSystem> SegmentEffect;
	UPROPERTY()
	TObjectPtr<USoundBase> ImpactSound;
	void SpawnVisualSegment(const FVector& Location);
	float DistanceSinceSegment = 0.0f;
	float GroundOffset = -70.0f;
	bool bDetailedFX = false;
	TSet<TWeakObjectPtr<AActor>> DamagedActors;
	FVector TravelDirection = FVector::ForwardVector;
	float Damage = 45.0f;
	float RemainingRange = 900.0f;
	float Speed = 1000.0f;
	float Radius = 100.0f;
};
