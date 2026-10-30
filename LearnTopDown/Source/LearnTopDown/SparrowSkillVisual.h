#pragma once

#include "CoreMinimal.h"
#include "GameFramework/Actor.h"
#include "SparrowSkillVisual.generated.h"

class UInstancedStaticMeshComponent;
class UStaticMeshComponent;
class UStaticMesh;
class UMaterialInstanceDynamic;
class UMaterialInterface;
class UParticleSystem;
class UParticleSystemComponent;
class USceneComponent;

enum class ESparrowVisualKind : uint8
{
	RetreatFocus,
	RicochetFocus,
	RetreatWake,
	ArrowFlight,
	RicochetHit,
	Ambush,
	Skyfall,
	RetreatHit
};

// 신규 ASDF의 표현만 소유한다. 충돌·내비·판정·카메라를 변경하지 않는다.
UCLASS()
class LEARNTOPDOWN_API ASparrowSkillVisual : public AActor
{
	GENERATED_BODY()

public:
	ASparrowSkillVisual();
	void Initialize(ESparrowVisualKind InKind, float Lifetime, float InRadius = 150.0f, float InDelay = 0.0f);
	void Trigger();
	void FadeOut(float Seconds);
	void SetArrowPresentation(bool bChain, int32 InHitOrdinal = 0);
	bool HasTriggered() const { return bTriggered; }
	virtual void Tick(float DeltaSeconds) override;
	virtual void EndPlay(const EEndPlayReason::Type EndPlayReason) override;

private:
	void Draw();
	UParticleSystemComponent* SpawnAuthoredEffect(const TCHAR* Path, const FVector& Location, const FRotator& Rotation,
		float Scale, float ActiveSeconds, USceneComponent* Parent = nullptr, FName Socket = NAME_None);
	void StopAuthoredEffects();
	void UpdateAuthoredEffects();
	void Line(const FVector& From, const FVector& To, float Width = 3.0f);
	void Spark(const FVector& Where, float Size);
	void Ring(const FVector& Center, float InRadius, const FRotator& Rotation = FRotator::ZeroRotator);
	void Wind(const FVector& From, const FVector& To, float Width);
	void Gust(const FVector& From, const FVector& To, float Width, float BendDirection = 1.0f);
	void Arrow(const FVector& Center, const FVector& Direction, float Length, float Width = 3.0f);
	void Arc(const FVector& Center, const FVector& AxisA, const FVector& AxisB, float InRadius,
		float StartAngle, float SweepAngle, int32 Segments, float Width);
	void UpdateInstances(UInstancedStaticMeshComponent* Mesh, const TArray<FTransform>& Transforms);
	void UpdateMeshPool(TArray<TObjectPtr<UStaticMeshComponent>>& Pool, const TArray<FTransform>& Transforms,
		UMaterialInterface* Material);
	UPROPERTY(VisibleAnywhere)
	TObjectPtr<UInstancedStaticMeshComponent> Core;
	UPROPERTY(VisibleAnywhere)
	TObjectPtr<UInstancedStaticMeshComponent> Glow;
	UPROPERTY(VisibleAnywhere)
	TObjectPtr<UInstancedStaticMeshComponent> Sparks;
	// 원본 Sparrow 재질의 ISM usage는 변경하지 않고 일반 메시 풀에서 재사용한다.
	UPROPERTY(Transient)
	TArray<TObjectPtr<UStaticMeshComponent>> RingMeshes;
	UPROPERTY(Transient)
	TArray<TObjectPtr<UStaticMeshComponent>> WindMeshes;
	UPROPERTY()
	TObjectPtr<UStaticMesh> PlaneMesh;
	UPROPERTY(VisibleAnywhere)
	TObjectPtr<UInstancedStaticMeshComponent> ArrowMeshes;
	UPROPERTY()
	TSoftObjectPtr<UMaterialInterface> StripSource;
	UPROPERTY()
	TSoftObjectPtr<UMaterialInterface> SparkSource;
	UPROPERTY()
	TSoftObjectPtr<UMaterialInterface> RingSource;
	UPROPERTY()
	TSoftObjectPtr<UMaterialInterface> WindSource;
	UPROPERTY()
	TSoftObjectPtr<UMaterialInterface> ExtraGustSource;
	UPROPERTY(Transient)
	TObjectPtr<UMaterialInstanceDynamic> CoreMaterial;
	UPROPERTY(Transient)
	TObjectPtr<UMaterialInstanceDynamic> GlowMaterial;
	UPROPERTY(Transient)
	TObjectPtr<UMaterialInstanceDynamic> SparkMaterial;
	UPROPERTY(Transient)
	TObjectPtr<UMaterialInstanceDynamic> RingMaterial;
	UPROPERTY(Transient)
	TObjectPtr<UMaterialInstanceDynamic> WindMaterial;
	UPROPERTY(Transient)
	TObjectPtr<UMaterialInstanceDynamic> ArrowMaterial;
	TArray<FTransform> CoreTransforms;
	TArray<FTransform> GlowTransforms;
	TArray<FTransform> SparkTransforms;
	TArray<FTransform> RingTransforms;
	TArray<FTransform> WindTransforms;
	TArray<FTransform> ArrowTransforms;
	TArray<FVector> FlightHistory;
	ESparrowVisualKind Kind = ESparrowVisualKind::RicochetHit;
	FVector Anchor = FVector::ZeroVector;
	FVector Forward = FVector::ForwardVector;
	FVector CameraNormal = FVector(0.0f, 0.0f, 1.0f);
	FVector WakeEnd = FVector::ZeroVector;
	float Age = 0.0f;
	float Radius = 150.0f;
	float Delay = 0.0f;
	float TriggerAge = 0.0f;
	float FadeAge = -1.0f;
	float FadeSeconds = 0.35f;
	bool bTriggered = false;
	bool bInitialized = false;
	bool bChainArrow = false;
	bool bUsesExtraGust = false;
	int32 HitOrdinal = 0;
	struct FAuthoredEffect
	{
		TWeakObjectPtr<UParticleSystemComponent> Component;
		float StopAt = 0.0f;
		bool bStopped = false;
	};
	TArray<FAuthoredEffect> AuthoredEffects;
};
