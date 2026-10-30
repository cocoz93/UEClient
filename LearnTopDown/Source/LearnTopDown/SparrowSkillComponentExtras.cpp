#include "SparrowSkillComponent.h"

#include "Animation/AnimMontage.h"
#include "Animation/AnimSequence.h"
#include "Components/CapsuleComponent.h"
#include "Components/SkeletalMeshComponent.h"
#include "Components/StaticMeshComponent.h"
#include "Engine/SkeletalMesh.h"
#include "Engine/World.h"
#include "EngineUtils.h"
#include "GameFramework/CharacterMovementComponent.h"
#include "KwangTrainingDummy.h"
#include "Materials/MaterialInterface.h"
#include "Particles/ParticleSystemComponent.h"
#include "SparrowAscension.h"
#include "SparrowGatherShot.h"
#include "SparrowBowMuzzleStudy.h"
#include "SparrowFlameStudies.h"
#include "SparrowFeatherTrail.h"
#include "TopDownCombatCharacter.h"

namespace
{
	constexpr int32 FirstExtraSlot = 8;
	constexpr int32 ExtraSkillCount = 4;
	constexpr float GearSpeed = 160.0f;
	constexpr float AscensionSeconds = 40.0f;
	constexpr float AscensionActionTime = 0.52f;
	constexpr float AscensionRecoveryTime = 1.35f;
}

void USparrowSkillComponent::InitializeExtraSkills()
{
	// 순수 정의만 초기화한다. 과거 BP의 4칸을 이행할 때도 constructor-only asset 조회를 하지 않는다.
	ExtraSkills.SetNum(ExtraSkillCount);
	const TCHAR* Names[] = {TEXT("GearArrow"), TEXT("Ascension"), TEXT("GoldenPiercing"), TEXT("CrystalShot")};
	const float Damages[] = {90.0f, 0.0f, 65.0f, 80.0f};
	const float Cooldowns[] = {8.0f, 16.0f, 10.0f, 12.0f};
	const float Ranges[] = {1800.0f, 0.0f, 1500.0f, 1100.0f};
	const float Actions[] = {0.42f, AscensionActionTime, 0.52f, 0.50f};
	const float Recoveries[] = {0.90f, AscensionRecoveryTime, 0.74f, 0.72f};
	for (int32 Index = 0; Index < ExtraSkillCount; ++Index)
	{
		FSparrowSkillDefinition& Definition = ExtraSkills[Index];
		Definition = FSparrowSkillDefinition();
		Definition.Name = Names[Index];
		Definition.Damage = Damages[Index];
		Definition.Cooldown = Cooldowns[Index];
		Definition.Range = Ranges[Index];
		Definition.ActionTime = Actions[Index];
		Definition.RecoveryTime = Recoveries[Index];
		Definition.Animation = Index == 1 ? Skills[3].Animation : Skills[2].Animation;
	}
}

