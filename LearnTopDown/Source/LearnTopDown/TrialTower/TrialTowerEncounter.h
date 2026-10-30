#pragma once

#include "CoreMinimal.h"
#include "GameFramework/Actor.h"
#include "TrialTowerEncounter.generated.h"

class ATrialTowerMonster;
class UTrialTowerStatusWidget;
class UPlayerCombatComponent;

UENUM(BlueprintType)
enum class ETrialTowerRunState : uint8
{
	Preparing,
	Fighting,
	Intermission,
	Complete,
	Error,
	Defeated
};

// Placed only in the Trial Tower map; all run state ends when that map is left.
UCLASS()
class LEARNTOPDOWN_API ATrialTowerEncounter : public AActor
{
	GENERATED_BODY()

public:
	ATrialTowerEncounter();
	UFUNCTION(BlueprintCallable, Category = "Trial Tower")
	void RestartRun();
	UFUNCTION(BlueprintPure, Category = "Trial Tower")
	int32 GetFloorNumber() const { return FloorNumber; }
	UFUNCTION(BlueprintPure, Category = "Trial Tower")
	int32 GetFloorCount() const { return 3; }
	UFUNCTION(BlueprintPure, Category = "Trial Tower")
	int32 GetRemainingMonsters() const { return PendingSpawns + LivingMonsters.Num(); }
	UFUNCTION(BlueprintPure, Category = "Trial Tower")
	ETrialTowerRunState GetRunState() const { return RunState; }
	UFUNCTION(BlueprintPure, Category = "Trial Tower")
	TArray<ATrialTowerMonster*> GetActiveMonsters() const;
	UFUNCTION(BlueprintPure, Category = "Trial Tower")
	FText GetStatusText() const;
	UFUNCTION(BlueprintPure, Category = "Trial Tower")
	float GetPlayerHealth() const;
	UFUNCTION(BlueprintPure, Category = "Trial Tower")
	float GetMaxPlayerHealth() const;
	UFUNCTION(BlueprintPure, Category = "Trial Tower")
	bool IsPlayerInvulnerable() const;
	UFUNCTION(BlueprintPure, Category = "Trial Tower")
	bool IsPlayerHitReacting() const;
	bool CanMonstersAttack() const { return !bShuttingDown && RunState == ETrialTowerRunState::Fighting && GetPlayerHealth() > 0.0f; }

protected:
	virtual void BeginPlay() override;
	virtual void EndPlay(const EEndPlayReason::Type EndPlayReason) override;

	UPROPERTY(EditInstanceOnly, Category = "Trial Tower")
	TSubclassOf<ATrialTowerMonster> MonsterClass;
	UPROPERTY(EditInstanceOnly, Category = "Trial Tower")
	TArray<FVector> EntryLocations;

private:
	void StartFloor();
	void SpawnNextBatch();
	bool SpawnAtEntry(int32 EntryIndex);
	void CheckFloorCleared();
	void AdvanceFloor();
	void FailRun(const TCHAR* Reason);
	void ClearMonsters();
	void ClearRunTimers();
	UFUNCTION()
	void RefreshStatus();
	UFUNCTION()
	void DefeatPlayer();
	UFUNCTION()
	void OnMonsterDefeated(ATrialTowerMonster* Monster);
	UFUNCTION()
	void OnMonsterDestroyed(AActor* Actor);

	UPROPERTY(Transient)
	TSet<TObjectPtr<ATrialTowerMonster>> LivingMonsters;
	TArray<TWeakObjectPtr<ATrialTowerMonster>> SpawnedMonsters;
	UPROPERTY(Transient)
	TObjectPtr<UTrialTowerStatusWidget> StatusWidget;
	ETrialTowerRunState RunState = ETrialTowerRunState::Preparing;
	int32 FloorNumber = 1;
	int32 PendingSpawns = 0;
	int32 SpawnedThisFloor = 0;
	int32 FailedBatches = 0;
	bool bShuttingDown = false;
	FTimerHandle PrepareTimer;
	FTimerHandle SpawnTimer;
	FTimerHandle IntermissionTimer;
	TWeakObjectPtr<UPlayerCombatComponent> PlayerCombat;
	bool bHasStartedRun = false;
};
