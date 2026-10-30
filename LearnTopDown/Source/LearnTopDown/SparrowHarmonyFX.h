#pragma once

#include "CoreMinimal.h"
#include "GameFramework/Actor.h"
#include "SparrowHarmonyFX.generated.h"

class ASparrowArrow;
class UInstancedStaticMeshComponent;
class UMaterialInstanceDynamic;
class UParticleSystemComponent;

// 실제 시전/발사/이동 신호만 따른다. 피해·충돌·조작 상태를 소유하지 않는다.
UCLASS()
class LEARNTOPDOWN_API ASparrowHarmonyFX : public AActor
{
	GENERATED_BODY()
public:
	ASparrowHarmonyFX();
	static bool Enabled();
	static constexpr float APairHalfSpacing = 80.0f;
	static ASparrowHarmonyFX* Create(AActor* Owner, FName Kind, const FVector& Point,
		const FVector& Direction, float Charge = .38f, AActor* Source = nullptr);
	void NotifyShot();
	void TrackArrow(ASparrowArrow* Arrow);
	virtual void Tick(float DeltaSeconds) override;
protected:
	virtual void EndPlay(const EEndPlayReason::Type Reason) override;
private:
	bool Initialize(FName Kind, const FVector& Point, const FVector& Direction, float Charge, AActor* Source);
	FVector Anchor() const;
	void Strip(const FVector& A, const FVector& B, float Width, float Alpha, float Path = 0.f);
	void Dot(const FVector& Point, float Size, float Alpha);
	void Arrow(const FVector& Tip, const FVector& Direction, float Size, float Alpha = 1.f);
	void Pulse(const FVector& Point, float Scale);
	void Rain();
	void Orbit();
	void Volley();
	void Bow();
	void Gather();
	void Blink();
	void Upload();
	UPROPERTY() TObjectPtr<UInstancedStaticMeshComponent> Ribbons;
	UPROPERTY() TObjectPtr<UInstancedStaticMeshComponent> Motes;
	UPROPERTY() TObjectPtr<UInstancedStaticMeshComponent> ArrowHeads;
	UPROPERTY(Transient) TObjectPtr<UMaterialInstanceDynamic> RibbonMaterial;
	UPROPERTY(Transient) TObjectPtr<UMaterialInstanceDynamic> MoteMaterial;
	UPROPERTY(Transient) TObjectPtr<UMaterialInstanceDynamic> ArrowMaterial;
	UPROPERTY(Transient) TArray<TObjectPtr<UParticleSystemComponent>> Pulses;
	TWeakObjectPtr<AActor> Follow;
	TArray<TWeakObjectPtr<ASparrowArrow>> Arrows;
	TArray<FVector> LastArrowPoints;
	TArray<bool> ArrowEnded;
	TArray<FTransform> RibbonTransforms, MoteTransforms, ArrowTransforms;
	TArray<FVector4f> RibbonData, MoteData;
	FVector Origin = FVector::ZeroVector, Forward = FVector::ForwardVector, CameraNormal = FVector::UpVector;
	FName Role;
	float Age = 0.f, ChargeSeconds = .38f, ShotAt = -1.f;
	int32 LastPulse = -1;
	bool bHasFollow = false;
};
