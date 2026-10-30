#pragma once

#include "CoreMinimal.h"
#include "GameFramework/Actor.h"
#include "KwangTrainingDummy.generated.h"

class UCapsuleComponent;
class UStaticMeshComponent;
class UTextRenderComponent;

UCLASS()
class LEARNTOPDOWN_API AKwangTrainingDummy : public AActor
{
	GENERATED_BODY()

public:
	AKwangTrainingDummy();
	virtual float TakeDamage(float DamageAmount, const FDamageEvent& DamageEvent,
		AController* EventInstigator, AActor* DamageCauser) override;
	UFUNCTION(BlueprintPure, Category = "Combat")
	bool IsAlive() const { return Health > 0.0f; }
	UFUNCTION(BlueprintCallable, Category = "Combat")
	void ResetDummy();
	UFUNCTION(BlueprintPure, Category = "Combat")
	FName GetCombatStatus() const;
	void SetCombatStatus(FName Status, float Duration);

protected:
	virtual void BeginPlay() override;

private:
	void UpdateLabel();

	UPROPERTY(VisibleAnywhere)
	TObjectPtr<UCapsuleComponent> Capsule;

	UPROPERTY(VisibleAnywhere)
	TObjectPtr<UStaticMeshComponent> Mesh;

	UPROPERTY(VisibleAnywhere)
	TObjectPtr<UTextRenderComponent> Label;

	UPROPERTY(VisibleAnywhere, Category = "Combat")
	float Health = 100.0f;
	FName CombatStatus = NAME_None;
	double StatusDeadline = 0.0;
	FTimerHandle StatusTimer;
	FTimerHandle RespawnTimer;
};
