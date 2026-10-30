#pragma once

#include "CoreMinimal.h"
#include "GameFramework/Actor.h"
#include "SparrowSharpImpact.generated.h"

class UStaticMeshComponent;
class UParticleSystemComponent;
class UMaterialInstanceDynamic;

// S의 실제 적중 위치에만 표시하는 짧은 중심광. 판정·피해는 소유하지 않는다.
UCLASS()
class LEARNTOPDOWN_API ASparrowSharpImpact : public AActor
{
	GENERATED_BODY()
public:
	ASparrowSharpImpact();
	void Initialize(int32 DetailPreviewStyle = 0, const FVector& ShotDirection = FVector::ForwardVector, bool bAscended = false, bool bCrystal = false);
	void InitializeReference(const FVector& ShotDirection, bool bRefined, bool bPlume = false);
	virtual void Tick(float DeltaSeconds) override;
private:
	UPROPERTY()
	TObjectPtr<UStaticMeshComponent> Surface;
	UPROPERTY(Transient)
	TObjectPtr<UMaterialInstanceDynamic> Material;
	UPROPERTY(Transient) TObjectPtr<UParticleSystemComponent> ContactFlames;
	double StartedAt = 0.0;
	FVector Direction = FVector::ForwardVector;
	bool bDirectional = false;
};
