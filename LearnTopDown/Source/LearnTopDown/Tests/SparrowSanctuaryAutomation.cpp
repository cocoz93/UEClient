#if WITH_EDITOR && WITH_DEV_AUTOMATION_TESTS

#include "CharacterPipelineQA.h"
#include "../SparrowArrow.h"
#include "../GideonProjectile.h"
#include "../SparrowSanctuary.h"
#include "../SparrowSkillComponent.h"
#include "../KwangTrainingDummy.h"
#include "AIController.h"
#include "Components/CapsuleComponent.h"
#include "Dom/JsonObject.h"
#include "Engine/World.h"
#include "EngineUtils.h"
#include "GameFramework/Character.h"
#include "GameFramework/CharacterMovementComponent.h"
#include "HAL/IConsoleManager.h"
#include "Kismet/GameplayStatics.h"
#include "Misc/FileHelper.h"
#include "Navigation/PathFollowingComponent.h"
#include "Particles/ParticleSystem.h"
#include "Serialization/JsonSerializer.h"
#include "UObject/StrongObjectPtr.h"

namespace
{
	struct FProbeProjectile
	{
		TStrongObjectPtr<ASparrowArrow> Arrow;
		TWeakObjectPtr<AGideonProjectile> Gideon;
	};
	TMap<FString, FProbeProjectile> ProbeProjectiles;
	bool ValidToken(const FString& Value)
	{
		return !Value.IsEmpty() && !Value.Contains(TEXT("/")) && !Value.Contains(TEXT("\\")) && !Value.Contains(TEXT(".."));
	}
	void WriteSanctuaryQA(const FString& Name, const TSharedRef<FJsonObject>& Json)
	{
		FString Text;
		FJsonSerializer::Serialize(Json, TJsonWriterFactory<>::Create(&Text));
		FFileHelper::SaveStringToFile(Text, *(CharacterPipelineQA::GetOutputDirectory(TEXT("QA/Sparrow")) / (Name + TEXT(".json"))),
			FFileHelper::EEncodingOptions::ForceUTF8WithoutBOM);
	}
}