void USparrowSkillComponent::CreateExtraMontages()
{
	const bool bLegacyDefinitions = ExtraSkills.Num() == 4 &&
		ExtraSkills[0].Name == TEXT("RetreatShot") && ExtraSkills[1].Name == TEXT("RicochetArrow") &&
		ExtraSkills[2].Name == TEXT("AmbushArrow") && ExtraSkills[3].Name == TEXT("SkyfallSalvo");
	if (bLegacyDefinitions) { InitializeExtraSkills(); }
	// 기존 저장 BP의 A/V/D 정의를 보존하면서 새 F 슬롯을 확장한다.
	if (ExtraSkills.Num() == 3) { ExtraSkills.SetNum(ExtraSkillCount); }
	ExtraMontages.SetNum(ExtraSkillCount);
	const USkeletalMesh* Mesh = Character.IsValid() && Character->GetMesh() ? Character->GetMesh()->GetSkeletalMeshAsset() : nullptr;
	if (!Mesh || ExtraSkills.Num() != ExtraSkillCount) { return; }
	// 반려된 가로 활 시안을 철회한다. 저장 BP에 남은 가로 자세도 기존 Primary 발사로 복구한다.
	ExtraSkills[0].Animation = Skills[2].Animation;
	// 저장 BP에도 같은 변신 시전·회복 시간을 적용한다. 다른 추가 스킬의 타이밍은 유지한다.
	if (ExtraSkills[1].Name == TEXT("Ascension"))
	{
		ExtraSkills[1].ActionTime = AscensionActionTime;
		ExtraSkills[1].RecoveryTime = AscensionRecoveryTime;
	}
	// 저장된 설치 궁수 정의도 새 관통 사격으로 이행한다. V의 내부 슬롯9는 그대로다.
	ExtraSkills[2].Name = TEXT("GoldenPiercing");
	ExtraSkills[2].Damage = 65.0f;
	ExtraSkills[2].Range = 1500.0f;
	ExtraSkills[2].Cooldown = 10.0f;
	ExtraSkills[2].ActionTime = 0.52f;
	ExtraSkills[2].RecoveryTime = 0.74f;
	ExtraSkills[2].Animation = Skills[2].Animation;
	ExtraSkills[3].Name = TEXT("CrystalShot");
	ExtraSkills[3].Damage = 80.0f;
	ExtraSkills[3].Range = 1100.0f;
	ExtraSkills[3].Cooldown = 12.0f;
	ExtraSkills[3].ActionTime = 1.05f;
	ExtraSkills[3].RecoveryTime = 1.23f;
	ExtraSkills[3].Animation = Skills[2].Animation;
	for (int32 Index = 0; Index < ExtraSkillCount; ++Index)
	{
		UAnimSequence* Sequence = ExtraSkills[Index].Animation;
		if (!Sequence || Sequence->GetSkeleton() != Mesh->GetSkeleton()) { continue; }
		UAnimMontage* Montage = UAnimMontage::CreateSlotAnimationAsDynamicMontage(Sequence,
			Index == 1 ? FullBodySlot : FName(TEXT("SparrowUpperBody")),
			Index == 1 ? 0.16f : 0.06f, Index == 1 ? 0.24f : 0.12f, 1.0f, 1);
		if (!Montage) { continue; }
		FAnimTrack& Track = Montage->SlotAnimTracks[0].AnimTrack;
		Track.AnimSegments.Reset();
		const auto Add = [&Track, Sequence](float SourceStart, float SourceEnd, float Start, float Duration)
		{
			FAnimSegment Segment;
			Segment.SetAnimReference(Sequence);
			Segment.StartPos = Start;
			Segment.AnimStartTime = SourceStart;
			Segment.AnimEndTime = SourceEnd;
			Segment.AnimPlayRate = (SourceEnd - SourceStart) /
				(Duration * FMath::Max(FMath::Abs(Sequence->RateScale), 0.001f));
			Segment.LoopingCount = 1;
			Track.AnimSegments.Add(Segment);
		};
		const float Action = ExtraSkills[Index].ActionTime;
		const float Recovery = ExtraSkills[Index].RecoveryTime;
		if (Index != 1 && Sequence->GetPlayLength() >= 0.6f - KINDA_SMALL_NUMBER)
		{
			// 당긴 준비 자세에서 .05 원본 발사 시점을 Action에 맞추고 정방향 회복을 이어 간다.
			Add(0.33f, 0.45f, 0.0f, Action - 0.05f);
			Add(0.0f, 0.05f, Action - 0.05f, 0.05f);
			Add(0.05f, 0.60f, Action, Recovery - Action);
		}
		else { Add(0.0f, Sequence->GetPlayLength(), 0.0f, Recovery); }
		Montage->SetCompositeLength(Recovery);
		Montage->SetFlags(RF_Transient);
		ExtraMontages[Index] = Montage;
	}
}

const FSparrowSkillDefinition* USparrowSkillComponent::GetSlotDefinition(int32 Slot) const
{
	if (Skills.IsValidIndex(Slot)) { return &Skills[Slot]; }
	return Slot >= FirstExtraSlot && Slot < FirstExtraSlot + ExtraSkillCount && ExtraSkills.IsValidIndex(Slot - FirstExtraSlot) ?
		&ExtraSkills[Slot - FirstExtraSlot] : nullptr;
}

UAnimMontage* USparrowSkillComponent::GetSlotMontage(int32 Slot) const
{
	if (SkillMontages.IsValidIndex(Slot)) { return SkillMontages[Slot].Get(); }
	return Slot >= FirstExtraSlot && Slot < FirstExtraSlot + ExtraSkillCount && ExtraMontages.IsValidIndex(Slot - FirstExtraSlot) ?
		ExtraMontages[Slot - FirstExtraSlot].Get() : nullptr;
}

