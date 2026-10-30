#pragma once

#include "CoreMinimal.h"
#include "GameFramework/Actor.h"
#include "SparrowFlameStudies.generated.h"

class ATopDownCombatCharacter;
class ASparrowArrow;
class ASparrowAscensionWings;
class UStaticMeshComponent;
class UPrimitiveComponent;
class UMaterialInstanceDynamic;

// 채택한 V3와 D 준비/비교안을 그린다. 피해·변신 수명·이동 제어는 소유하지 않는다.
UCLASS()
class LEARNTOPDOWN_API ASparrowFlameStudies : public AActor
{
	GENERATED_BODY()
public:
	ASparrowFlameStudies();
	static int32 GetDPreview();
	static int32 GetVPreview();
	static int32 GetVDesignPreview();
	bool InitializeD(ATopDownCombatCharacter* Character, const FVector& Aim, float ChargeSeconds);
	bool InitializeDCharge(ATopDownCombatCharacter* Character, const FVector& Aim, float ChargeSeconds);
	bool InitializeV(ATopDownCombatCharacter* Character, ASparrowAscensionWings* NativeForm);
	static ASparrowFlameStudies* FindActiveForm(ATopDownCombatCharacter* Character);
	bool BeginFormFold(const FVector& Aim, float ChargeSeconds);
	void ReleaseFormFold();
	void CancelFormFold();
	void Release(ASparrowArrow* Arrow);
	UFUNCTION(BlueprintPure, Category = "Studies") bool HasReleased() const { return ReleasedAt >= 0.0f; }
	UFUNCTION(BlueprintPure, Category = "Studies") int32 GetDesign() const { return Design; }
	UFUNCTION(BlueprintPure, Category = "Studies") bool IsFormStudy() const { return bForm; }
	UFUNCTION(BlueprintPure, Category = "Studies") bool IsFoldingForm() const { return FoldStartedAt >= 0.0f; }
	UFUNCTION(BlueprintPure, Category = "Studies") float GetFormFoldAmount() const { return FoldAmount; }
	UFUNCTION(BlueprintPure, Category = "Studies") float GetTrackedDistance() const { return Travelled; }
	virtual void Tick(float DeltaTime) override;
	virtual void EndPlay(const EEndPlayReason::Type EndPlayReason) override;
private:
	bool AddSurface(const TCHAR* MaterialName, int32 Index, bool bCylinder = false);
	bool AddDesignSurface(const TCHAR* MeshName, const TCHAR* MaterialName, int32 Index);
	void HideForStudy(UPrimitiveComponent* Part);
	UFUNCTION() void OnProjectileDestroyed(AActor* DestroyedActor);
	void DrawD();
	void DrawDCharge();
	void DrawV();
	void DrawVEntry();
	void DrawVDesign();
	void DrawCelestialV();
	void DrawPlumeV();
	void UpdateVGroundAnchor();
	void DrawRenaissanceV();
	void SetSurface(int32 Index, const FVector& Position, const FQuat& Rotation, const FVector& Scale, float Opacity = 1.0f);
	FQuat Face(const FVector& Axis, const FVector& Position) const;
	UPROPERTY(Transient) TArray<TObjectPtr<UStaticMeshComponent>> Surfaces;
	UPROPERTY(Transient) TArray<TObjectPtr<UMaterialInstanceDynamic>> Materials;
	TArray<TWeakObjectPtr<UPrimitiveComponent>> HiddenParts;
	TArray<bool> OriginalVisibility;
	TWeakObjectPtr<ATopDownCombatCharacter> Caster;
	TWeakObjectPtr<ASparrowAscensionWings> Form;
	TWeakObjectPtr<ASparrowArrow> Projectile;
	FVector Direction = FVector::ForwardVector;
	FVector Origin = FVector::ZeroVector;
	FVector EntryGroundNormal = FVector::UpVector;
	FVector Head = FVector::ZeroVector;
	FVector FoldDirection = FVector::ForwardVector;
	float Age = 0.0f;
	float ReleasedAt = -1.0f;
	float Charge = .52f;
	float Travelled = 0.0f;
	float FoldStartedAt = -1.0f;
	float FoldReleasedAt = -1.0f;
	float FoldDuration = .42f;
	float FoldAmount = 0.0f;
	int32 Design = 0;
	int32 EntryStart = INDEX_NONE;
	int32 VDesign = 0;
	uint8 EntryDiagnosticPhases = 0;
	bool bForm = false;
};
