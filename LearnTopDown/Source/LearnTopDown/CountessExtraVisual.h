#pragma once

#include "CoreMinimal.h"
#include "GameFramework/Actor.h"
#include "CountessExtraVisual.generated.h"

class UMaterialInterface;
class UMaterialInstanceDynamic;
class UStaticMesh;
class UStaticMeshComponent;
class USceneComponent;
class UParticleSystemComponent;

enum class ECountessExtraVisual : uint8 { Seal, Rush, Tide, Ambush, Impact, AuthoredImpact };

// 추가 스킬의 형상과 짧은 후행 외형만 소유한다. 피해·이동·범위 판정은 갖지 않는다.
UCLASS()
class LEARNTOPDOWN_API ACountessExtraVisual : public AActor
{
	GENERATED_BODY()

public:
	ACountessExtraVisual();
	void Initialize(ECountessExtraVisual InKind, const FVector& Direction, float Lifetime, AActor* Follow = nullptr);
	void Trigger();
	void Retire();
	virtual void Tick(float DeltaSeconds) override;
	virtual void EndPlay(const EEndPlayReason::Type EndPlayReason) override;

private:
	void AddPart(UStaticMesh* Mesh, UMaterialInterface* Material, bool bCard, float Shape = 0.0f);
	void SetPart(int32 Index, const FVector& Center, const FVector& Direction, float Length, float Width, float Fade, float Pulse, float Opacity = 1.0f, bool bFaceCamera = false);
	void UpdateParts();
	UParticleSystemComponent* SpawnAuthored(const TCHAR* Path, const FVector& Offset, const FRotator& Rotation, float Scale);
	void StopAuthored();
	UPROPERTY()
	TObjectPtr<USceneComponent> SceneRoot;
	UPROPERTY()
	TArray<TObjectPtr<UStaticMeshComponent>> Parts;
	UPROPERTY()
	TArray<TObjectPtr<UMaterialInstanceDynamic>> Materials;
	UPROPERTY()
	TArray<TObjectPtr<UParticleSystemComponent>> AuthoredEffects;
	TWeakObjectPtr<UParticleSystemComponent> GatherEffect;
	UPROPERTY()
	TSoftObjectPtr<UMaterialInterface> InkMaterial;
	UPROPERTY()
	TSoftObjectPtr<UMaterialInterface> QualityMaterial;
	TArray<bool> Cards;
	TWeakObjectPtr<AActor> FollowActor;
	FVector FollowOffset = FVector::ZeroVector;
	FVector ViewDirectionLocal = FVector(1, 1, 1).GetSafeNormal();
	ECountessExtraVisual Kind = ECountessExtraVisual::Seal;
	double StartedAt = 0.0;
	double TriggeredAt = -1.0;
	double RetiredAt = -1.0;
	float LifeSeconds = 1.0f;
};