bool USparrowSkillComponent::FindExtraGround(const FVector& Aim, float Range, FVector& Ground, AActor* Target) const
{
	if (!GetWorld() || !Character.IsValid() || Aim.ContainsNaN() ||
		FVector::DistSquared2D(Aim, Character->GetActorLocation()) > FMath::Square(Range)) { return false; }
	FCollisionQueryParams Query(SCENE_QUERY_STAT(SparrowAscensionGround), false, Character.Get());
	for (TActorIterator<APawn> It(GetWorld()); It; ++It) { Query.AddIgnoredActor(*It); }
	for (TActorIterator<AKwangTrainingDummy> It(GetWorld()); It; ++It) { Query.AddIgnoredActor(*It); }
	if (IsValid(Target)) { Query.AddIgnoredActor(Target); }
	FHitResult Hit;
	if (!GetWorld()->LineTraceSingleByChannel(Hit, Aim + FVector(0.0f, 0.0f, 400.0f),
		Aim - FVector(0.0f, 0.0f, 600.0f), ECC_Visibility, Query) || Hit.ImpactNormal.Z < 0.65f) { return false; }
	const float FeetZ = Character->GetActorLocation().Z - Character->GetCapsuleComponent()->GetScaledCapsuleHalfHeight();
	Ground = Hit.ImpactPoint;
	return FMath::Abs(Ground.Z - FeetZ) <= 200.0f &&
		HasWorldLineOfSight(Character->GetActorLocation(), Ground + FVector(0.0f, 0.0f, 70.0f));
}

bool USparrowSkillComponent::FindMirrorLocations(const FVector& Facing, FVector& Left, FVector& Right) const
{
	if (!Character.IsValid()) { return false; }
	const FVector Side = FVector::CrossProduct(FVector::UpVector, Facing).GetSafeNormal2D();
	for (const FVector2D Offset : {FVector2D(130.0f, 165.0f), FVector2D(100.0f, 130.0f), FVector2D(80.0f, 100.0f)})
	{
		const FVector Origin = Character->GetActorLocation() - Facing * Offset.X;
		if (!FindExtraGround(Origin - Side * Offset.Y, 300.0f, Left) ||
			!FindExtraGround(Origin + Side * Offset.Y, 300.0f, Right)) { continue; }
		const float Height = Character->GetCapsuleComponent()->GetScaledCapsuleHalfHeight();
		Left.Z += Height;
		Right.Z += Height;
		return true;
	}
	return false;
}

bool USparrowSkillComponent::TryUseExtraSkill(int32 Slot, const FVector& AimLocation, AActor* Target)
{
	const FSparrowSkillDefinition* Definition = GetSlotDefinition(Slot);
	if (!Definition || !bEnabled || !GetWorld() || !Character.IsValid() ||
		!Character->GetCharacterMovement() || Character->GetCharacterMovement()->MovementMode != MOVE_Walking ||
		AimLocation.ContainsNaN() || !GetSlotMontage(Slot)) { return RejectInput(TEXT("Unavailable")); }
	if (IsCasting()) { return RejectInput(TEXT("Casting")); }
	if (GetSlotCooldownRemaining(Slot == 9 ? 16 : Slot) > 0.0f) { return RejectInput(TEXT("Cooldown")); }
	if (Slot == 9 && GetAscensionRemaining() > 0.0f) { return RejectInput(TEXT("Ascension is already active")); }
	const FVector Facing = (AimLocation - Character->GetActorLocation()).GetSafeNormal2D();
	if (Slot != 9 && Facing.IsNearlyZero()) { return RejectInput(TEXT("Choose a direction")); }
	return BeginSkill(Slot, Slot == 9 ? Character->GetActorLocation() : AimLocation);
}

