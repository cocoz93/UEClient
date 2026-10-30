#pragma once

#include "CoreMinimal.h"
#include "GameFramework/Actor.h"
#include "SparrowBowMuzzleStudy.generated.h"

class ATopDownCombatCharacter;
class ASparrowHarmonyFX;
class UInstancedStaticMeshComponent;
class UMaterialInstanceDynamic;
class USkeletalMeshComponent;
class USplineMeshComponent;
class UStaticMeshComponent;

// D 활의 실제 본을 따라가는 선택형 외관. 투사체·피해·경로 깃털은 기존 스킬이 소유한다.
UCLASS()
class LEARNTOPDOWN_API ASparrowBowMuzzleStudy : public AActor
{
	GENERATED_BODY()
public:
	ASparrowBowMuzzleStudy();
	static int32 GetPreviewStyle();
	bool Initialize(ATopDownCombatCharacter* Character, const FVector& Aim, float ChargeSeconds);
	void Release();
	void Cancel();
	virtual void Tick(float DeltaSeconds) override;
	UFUNCTION(BlueprintPure) int32 GetDesign() const { return Design; }
	UFUNCTION(BlueprintPure) bool HasReleased() const { return ReleasedAt >= 0.0f; }
	UFUNCTION(BlueprintPure) bool HasValidMaterials() const { return bReady; }
	UFUNCTION(BlueprintPure) float GetBowSpan() const { return BowSpan; }
	UFUNCTION(BlueprintPure) FVector GetTrackedNock() const { return Nock; }
	UFUNCTION(BlueprintPure) FVector GetTrackedUpperTip() const { return UpperTip; }
	UFUNCTION(BlueprintPure) FVector GetTrackedLowerTip() const { return LowerTip; }
	UFUNCTION(BlueprintPure) int32 GetVisibleSegmentCount() const;

private:
	TWeakObjectPtr<ASparrowHarmonyFX> HarmonyFX;
	static constexpr int32 BankCount = 5;
	void Draw();
	bool CreateFeatherSkin();
	void DrawFeatherSkin(float Preparation, float Pulse, float Fade);
	bool CreateOrnateBow();
	void DrawOrnateBow(float Preparation, float Pulse, float Fade);
	FVector LimbPoint(int32 Side, float T) const;
	void Segment(int32 Bank, const FVector& A, const FVector& B, float Width,
		float Start, float Span, float Seed, float Alpha = 1.0f);
	void Upload();
	UPROPERTY(Transient) TArray<TObjectPtr<UInstancedStaticMeshComponent>> Banks;
	UPROPERTY(Transient) TArray<TObjectPtr<UMaterialInstanceDynamic>> Materials;
	UPROPERTY(Transient) TArray<TObjectPtr<USplineMeshComponent>> FeatherSkin;
	UPROPERTY(Transient) TObjectPtr<UMaterialInstanceDynamic> FeatherMaterial;
	UPROPERTY(Transient) TObjectPtr<UStaticMeshComponent> OrnateBow;
	UPROPERTY(Transient) TObjectPtr<UMaterialInstanceDynamic> OrnateMaterial;
	TArray<FTransform> Transforms[BankCount];
	TArray<FVector4f> InstanceData[BankCount];
	TWeakObjectPtr<ATopDownCombatCharacter> Caster;
	TWeakObjectPtr<USkeletalMeshComponent> Body;
	FVector Limb[2][5];
	FVector ReleaseLimb[2][3];
	FVector ReleaseGrip = FVector::ZeroVector;
	FVector ReleaseBowNormal = FVector::UpVector;
	FVector Nock = FVector::ZeroVector;
	FVector UpperTip = FVector::ZeroVector;
	FVector LowerTip = FVector::ZeroVector;
	FVector Forward = FVector::ForwardVector;
	FVector CameraNormal = FVector::UpVector;
	FVector BowNormal = FVector::ForwardVector;
	float Age = 0.0f;
	float Charge = .5f;
	float ReleasedAt = -1.0f;
	float CancelledAt = -1.0f;
	float BowSpan = 0.0f;
	int32 Design = 0;
	int32 FeatherAuditSamples = 0;
	bool bReady = false;
};
