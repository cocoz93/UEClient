#pragma once

#include "CoreMinimal.h"
#include "GameFramework/Actor.h"
#include "CountessRuinVisual.generated.h"

class ATopDownCombatCharacter;
class UMaterialInterface;
class UMaterialInstanceDynamic;
class UParticleSystem;
class UParticleSystemComponent;
class UStaticMesh;
class UStaticMeshComponent;

UENUM(BlueprintType)
enum class ECountessRuinKind : uint8 { Spikes, Claws, Eruption };

// 지면 기준의 검붉은 조형과 잔재만 소유한다. 시전·피해·충돌 판정은 스킬 컴포넌트가 맡는다.
UCLASS()
class LEARNTOPDOWN_API ACountessRuinVisual : public AActor
{

	GENERATED_BODY()

public:
	ACountessRuinVisual();
	void Initialize(ATopDownCombatCharacter* Source, ECountessRuinKind Kind,
		const FVector& Origin, const FVector& Direction, float Lifetime);
	UFUNCTION(BlueprintPure, Category = "Skills")
	float GetAge() const { return Age; }
	UFUNCTION(BlueprintPure, Category = "Skills")
	ECountessRuinKind GetKind() const { return RuinKind; }
	virtual void Tick(float DeltaSeconds) override;
	virtual void EndPlay(const EEndPlayReason::Type EndPlayReason) override;

private:
	enum class EMotion : uint8 { Spike, Slash, RiseCut, Plume, Scar, Shard, Field, Core, Hand };
	struct FPiece
	{
		FVector Base;
		FVector Direction;
		FVector Size;
		FVector SourceSize;
		FVector SourceCenter;
		FQuat Basis;
		int32 LongAxis = 0;
		int32 WideAxis = 1;
		float Delay = 0.0f;
		float Span = 1.0f;
		float Seed = 0.0f;
		EMotion Motion = EMotion::Spike;
	};
	int32 AddPiece(UStaticMesh* Mesh, UMaterialInterface* Material, EMotion Motion,
		const FVector& Base, const FVector& Direction, const FVector& Size, float Delay, float Span, float SourceForward = 1.0f);
	FVector Ground(const FVector& Local) const;
	void UpdatePieces();
	void UpdateBursts();
	void Pulse(UParticleSystem* Effect, const FVector& Local, float Scale);
	UPROPERTY(Transient)
	TArray<TObjectPtr<UStaticMeshComponent>> Meshes;
	UPROPERTY(Transient)
	TArray<TObjectPtr<UMaterialInstanceDynamic>> Materials;
	UPROPERTY(Transient)
	TArray<TObjectPtr<UParticleSystemComponent>> Effects;
	UPROPERTY(Transient)
	TObjectPtr<UParticleSystem> ContactEffect;
	UPROPERTY(Transient)
	TObjectPtr<UParticleSystem> GroundEffect;
	TArray<FPiece> Pieces;
	TWeakObjectPtr<ATopDownCombatCharacter> Character;
	ECountessRuinKind RuinKind = ECountessRuinKind::Spikes;
	float Age = 0.0f;
	float Life = 1.0f;
	int32 BurstStage = 0;
	bool bInitialized = false;
};