void USparrowSkillComponent::PrepareExtraPresentation(int32 Slot, float ActionSeconds)
{
	if (!Character.IsValid() || !GetWorld()) { return; }
	if (Slot == 8)
	{
		if (UParticleSystemComponent* Effect = SpawnEffect(PrimaryMuzzle, GetArrowOrigin(), Character->GetActorRotation(),
			ActionSeconds + 0.05f, true, 0.45f, TEXT("BowEmitterSocket"))) { CastEffects.Add(Effect); }
	}
	else if (Slot == 10 || Slot == 11)
	{
		if (GatherShot.IsValid() && !GatherShot->HasReleased()) { GatherShot->Destroy(); }
		if (FlameStudy.IsValid() && !FlameStudy->HasReleased()) { FlameStudy->Destroy(); }
		FlameStudy.Reset();
		if (BowMuzzleStudy.IsValid()) { BowMuzzleStudy->Cancel(); }
		BowMuzzleStudy.Reset();
		FActorSpawnParameters Spawn;
		Spawn.Owner = Character.Get();
		Spawn.ObjectFlags |= RF_Transient;
		Spawn.SpawnCollisionHandlingOverride = ESpawnActorCollisionHandlingMethod::AlwaysSpawn;
		if (Slot == 10)
		{
			if (ASparrowBowMuzzleStudy::GetPreviewStyle() > 0)
			{
				ASparrowBowMuzzleStudy* Bow = GetWorld()->SpawnActor<ASparrowBowMuzzleStudy>(Character->GetActorLocation(), Character->GetActorRotation(), Spawn);
				if (Bow && Bow->Initialize(Character.Get(), CastAim, ActionSeconds))
				{
					BowMuzzleStudy = Bow;
					VisualProxies.Add(Bow);
					return;
				}
				if (Bow) { Bow->Destroy(); }
			}
			ASparrowFlameStudies* Study = GetWorld()->SpawnActor<ASparrowFlameStudies>(Character->GetActorLocation(), Character->GetActorRotation(), Spawn);
			if (Study && Study->InitializeDCharge(Character.Get(), CastAim, ActionSeconds))
			{
				FlameStudy = Study;
				VisualProxies.Add(Study);
				return;
			}
			if (Study) { Study->Destroy(); }
			return;
		}
		ASparrowGatherShot* Visual = GetWorld()->SpawnActor<ASparrowGatherShot>(Character->GetActorLocation(), Character->GetActorRotation(), Spawn);
		if (Visual && Visual->Initialize(Character.Get(), CastAim, Slot == 11, ActionSeconds))
		{
			GatherShot = Visual;
			VisualProxies.RemoveAll([](const TWeakObjectPtr<AActor>& Item) { return !Item.IsValid(); });
			VisualProxies.Add(Visual);
		}
		else if (Visual) { Visual->Destroy(); }
	}
}

ASparrowArrow* USparrowSkillComponent::SpawnAscensionArrow(const FVector& Origin, const FVector& Direction, float Damage, bool bGear, bool bAllowMirrors)
{
	if (!GetWorld() || !Character.IsValid() || Origin.ContainsNaN() || Direction.ContainsNaN() || Direction.IsNearlyZero()) { return nullptr; }
	const FTransform Transform(Direction.Rotation(), Origin);
	UClass* ArrowClass = bGear ? ASparrowGearArrow::StaticClass() : ASparrowArrow::StaticClass();
	ASparrowArrow* Arrow = GetWorld()->SpawnActorDeferred<ASparrowArrow>(ArrowClass, Transform,
		Character.Get(), Character.Get(), ESpawnActorCollisionHandlingMethod::AlwaysSpawn);
	if (!Arrow) { return nullptr; }
	Arrow->SetAppliesRelentlessBonus(false);
	Arrow->SetRecordsRelentless(bAllowMirrors);
	// 신규 화살만 명시적으로 금속 재질을 적용한다. 기존 QWER/평타의 메시 재질은 보존한다.
	if (UMaterialInterface* Gold = LoadObject<UMaterialInterface>(nullptr,
		TEXT("/Game/TopDown/Characters/Sparrow/Materials/M_SparrowAscensionGold.M_SparrowAscensionGold")))
	{
		TArray<UStaticMeshComponent*> Meshes;
		Arrow->GetComponents<UStaticMeshComponent>(Meshes);
		for (UStaticMeshComponent* Mesh : Meshes)
		{
			for (int32 Slot = 0; Slot < FMath::Max(1, Mesh->GetNumMaterials()); ++Slot) { Mesh->SetMaterial(Slot, Gold); }
		}
	}
	// 느린 깃털환 화살은 수평으로 진행해 관통 뒤에도 겨눈 바닥으로 내려가지 않는다.
	const FVector FlightDirection = bGear ? Direction.GetSafeNormal2D() : Direction.GetSafeNormal();
	Arrow->InitArrow(FlightDirection, Damage, 1800.0f, bGear ? GearSpeed : ArrowSpeed, bGear, false,
		bGear ? UltimateTrail.Get() : PrimaryTrail.Get(), bGear ? nullptr : PrimaryHit.Get(), bGear ? nullptr : PrimaryWorldHit.Get());
	Arrow->FinishSpawning(Transform);
	OwnedArrows.RemoveAll([](const TWeakObjectPtr<ASparrowArrow>& Item) { return !Item.IsValid(); });
	OwnedArrows.Add(Arrow);
	SpawnEffect(PrimaryMuzzle, Origin, Direction.Rotation(), 0.25f, false, bGear ? 1.0f : 0.65f);
	if (bAllowMirrors && bGear) { EchoAscensionArrow(FlightDirection, Damage); }
	return Arrow;
}

