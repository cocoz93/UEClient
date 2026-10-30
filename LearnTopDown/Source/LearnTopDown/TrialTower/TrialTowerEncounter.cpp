#include "TrialTowerEncounter.h"

#include "TrialTowerMonster.h"
#include "TrialTowerStatusWidget.h"
#include "../PlayerCombatComponent.h"
#include "Components/CapsuleComponent.h"
#include "Engine/World.h"
#include "GameFramework/PlayerController.h"
#include "Kismet/GameplayStatics.h"
#include "NavigationSystem.h"
#include "TimerManager.h"

#define LOCTEXT_NAMESPACE "TrialTower"

ATrialTowerEncounter::ATrialTowerEncounter()
{
	PrimaryActorTick.bCanEverTick = false;
	EntryLocations = {FVector(0, 2080, 0), FVector(2080, 0, 0),
		FVector(0, -2080, 0), FVector(-2080, 0, 0)};
}

void ATrialTowerEncounter::BeginPlay()
{
	Super::BeginPlay();
	if (APlayerController* Player = UGameplayStatics::GetPlayerController(this, 0))
	{
		PlayerCombat = Player->FindComponentByClass<UPlayerCombatComponent>();
		if (UPlayerCombatComponent* Combat = PlayerCombat.Get())
		{
			Combat->OnStateChanged.AddDynamic(this, &ATrialTowerEncounter::RefreshStatus);
			Combat->OnDied.AddDynamic(this, &ATrialTowerEncounter::DefeatPlayer);
		}
		StatusWidget = CreateWidget<UTrialTowerStatusWidget>(Player, UTrialTowerStatusWidget::StaticClass());
		if (StatusWidget)
		{
			StatusWidget->InitializeEncounter(this);
			StatusWidget->AddToViewport(20);
		}
	}
	RestartRun();
}

void ATrialTowerEncounter::EndPlay(const EEndPlayReason::Type EndPlayReason)
{
	bShuttingDown = true;
	ClearRunTimers();
	if (UPlayerCombatComponent* Combat = PlayerCombat.Get())
	{
		Combat->OnStateChanged.RemoveDynamic(this, &ATrialTowerEncounter::RefreshStatus);
		Combat->OnDied.RemoveDynamic(this, &ATrialTowerEncounter::DefeatPlayer);
	}
	ClearMonsters();
	if (StatusWidget)
	{
		StatusWidget->RemoveFromParent();
		StatusWidget = nullptr;
	}
	Super::EndPlay(EndPlayReason);
}

void ATrialTowerEncounter::RestartRun()
{
	if (bShuttingDown || !GetWorld()) { return; }
	ClearRunTimers();
	RunState = ETrialTowerRunState::Preparing;
	PendingSpawns = 0;
	ClearMonsters();
	UPlayerCombatComponent* Combat = PlayerCombat.Get();
	if (!Combat || (bHasStartedRun && !Combat->RespawnPlayer()))
	{
		FailRun(TEXT("Could not respawn the selected player character"));
		return;
	}
	bHasStartedRun = true;
	FloorNumber = 1;
	SpawnedThisFloor = 0;
	FailedBatches = 0;
	RefreshStatus();
	if (!MonsterClass || EntryLocations.Num() != 4)
	{
		FailRun(TEXT("The tower requires a monster class and exactly four entries"));
		return;
	}
	GetWorldTimerManager().SetTimer(PrepareTimer, this, &ATrialTowerEncounter::StartFloor, 3.0f, false);
}

void ATrialTowerEncounter::StartFloor()
{
	if (bShuttingDown || (RunState != ETrialTowerRunState::Preparing &&
		RunState != ETrialTowerRunState::Intermission)) { return; }
	ClearMonsters();
	SpawnedThisFloor = 0;
	FailedBatches = 0;
	PendingSpawns = 4 * (FloorNumber + 1); // 8, 12, 16; every entry supplies an equal share.
	RunState = ETrialTowerRunState::Fighting;
	UE_LOG(LogTemp, Display, TEXT("TrialTower floor=%d started total=%d"), FloorNumber, PendingSpawns);
	RefreshStatus();
	SpawnNextBatch();
	if (RunState == ETrialTowerRunState::Fighting && PendingSpawns > 0)
	{
		GetWorldTimerManager().SetTimer(SpawnTimer, this, &ATrialTowerEncounter::SpawnNextBatch, 0.85f, true);
	}
}