// F의 입사광은 진짜 native projectile이며 damage/range/speed/Sweep를 우회하지 않는다.
static FAutoConsoleCommandWithWorldAndArgs LaunchSanctuaryQAProjectile(
	TEXT("SparrowSanctuaryQA.Launch"), TEXT("PIE: token shooter_actor_name x y z dx dy dz speed damage arrow|gideon"),
	FConsoleCommandWithWorldAndArgsDelegate::CreateLambda([](const TArray<FString>& Args, UWorld* World)
	{
		if (!World || World->WorldType != EWorldType::PIE || Args.Num() != 11 || !ValidToken(Args[0])) { return; }
		AActor* Shooter = nullptr;
		for (TActorIterator<AActor> It(World); It; ++It) { if (It->GetName() == Args[1]) { Shooter = *It; break; } }
		const FVector Location(FCString::Atod(*Args[2]), FCString::Atod(*Args[3]), FCString::Atod(*Args[4]));
		const FVector Direction = FVector(FCString::Atod(*Args[5]), FCString::Atod(*Args[6]), FCString::Atod(*Args[7])).GetSafeNormal();
		const float Speed = FCString::Atof(*Args[8]);
		const float Damage = FCString::Atof(*Args[9]);
		if (!IsValid(Shooter) || Location.ContainsNaN() || Direction.ContainsNaN() || Direction.IsNearlyZero() ||
			!FMath::IsFinite(Speed) || !FMath::IsFinite(Damage) || Speed <= 0.0f || Damage < 0.0f) { return; }
		UParticleSystem* Trail = LoadObject<UParticleSystem>(nullptr,
			TEXT("/Game/ParagonSparrow/FX/Particles/Sparrow/Abilities/Primary/FX/P_Sparrow_PrimaryAttack.P_Sparrow_PrimaryAttack"));
		UParticleSystem* WorldHit = LoadObject<UParticleSystem>(nullptr,
			TEXT("/Game/ParagonSparrow/FX/Particles/Sparrow/Abilities/Primary/FX/P_Sparrow_Primary_Ballistic_HitWorld.P_Sparrow_Primary_Ballistic_HitWorld"));
		const FTransform Transform(Direction.Rotation(), Location);
		AActor* Projectile = nullptr;
		if (Args[10] == TEXT("arrow"))
		{
			ASparrowArrow* Arrow = World->SpawnActorDeferred<ASparrowArrow>(ASparrowArrow::StaticClass(), Transform,
				Shooter, Cast<APawn>(Shooter), ESpawnActorCollisionHandlingMethod::AlwaysSpawn);
			if (Arrow)
			{
				Arrow->SetAppliesRelentlessBonus(false);
				Arrow->SetRecordsRelentless(false);
				Arrow->InitArrow(Direction, Damage, 1800.0f, Speed, false, false, Trail, nullptr, WorldHit);
				Arrow->FinishSpawning(Transform);
				Projectile = Arrow;
			}
		}
		else if (Args[10] == TEXT("gideon"))
		{
			AGideonProjectile* Gideon = World->SpawnActorDeferred<AGideonProjectile>(AGideonProjectile::StaticClass(), Transform,
				Shooter, Cast<APawn>(Shooter), ESpawnActorCollisionHandlingMethod::AlwaysSpawn);
			if (Gideon)
			{
				Gideon->Launch(EGideonProjectileKind::Primary, Direction, Speed, 1800.0f, Damage, Trail, nullptr, WorldHit, nullptr);
				Gideon->FinishSpawning(Transform);
				Projectile = Gideon;
			}
		}
		TSharedRef<FJsonObject> Json = MakeShared<FJsonObject>();
		Json->SetBoolField(TEXT("launched"), IsValid(Projectile));
		Json->SetStringField(TEXT("class"), Projectile ? Projectile->GetClass()->GetName() : TEXT(""));
		Json->SetStringField(TEXT("name"), GetNameSafe(Projectile));
		Json->SetStringField(TEXT("shooter"), Shooter->GetName());
		Json->SetNumberField(TEXT("speed"), Speed);
		Json->SetNumberField(TEXT("damage"), Damage);
		if (Projectile) { Projectile->Tags.Add(TEXT("SparrowSanctuaryQAProjectile")); Projectile->Tags.Add(*Args[0]); }
		FProbeProjectile& Record = ProbeProjectiles.FindOrAdd(Args[0]);
		Record.Arrow.Reset(Cast<ASparrowArrow>(Projectile));
		Record.Gideon = Cast<AGideonProjectile>(Projectile);
		WriteSanctuaryQA(Args[0], Json);
	}));

static FAutoConsoleCommandWithWorldAndArgs SnapshotSanctuaryQAProjectile(
	TEXT("SparrowSanctuaryQA.Shot"), TEXT("PIE: launch token; read the native arrow's preserved post-destruction hit count"),
	FConsoleCommandWithWorldAndArgsDelegate::CreateLambda([](const TArray<FString>& Args, UWorld* World)
	{
		if (!World || World->WorldType != EWorldType::PIE || Args.Num() != 1 || !ValidToken(Args[0])) { return; }
		FProbeProjectile* Record = ProbeProjectiles.Find(Args[0]);
		if (!Record) { return; }
		TSharedRef<FJsonObject> Json = MakeShared<FJsonObject>();
		Json->SetBoolField(TEXT("alive"), IsValid(Record->Arrow.Get()) || Record->Gideon.IsValid());
		if (Record->Arrow.Get())
		{
			Json->SetNumberField(TEXT("native_hit_count"), Record->Arrow->GetHitCount());
			Json->SetNumberField(TEXT("distance_travelled"), Record->Arrow->GetDistanceTravelled());
		}
		WriteSanctuaryQA(Args[0] + TEXT("_shot"), Json);
	}));