void USparrowSkillComponent::EchoArrowShot(const FVector& Direction, float Damage, float Range, float Speed,
	bool bPiercing, bool bPassesWorld, bool bUltimate, TSharedPtr<TSet<TWeakObjectPtr<AActor>>> VolleyHits)
{
	// D는 설치 궁수의 독립 평타만 사용한다. 기존 호출 계약은 남기되 본체 발사를 중복 복제하지 않는다.
}

void USparrowSkillComponent::EchoHail(const FVector& Location)
{
	// 설치 궁수는 Q의 광역 피해나 화살비를 추가 생성하지 않는다.
}

void USparrowSkillComponent::EchoAscensionArrow(const FVector& Direction, float Damage)
{
	// A의 독립 관통/피해와 설치 궁수의 평타를 분리한다.
}

float USparrowSkillComponent::GetMirrorRemaining() const
{
	float Remaining = 0.0f;
	for (const TWeakObjectPtr<ASparrowMirrorArcher>& Echo : ActiveMirrorArchers)
	{
		if (Echo.IsValid()) { Remaining = FMath::Max(Remaining, Echo->GetRemainingSeconds()); }
	}
	return Remaining;
}

void USparrowSkillComponent::ExecuteExtraAction(uint32 Generation)
{
	if (!Character.IsValid() || !GetWorld()) { return; }
	if (ActiveSkillIndex == 8)
	{
		ASparrowArrow* Arrow = SpawnAscensionArrow(GetArrowOrigin(), (CastAim - GetArrowOrigin()).GetSafeNormal(), ExtraSkills[0].Damage, true);
		UE_LOG(LogTemp, Display, TEXT("SPARROW_ASCENSION gear released=%d damage=90 speed=%.0f range=1800"), Arrow != nullptr, GearSpeed);
	}
	else if (ActiveSkillIndex == 9)
	{
		const FTransform Transform(Character->GetActorTransform());
		ASparrowAscensionWings* Form = GetWorld()->SpawnActorDeferred<ASparrowAscensionWings>(ASparrowAscensionWings::StaticClass(),
			Transform, Character.Get(), Character.Get(), ESpawnActorCollisionHandlingMethod::AlwaysSpawn);
		if (!Form) { return; }
		if (!Form->Initialize(Character.Get(), AscensionSeconds)) { Form->Destroy(); return; }
		Form->FinishSpawning(Transform);
		AscensionWings = Form;
		VisualProxies.RemoveAll([](const TWeakObjectPtr<AActor>& Item) { return !Item.IsValid(); });
		VisualProxies.Add(Form);
		if (ASparrowFlameStudies::GetVPreview() > 0)
		{
			FActorSpawnParameters Spawn;
			Spawn.Owner = Character.Get();
			Spawn.ObjectFlags |= RF_Transient;
			Spawn.SpawnCollisionHandlingOverride = ESpawnActorCollisionHandlingMethod::AlwaysSpawn;
			ASparrowFlameStudies* Study = GetWorld()->SpawnActor<ASparrowFlameStudies>(Character->GetActorLocation(), Character->GetActorRotation(), Spawn);
			if (Study && Study->InitializeV(Character.Get(), Form)) { VisualProxies.Add(Study); }
			else if (Study) { Study->Destroy(); }
		}
	}
	else if (ActiveSkillIndex == 10)
	{
		const FVector Direction = (CastAim - Character->GetActorLocation()).GetSafeNormal2D();
		ASparrowArrow* Arrow = SpawnArrow(Direction, ExtraSkills[2].Damage, ExtraSkills[2].Range, 6500.0f,
			true, false, false, false, nullptr, false);
		if (Arrow) { Arrow->EnablePiercingLance(45.0f); }
		if (BowMuzzleStudy.IsValid()) { if (Arrow) { BowMuzzleStudy->Release(); } else { BowMuzzleStudy->Cancel(); } }
		if (FlameStudy.IsValid()) { FlameStudy->Release(Arrow); }
		if (GatherShot.IsValid()) { GatherShot->Release(Arrow); }
		if (Arrow)
		{
			FActorSpawnParameters Spawn;
			Spawn.Owner = Character.Get();
			Spawn.ObjectFlags |= RF_Transient;
			Spawn.SpawnCollisionHandlingOverride = ESpawnActorCollisionHandlingMethod::AlwaysSpawn;
			ASparrowFeatherTrail* Feathers = GetWorld()->SpawnActor<ASparrowFeatherTrail>(Arrow->GetActorLocation(), Arrow->GetActorRotation(), Spawn);
			if (Feathers && Feathers->InitializeD(Arrow, GetAscensionRemaining() > 0.0f)) { VisualProxies.Add(Feathers); }
			else if (Feathers) { Feathers->Destroy(); }
		}
		UE_LOG(LogTemp, Display, TEXT("SPARROW_PIERCING released=%d damage=65 speed=6500 range=1500"), Arrow != nullptr);
	}
	else if (ActiveSkillIndex == 11)
	{
		const FVector Direction = (CastAim - Character->GetActorLocation()).GetSafeNormal2D();
		// 세 화살은 발사축에 수직인 삼각형을 유지한다. 공유 피해 집합으로 중첩 피해를 막는다.
		auto Hits = MakeShared<TSet<TWeakObjectPtr<AActor>>>();
		const bool bTriple = GetAscensionRemaining() > 0.0f;
		const FVector Center = GetArrowOrigin();
		const FVector Right = FVector::CrossProduct(FVector::UpVector, Direction);
		const FVector Offsets[] = {FVector::UpVector * 32.0f,
			-Right * 28.0f - FVector::UpVector * 16.0f, Right * 28.0f - FVector::UpVector * 16.0f};
		TArray<ASparrowArrow*> Released;
		for (int32 Index = 0; Index < (bTriple ? 3 : 1); ++Index)
		{
			const FVector Origin = Center + (bTriple ? Offsets[Index] : FVector::ZeroVector);
			ASparrowArrow* Arrow = SpawnArrow(Direction, ExtraSkills[3].Damage, ExtraSkills[3].Range, 5200.0f,
				true, false, false, false, &Origin, false, Hits);
			if (Arrow)
			{
				if (GatherShot.IsValid()) { GatherShot->PrepareArrowPresentation(Arrow); }
				Arrow->EnableCrystalArrowPresentation();
				Released.Add(Arrow);
			}
		}
		if (GatherShot.IsValid()) { GatherShot->ReleaseVolley(Released); }
		UE_LOG(LogTemp, Display, TEXT("SPARROW_CRYSTAL released=%d damage=80 speed=5200 range=1100"), Released.Num());
	}
}