bool ATrialTowerEncounter::SpawnAtEntry(int32 EntryIndex)
{
	UNavigationSystemV1* Navigation = FNavigationSystem::GetCurrent<UNavigationSystemV1>(GetWorld());
	APawn* Player = UGameplayStatics::GetPlayerPawn(this, 0);
	if (!Navigation || !Player) { return false; }
	const ATrialTowerMonster* Defaults = MonsterClass.GetDefaultObject();
	const float HalfHeight = Defaults->GetCapsuleComponent()->GetScaledCapsuleHalfHeight();
	const FVector Entry = EntryLocations[EntryIndex];
	const FVector Side = FMath::Abs(Entry.X) > FMath::Abs(Entry.Y) ? FVector::YAxisVector : FVector::XAxisVector;
	for (float Offset : {0.0f, -120.0f, 120.0f})
	{
		FNavLocation Projected;
		if (!Navigation->ProjectPointToNavigation(Entry + Side * Offset, Projected, FVector(65, 65, 250),
			&Defaults->GetNavAgentPropertiesRef())) { continue; }
		const FVector Location = Projected.Location + FVector(0, 0, HalfHeight + 3.0f);
		FRotator Facing = (Player->GetActorLocation() - Location).Rotation();
		Facing.Pitch = 0;
		Facing.Roll = 0;
		const FTransform Transform(Facing, Location);
		ATrialTowerMonster* Monster = GetWorld()->SpawnActorDeferred<ATrialTowerMonster>(MonsterClass, Transform,
			this, nullptr, ESpawnActorCollisionHandlingMethod::AdjustIfPossibleButDontSpawnIfColliding);
		if (!Monster) { continue; }
		Monster->InitializeForFloor(100.0f, 225.0f);
		Monster->InitializeEncounter(this);
		UGameplayStatics::FinishSpawningActor(Monster, Transform);
		if (!IsValid(Monster)) { continue; }
		Monster->OnDefeated.AddDynamic(this, &ATrialTowerEncounter::OnMonsterDefeated);
		Monster->OnDestroyed.AddDynamic(this, &ATrialTowerEncounter::OnMonsterDestroyed);
		LivingMonsters.Add(Monster);
		SpawnedMonsters.Add(Monster);
		--PendingSpawns;
		++SpawnedThisFloor;
		UE_LOG(LogTemp, Display, TEXT("TrialTower spawned floor=%d entry=%d monster=%s"),
			FloorNumber, EntryIndex, *Monster->GetName());
		return true;
	}
	return false;
}

void ATrialTowerEncounter::SpawnNextBatch()
{
	if (bShuttingDown || RunState != ETrialTowerRunState::Fighting) { return; }
	const int32 Before = PendingSpawns;
	for (int32 Attempt = 0; Attempt < 4 && PendingSpawns > 0; ++Attempt)
	{
		if (!SpawnAtEntry(SpawnedThisFloor % 4)) { break; }
	}
	FailedBatches = Before == PendingSpawns ? FailedBatches + 1 : 0;
	if (FailedBatches >= 8)
	{
		FailRun(TEXT("Repeated spawn failure: check entry navigation and collision"));
		return;
	}
	if (PendingSpawns == 0) { GetWorldTimerManager().ClearTimer(SpawnTimer); }
	RefreshStatus();
	CheckFloorCleared();
}

void ATrialTowerEncounter::OnMonsterDefeated(ATrialTowerMonster* Monster)
{
	if (bShuttingDown || LivingMonsters.Remove(Monster) == 0) { return; }
	RefreshStatus();
	CheckFloorCleared();
}

void ATrialTowerEncounter::OnMonsterDestroyed(AActor* Actor)
{
	if (ATrialTowerMonster* Monster = Cast<ATrialTowerMonster>(Actor))
	{
		OnMonsterDefeated(Monster);
	}
}

void ATrialTowerEncounter::CheckFloorCleared()
{
	// Pending spawns are part of the floor: killing an early batch cannot skip it.
	if (RunState != ETrialTowerRunState::Fighting || PendingSpawns != 0 || !LivingMonsters.IsEmpty()) { return; }
	GetWorldTimerManager().ClearTimer(SpawnTimer);
	UE_LOG(LogTemp, Display, TEXT("TrialTower floor=%d cleared"), FloorNumber);
	if (FloorNumber == GetFloorCount())
	{
		RunState = ETrialTowerRunState::Complete;
	}
	else
	{
		RunState = ETrialTowerRunState::Intermission;
		GetWorldTimerManager().SetTimer(IntermissionTimer, this, &ATrialTowerEncounter::AdvanceFloor, 3.0f, false);
	}
	RefreshStatus();
}

