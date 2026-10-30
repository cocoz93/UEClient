#pragma once

#include "CoreMinimal.h"
#include "GameFramework/Actor.h"
#include "SparrowEDesignVisual.generated.h"

class ASparrowArrow;
class UStaticMeshComponent;
class UInstancedStaticMeshComponent;
class UMaterialInstanceDynamic;
class USkeletalMeshComponent;

// 선택용 E 외형만 소유한다. 피해와 곡사 화살의 이동은 실제 스킬/화살 경로에서 처리한다.
UCLASS()
class LEARNTOPDOWN_API ASparrowEDesignVisual : public AActor
{
	GENERATED_BODY()
public:
	ASparrowEDesignVisual();
	bool Initialize(const FVector& Direction, int32 InStyle, bool bInImpact = false, bool bWorld = false);
	void NotifyShot();
	void FadeOut();
	virtual void Tick(float DeltaSeconds) override;
private:
	void Draw();
	void DrawHelios(const FVector& Center, const FRotator& Facing);
	void DrawRegalia();
	void Line(const FVector& A, const FVector& B, float Width);
	UPROPERTY() TObjectPtr<UInstancedStaticMeshComponent> Strands;
	UPROPERTY(Transient) TArray<TObjectPtr<UStaticMeshComponent>> Parts;
	UPROPERTY(Transient) TArray<TObjectPtr<UMaterialInstanceDynamic>> Materials;
	UPROPERTY(Transient) TObjectPtr<UMaterialInstanceDynamic> StrandMaterial;
	TWeakObjectPtr<USkeletalMeshComponent> BowMesh;
	TArray<FTransform> Lines;
	FVector Origin = FVector::ZeroVector;
	FVector OwnerStart = FVector::ZeroVector;
	FVector Forward = FVector::ForwardVector;
	FVector Normal = FVector::UpVector;
	float Age = 0.0f;
	float ShotAt = -1.0f;
	float FadeAt = -1.0f;
	float ImpactScale = 1.0f;
	int32 Style = 0;
	bool bImpact = false;
	bool bAscended = false;
};

// 실제 화살이 지난 위치만 연결한다. 곡선 장식만 그려 다발 판정을 흉내 내지 않는다.
UCLASS()
class LEARNTOPDOWN_API ASparrowEDesignTrail : public AActor
{
	GENERATED_BODY()
public:
	ASparrowEDesignTrail();
	bool Initialize(ASparrowArrow* Arrow, int32 InStyle);
	virtual void Tick(float DeltaSeconds) override;
private:
	TWeakObjectPtr<ASparrowArrow> SourceArrow;
	UPROPERTY() TObjectPtr<UInstancedStaticMeshComponent> Strands;
	UPROPERTY(Transient) TObjectPtr<UMaterialInstanceDynamic> Material;
	TArray<FVector> Positions;
	TArray<float> Times;
	TArray<float> Distances;
	TArray<FTransform> Lines;
	TArray<FVector2f> SegmentData;
	float Age = 0.0f;
	float EndAt = -1.0f;
	int32 Style = 0;
};
