#pragma once

#include "CoreMinimal.h"
#include "GameFramework/Actor.h"
#include "SparrowPiercingLance.generated.h"

class UInstancedStaticMeshComponent;
class UMaterialInstanceDynamic;
class UParticleSystemComponent;

// D의 실제 관통 궤적과 적중 지점만 표현한다. 피해·충돌은 ASparrowArrow가 소유한다.
UCLASS()
class LEARNTOPDOWN_API ASparrowPiercingLance : public AActor
{
	GENERATED_BODY()

public:
	ASparrowPiercingLance();
	void InitializeFlight(const FVector& Direction);
	void UpdateHead(const FVector& Position);
	void FinishFlight(const FVector& Position);
	void InitializeImpact(const FVector& Direction, int32 HitOrdinal, bool bWorld);
	virtual void Tick(float DeltaSeconds) override;
	virtual void EndPlay(const EEndPlayReason::Type EndPlayReason) override;

private:
	bool CreateMaterials();
	void Draw();
	void Line(const FVector& From, const FVector& To, float Width);
	void Arc(const FVector& Center, const FVector& AxisA, const FVector& AxisB,
		float Radius, float Begin, float Sweep, int32 Count, float Width);
	void SpawnTexture(bool bWorld);
	UPROPERTY(VisibleAnywhere)
	TObjectPtr<UInstancedStaticMeshComponent> Core;
	UPROPERTY(VisibleAnywhere)
	TObjectPtr<UInstancedStaticMeshComponent> Glow;
	UPROPERTY(Transient)
	TObjectPtr<UMaterialInstanceDynamic> CoreMaterial;
	UPROPERTY(Transient)
	TObjectPtr<UMaterialInstanceDynamic> GlowMaterial;
	UPROPERTY(Transient)
	TObjectPtr<UParticleSystemComponent> Texture;
	TArray<FTransform> CoreTransforms;
	TArray<FTransform> GlowTransforms;
	FVector Origin = FVector::ZeroVector;
	FVector Head = FVector::ZeroVector;
	FVector Forward = FVector::ForwardVector;
	FVector CameraNormal = FVector::UpVector;
	float Age = 0.0f;
	float FinishedAt = -1.0f;
	int32 Ordinal = 0;
	bool bImpact = false;
	bool bWorldHit = false;
	bool bReady = false;
};