static FAutoConsoleCommandWithWorldAndArgs ResetSanctuaryQAProjectiles(
	TEXT("SparrowSanctuaryQA.Reset"), TEXT("PIE: destroy remaining probe projectiles and release test-only retained references"),
	FConsoleCommandWithWorldAndArgsDelegate::CreateLambda([](const TArray<FString>& Args, UWorld* World)
	{
		if (!World || World->WorldType != EWorldType::PIE || !Args.IsEmpty()) { return; }
		for (auto& Pair : ProbeProjectiles)
		{
			if (IsValid(Pair.Value.Arrow.Get())) { Pair.Value.Arrow->Destroy(); }
			if (Pair.Value.Gideon.IsValid()) { Pair.Value.Gideon->Destroy(); }
		}
		ProbeProjectiles.Reset();
	}));

// 이동 가능한 실제 ACharacter + AI PathFollowing을 만들며, 시각 허수아비와 구분해 기록한다.
static FAutoConsoleCommandWithWorldAndArgs CreateSanctuaryQAMovement(
	TEXT("SparrowSanctuaryQA.Movement"), TEXT("PIE: token x y z goal_x goal_y goal_z"),
	FConsoleCommandWithWorldAndArgsDelegate::CreateLambda([](const TArray<FString>& Args, UWorld* World)
	{
		if (!World || World->WorldType != EWorldType::PIE || Args.Num() != 7 || !ValidToken(Args[0])) { return; }
		const FVector Location(FCString::Atod(*Args[1]), FCString::Atod(*Args[2]), FCString::Atod(*Args[3]));
		const FVector Goal(FCString::Atod(*Args[4]), FCString::Atod(*Args[5]), FCString::Atod(*Args[6]));
		if (Location.ContainsNaN() || Goal.ContainsNaN()) { return; }
		FActorSpawnParameters Params;
		Params.SpawnCollisionHandlingOverride = ESpawnActorCollisionHandlingMethod::AlwaysSpawn;
		ACharacter* Character = World->SpawnActor<ACharacter>(ACharacter::StaticClass(), Location, FRotator::ZeroRotator, Params);
		AAIController* Controller = World->SpawnActor<AAIController>(AAIController::StaticClass(), Location, FRotator::ZeroRotator, Params);
		if (!Character || !Controller) { if (Character) { Character->Destroy(); } if (Controller) { Controller->Destroy(); } return; }
		Character->Tags.Add(TEXT("SparrowSanctuaryQAMovement"));
		Character->Tags.Add(*Args[0]);
		Controller->Tags.Add(TEXT("SparrowSanctuaryQAMovement"));
		Character->GetCharacterMovement()->MaxWalkSpeed = 80.0f;
		Character->GetCharacterMovement()->SetMovementMode(MOVE_Walking);
		Controller->Possess(Character);
		const EPathFollowingRequestResult::Type Result = Controller->MoveToLocation(Goal, 10.0f);
		TSharedRef<FJsonObject> Json = MakeShared<FJsonObject>();
		Json->SetStringField(TEXT("name"), Character->GetName());
		Json->SetNumberField(TEXT("movement_mode"), Character->GetCharacterMovement()->MovementMode);
		Json->SetBoolField(TEXT("tick_enabled"), Character->GetCharacterMovement()->IsComponentTickEnabled());
		Json->SetNumberField(TEXT("path_result"), Result);
		Json->SetNumberField(TEXT("path_status"), Controller->GetPathFollowingComponent()->GetStatus());
		Json->SetNumberField(TEXT("request_id"), Controller->GetPathFollowingComponent()->GetCurrentRequestId().GetID());
		WriteSanctuaryQA(Args[0], Json);
	}));

