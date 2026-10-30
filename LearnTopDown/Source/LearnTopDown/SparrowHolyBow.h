#pragma once

#include "CoreMinimal.h"
#include "GameFramework/Actor.h"
#include "SparrowHolyBow.generated.h"

class UStaticMeshComponent;
class UInstancedStaticMeshComponent;
class UMaterialInstanceDynamic;
class ASparrowEDesignVisual;

// E 전용 시전/접촉 연출. 실제 단발의 피해·충돌·발사 예약은 SkillComponent가 소유한다.
UCLASS()
class LEARNTOPDOWN_API ASparrowHolyBow : public AActor
{
	GENERATED_BODY()
public:
	ASparrowHolyBow();
	void Initialize(const FVector& Direction, int32 InDesignStyle = -1);
	void InitializeImpact(const FVector& Direction, bool bWorld, int32 InDesignStyle = -1);
	UFUNCTION(BlueprintPure) int32 GetDesignStyle() const { return DesignStyle; }
	void NotifyShot();
	void FadeOut();
	virtual void Tick(float DeltaSeconds) override;
	virtual void EndPlay(const EEndPlayReason::Type EndPlayReason) override;
	UFUNCTION(BlueprintPure) int32 GetShotsObserved() const { return ShotsObserved; }
	UFUNCTION(BlueprintPure) bool HasValidMaterials() const { return bReady; }
	UFUNCTION(BlueprintPure) bool IsFading() const { return FinishedAt >= 0.0f; }
	UFUNCTION(BlueprintPure) bool IsImpact() const { return bImpact; }

private:
	void Draw();
	void DrawImpact();
	void UploadGeometry();
	void Line(const FVector& A, const FVector& B, float Width);
	UPROPERTY(VisibleAnywhere) TObjectPtr<UStaticMeshComponent> Bow;
	UPROPERTY(VisibleAnywhere) TObjectPtr<UInstancedStaticMeshComponent> Core;
	UPROPERTY(VisibleAnywhere) TObjectPtr<UInstancedStaticMeshComponent> Glow;
	UPROPERTY(Transient) TObjectPtr<UMaterialInstanceDynamic> BowMaterial;
	UPROPERTY(Transient) TObjectPtr<UMaterialInstanceDynamic> CoreMaterial;
	UPROPERTY(Transient) TObjectPtr<UMaterialInstanceDynamic> GlowMaterial;
	TWeakObjectPtr<ASparrowEDesignVisual> DesignVisual;
	int32 DesignStyle = 0;
	TArray<FTransform> CoreTransforms;
	TArray<FTransform> GlowTransforms;
	FVector Origin = FVector::ZeroVector;
	FVector OwnerStart = FVector::ZeroVector;
	FVector Forward = FVector::ForwardVector;
	FVector CameraNormal = FVector::UpVector;
	float Age = 0.0f;
	float LastShotAge = -1.0f;
	float FinishedAt = -1.0f;
	int32 ShotsObserved = 0;
	bool bReady = false;
	bool bImpact = false;
	bool bAscended = false;
	float ImpactScale = 1.0f;
};
