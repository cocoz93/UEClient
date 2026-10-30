#pragma once

#include "CoreMinimal.h"
#include "GameFramework/Actor.h"
#include "SparrowFeatherTrail.generated.h"

class ASparrowArrow;
class UStaticMeshComponent;
class UMaterialInstanceDynamic;

// F 실탄은 기존 0.6초 깃털을, D 실탄은 별도 재질과 수명의 경로 깃털을 남긴다.
UCLASS()
class LEARNTOPDOWN_API ASparrowFeatherTrail : public AActor
{
	GENERATED_BODY()
public:
	ASparrowFeatherTrail();
	bool Initialize(ASparrowArrow* Arrow, bool bAscended = false);
	bool InitializeD(ASparrowArrow* Arrow, bool bAscended = false);
	void StopTracking(const FVector& FinalLocation);
	virtual void Tick(float DeltaSeconds) override;
protected:
	virtual void EndPlay(const EEndPlayReason::Type EndPlayReason) override;
private:
	struct FFeatherSample
	{
		FVector Position = FVector::ZeroVector;
		FVector Direction = FVector::ForwardVector;
		float BornAt = -10.0f;
		int32 Seed = 0;
	};
	void AppendSegment(const FVector& Position);
	void Emit(const FVector& Position, const FVector& Direction);
	UFUNCTION() void OnTrackedArrowDestroyed(AActor* DestroyedActor);
	UPROPERTY(Transient) TArray<TObjectPtr<UStaticMeshComponent>> Surfaces;
	UPROPERTY(Transient) TArray<TObjectPtr<UMaterialInstanceDynamic>> Materials;
	TArray<FFeatherSample> Samples;
	TWeakObjectPtr<ASparrowArrow> SourceArrow;
	FVector LastPosition = FVector::ZeroVector;
	FVector LastDirection = FVector::ForwardVector;
	float Age = 0.0f;
	float DistanceSinceSample = 0.0f;
	float SampleSpacing = 70.0f;
	float FadeLifetime = .60f;
	float GroundLimit = 0.0f;
	int32 Emitted = 0;
	bool bReady = false;
	bool bTracking = false;
	bool bForm = false;
	bool bDRoute = false;
};
