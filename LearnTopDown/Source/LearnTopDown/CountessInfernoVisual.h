#pragma once

#include "CoreMinimal.h"
#include "GameFramework/Actor.h"
#include "CountessInfernoVisual.generated.h"

class ATopDownCombatCharacter;
class USceneComponent;
class USkeletalMeshComponent;
class UStaticMeshComponent;
class UAnimSequence;
class UMaterialInterface;
class UMaterialInstanceDynamic;
class UParticleSystem;
class UParticleSystemComponent;
class UPostProcessComponent;

// V의 고정 폭풍과 A의 왕복 회전 분신 외형만 소유한다. 피해와 본체 상태는 변경하지 않는다.
UCLASS()
class LEARNTOPDOWN_API ACountessInfernoVisual : public AActor
{
	GENERATED_BODY()
public:
	ACountessInfernoVisual();
	static constexpr float StormDuration = 3.6f;
	static constexpr float OrbitDuration = 2.3f;
	void Initialize(ATopDownCombatCharacter* Source, bool bStorm, const FVector& Origin,
		const FVector& Direction, float Lifetime);
	UFUNCTION(BlueprintPure, Category = "Skills")
	float GetVisualAge() const { return Age; }
	UFUNCTION(BlueprintPure, Category = "Skills")
	FVector GetFieldCenter() const { return FieldCenter; }
	UFUNCTION(BlueprintPure, Category = "Skills")
	int32 GetVisibleShadowCount() const;
	virtual void Tick(float DeltaSeconds) override;
protected:
	virtual void EndPlay(const EEndPlayReason::Type EndPlayReason) override;
private:
	struct FShadowMotion
	{
		FVector Start = FVector::ZeroVector;
		FVector End = FVector::ZeroVector;
		float Birth = -1.0f;
		int32 Serial = 0;
		int32 Animation = INDEX_NONE;
		bool bVisible = false;
	};
	UParticleSystemComponent* CreateParticle(UParticleSystem* Template, USceneComponent* Parent, FName Tag);
	void StartShadow(int32 Slot, int32 Serial, float Birth);
	void SetShadowPose(int32 Slot, const FVector& Location, const FVector& Facing, int32 Animation, float Sample);
	void SetShadowTrails(int32 Slot, bool bActive, bool bReset = false);
	void UpdateStorm();
	void UpdateOrbit();
	void UpdateInk();
	void UpdateBlades();
	void UpdateSurroundings();
	float GetEnvelope() const;
	UPROPERTY()
	TObjectPtr<USceneComponent> SceneRoot;
	UPROPERTY(Transient)
	TArray<TObjectPtr<USkeletalMeshComponent>> Shadows;
	UPROPERTY(Transient)
	TArray<TObjectPtr<UMaterialInstanceDynamic>> ShadowMaterials;
	UPROPERTY(Transient)
	TArray<TObjectPtr<UAnimSequence>> Attacks;
	UPROPERTY(Transient)
	TArray<TObjectPtr<UParticleSystemComponent>> Trails;
	UPROPERTY(Transient)
	TArray<TObjectPtr<UParticleSystemComponent>> StormLayers;
	UPROPERTY(Transient)
	TArray<TObjectPtr<UStaticMeshComponent>> InkCards;
	UPROPERTY(Transient)
	TArray<TObjectPtr<UMaterialInstanceDynamic>> InkMaterials;
	UPROPERTY(Transient)
	TArray<TObjectPtr<UStaticMeshComponent>> BladeSurfaces;
	UPROPERTY(Transient)
	TArray<TObjectPtr<UMaterialInstanceDynamic>> BladeMaterials;
	UPROPERTY(Transient)
	TObjectPtr<UPostProcessComponent> Surroundings;
	UPROPERTY(Transient)
	TObjectPtr<UMaterialInstanceDynamic> SurroundingsMaterial;
	TWeakObjectPtr<ATopDownCombatCharacter> SourceCharacter;
	TArray<FShadowMotion> ShadowMotion;
	TArray<float> LayerBirths;
	FTransform MeshToCharacter = FTransform::Identity;
	FVector FieldOrigin = FVector::ZeroVector;
	FVector FieldCenter = FVector::ZeroVector;
	FVector FieldForward = FVector::ForwardVector;
	FVector FieldSide = FVector::RightVector;
	float CapsuleHeight = 90.0f;
	float LifeSeconds = StormDuration;
	float Age = 0.0f;
	float Radius = 100.0f;
	int32 ShadowsStarted = 0;
	bool bStormField = true;
	bool bInitialized = false;
};