static FAutoConsoleCommandWithWorldAndArgs SnapshotSanctuaryQA(
	TEXT("SparrowSanctuaryQA.State"), TEXT("PIE: token"),
	FConsoleCommandWithWorldAndArgsDelegate::CreateLambda([](const TArray<FString>& Args, UWorld* World)
	{
		if (!World || World->WorldType != EWorldType::PIE || Args.Num() != 1 || !ValidToken(Args[0])) { return; }
		TSharedRef<FJsonObject> Json = MakeShared<FJsonObject>();
		TArray<TSharedPtr<FJsonValue>> Effects, Movement;
		const ACharacter* Player = UGameplayStatics::GetPlayerCharacter(World, 0);
		const USparrowSkillComponent* Skills = Player ? Player->FindComponentByClass<USparrowSkillComponent>() : nullptr;
		if (Skills)
		{
			Json->SetNumberField(TEXT("active_skill"), Skills->GetActiveSkillNumber());
			Json->SetNumberField(TEXT("cooldown_s"), Skills->GetSlotCooldownRemaining(9));
			Json->SetNumberField(TEXT("cooldown_f"), Skills->GetSlotCooldownRemaining(11));
			Json->SetNumberField(TEXT("cooldown_v"), Skills->GetSlotCooldownRemaining(16));
		}
		for (TActorIterator<ASparrowSanctuary> It(World); It; ++It)
		{
			TSharedRef<FJsonObject> Row = MakeShared<FJsonObject>();
			Row->SetStringField(TEXT("name"), It->GetName());
			Row->SetNumberField(TEXT("slot"), It->GetSlot());
			Row->SetBoolField(TEXT("committed"), It->HasCommitted());
			Row->SetBoolField(TEXT("casting"), It->IsCasting());
			Row->SetNumberField(TEXT("remaining"), It->GetRemainingSeconds());
			Row->SetNumberField(TEXT("blocked"), It->GetBlockedProjectileCount());
			Row->SetNumberField(TEXT("counters"), It->GetCounterShotCount());
			Effects.Add(MakeShared<FJsonValueObject>(Row));
		}
		for (TActorIterator<ACharacter> It(World); It; ++It)
		{
			if (!It->ActorHasTag(TEXT("SparrowSanctuaryQAMovement"))) { continue; }
			TSharedRef<FJsonObject> Row = MakeShared<FJsonObject>();
			Row->SetStringField(TEXT("name"), It->GetName());
			Row->SetNumberField(TEXT("mode"), It->GetCharacterMovement()->MovementMode);
			Row->SetNumberField(TEXT("custom_mode"), It->GetCharacterMovement()->CustomMovementMode);
			Row->SetBoolField(TEXT("tick_enabled"), It->GetCharacterMovement()->IsComponentTickEnabled());
			const AAIController* Controller = Cast<AAIController>(It->GetController());
			Row->SetNumberField(TEXT("path_status"), Controller ? Controller->GetPathFollowingComponent()->GetStatus() : -1);
			Row->SetNumberField(TEXT("request_id"), Controller ? Controller->GetPathFollowingComponent()->GetCurrentRequestId().GetID() : 0);
			Movement.Add(MakeShared<FJsonValueObject>(Row));
		}
		Json->SetArrayField(TEXT("effects"), Effects);
		Json->SetArrayField(TEXT("movement"), Movement);
		WriteSanctuaryQA(Args[0], Json);
	}));

static FAutoConsoleCommandWithWorldAndArgs CancelSanctuaryQACast(
	TEXT("SparrowSanctuaryQA.Cancel"), TEXT("PIE: cancel the current Sparrow cast through its real public skill contract"),
	FConsoleCommandWithWorldAndArgsDelegate::CreateLambda([](const TArray<FString>& Args, UWorld* World)
	{
		if (!World || World->WorldType != EWorldType::PIE || !Args.IsEmpty()) { return; }
		ACharacter* Player = UGameplayStatics::GetPlayerCharacter(World, 0);
		if (USparrowSkillComponent* Skills = Player ? Player->FindComponentByClass<USparrowSkillComponent>() : nullptr) { Skills->CancelSkill(); }
	}));

static FAutoConsoleCommandWithWorldAndArgs SetSanctuaryQAPreviousStatus(
	TEXT("SparrowSanctuaryQA.Status"), TEXT("PIE: dummy_actor_name status duration; prepare an actual pre-existing status"),
	FConsoleCommandWithWorldAndArgsDelegate::CreateLambda([](const TArray<FString>& Args, UWorld* World)
	{
		if (!World || World->WorldType != EWorldType::PIE || Args.Num() != 3) { return; }
		for (TActorIterator<AKwangTrainingDummy> It(World); It; ++It)
		{
			if (It->GetName() == Args[0]) { It->SetCombatStatus(*Args[1], FMath::Clamp(FCString::Atof(*Args[2]), 0.01f, 10.0f)); return; }
		}
	}));

#endif