float USparrowSkillComponent::GetAscensionRemaining() const
{
	return AscensionWings.IsValid() ? AscensionWings->GetRemainingSeconds() : 0.0f;
}

void USparrowSkillComponent::SpawnExtraArrowHitVisual(const FVector& Location, const FVector& Direction, bool bChain, int32 HitOrdinal)
{
	// 이전 opt-in 화살의 호출 계약만 남긴다. 제거한 퇴로/연쇄/덫/낙성 연출은 다시 생성하지 않는다.
}

void USparrowSkillComponent::CancelExtraCast()
{
	if (BowMuzzleStudy.IsValid()) { BowMuzzleStudy->Cancel(); }
	BowMuzzleStudy.Reset();
	if (FlameStudy.IsValid() && !FlameStudy->HasReleased()) { FlameStudy->Destroy(); }
	FlameStudy.Reset();
	if (GatherShot.IsValid() && !GatherShot->HasReleased()) { GatherShot->Destroy(); }
	GatherShot.Reset();
	for (const TWeakObjectPtr<ASparrowMirrorArcher>& Echo : PendingMirrorArchers)
	{
		if (Echo.IsValid() && !Echo->HasStartedVolley()) { Echo->Destroy(); }
	}
	PendingMirrorArchers.Reset();
}

void USparrowSkillComponent::CleanupExtraSkills()
{
	CancelExtraCast();
	for (const TWeakObjectPtr<ASparrowMirrorArcher>& Echo : ActiveMirrorArchers)
	{
		if (Echo.IsValid()) { Echo->Destroy(); }
	}
	ActiveMirrorArchers.Reset();
	if (AscensionWings.IsValid()) { AscensionWings->Destroy(); }
	AscensionWings.Reset();
}