void ATrialTowerEncounter::AdvanceFloor()
{
	if (bShuttingDown || RunState != ETrialTowerRunState::Intermission) { return; }
	++FloorNumber;
	StartFloor();
}

void ATrialTowerEncounter::FailRun(const TCHAR* Reason)
{
	UE_LOG(LogTemp, Error, TEXT("TrialTower stopped: %s"), Reason);
	ClearRunTimers();
	RunState = ETrialTowerRunState::Error;
	PendingSpawns = 0;
	ClearMonsters();
	RefreshStatus();
}

void ATrialTowerEncounter::ClearRunTimers()
{
	GetWorldTimerManager().ClearTimer(PrepareTimer);
	GetWorldTimerManager().ClearTimer(SpawnTimer);
	GetWorldTimerManager().ClearTimer(IntermissionTimer);
}

void ATrialTowerEncounter::ClearMonsters()
{
	LivingMonsters.Reset();
	for (const TWeakObjectPtr<ATrialTowerMonster>& Item : SpawnedMonsters)
	{
		if (ATrialTowerMonster* Monster = Item.Get())
		{
			Monster->OnDefeated.RemoveDynamic(this, &ATrialTowerEncounter::OnMonsterDefeated);
			Monster->OnDestroyed.RemoveDynamic(this, &ATrialTowerEncounter::OnMonsterDestroyed);
			Monster->Destroy();
		}
	}
	SpawnedMonsters.Reset();
}

TArray<ATrialTowerMonster*> ATrialTowerEncounter::GetActiveMonsters() const
{
	TArray<ATrialTowerMonster*> Result;
	Result.Reserve(LivingMonsters.Num());
	for (ATrialTowerMonster* Monster : LivingMonsters)
	{
		if (IsValid(Monster)) { Result.Add(Monster); }
	}
	return Result;
}

FText ATrialTowerEncounter::GetStatusText() const
{
	switch (RunState)
	{
	case ETrialTowerRunState::Preparing: return LOCTEXT("Preparing", "잠시 후 전투가 시작됩니다");
	case ETrialTowerRunState::Fighting:
		if (IsPlayerHitReacting()) { return LOCTEXT("HitReaction", "피격 · 잠시 행동할 수 없습니다"); }
		return LOCTEXT("Fight", "몬스터를 모두 처치하세요");
	case ETrialTowerRunState::Intermission: return LOCTEXT("Cleared", "층 클리어 · 잠시 후 다음 층");
	case ETrialTowerRunState::Complete: return LOCTEXT("Complete", "3층 정복 · 시험 완료!");
	case ETrialTowerRunState::Error: return LOCTEXT("Retry", "전투를 시작하지 못했습니다. 다시 도전해 주세요.");
	case ETrialTowerRunState::Defeated: return LOCTEXT("Defeated", "쓰러졌습니다 · 다시 도전해 보세요");
	}
	return FText::GetEmpty();
}

void ATrialTowerEncounter::RefreshStatus()
{
	if (StatusWidget) { StatusWidget->Refresh(); }
}

float ATrialTowerEncounter::GetPlayerHealth() const
{
	const UPlayerCombatComponent* Combat = PlayerCombat.Get();
	return Combat ? Combat->GetHealth() : 0.0f;
}

float ATrialTowerEncounter::GetMaxPlayerHealth() const
{
	const UPlayerCombatComponent* Combat = PlayerCombat.Get();
	return Combat ? Combat->GetMaxHealth() : 100.0f;
}

bool ATrialTowerEncounter::IsPlayerInvulnerable() const
{
	const UPlayerCombatComponent* Combat = PlayerCombat.Get();
	return Combat && Combat->IsInvulnerable();
}

bool ATrialTowerEncounter::IsPlayerHitReacting() const
{
	const UPlayerCombatComponent* Combat = PlayerCombat.Get();
	return Combat && Combat->IsHitReacting();
}

void ATrialTowerEncounter::DefeatPlayer()
{
	if (bShuttingDown || RunState == ETrialTowerRunState::Defeated) { return; }
	RunState = ETrialTowerRunState::Defeated;
	ClearRunTimers();
	for (ATrialTowerMonster* Monster : GetActiveMonsters()) { Monster->StopCombat(); }
	RefreshStatus();
	UE_LOG(LogTemp, Display, TEXT("TrialTower player defeated floor=%d"), FloorNumber);
}

#undef LOCTEXT_NAMESPACE
