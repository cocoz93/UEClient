#include "SparrowCharacter.h"
#include "CharacterClothPresentation.h"
#include "Animation/AnimMontage.h"
#include "Animation/AnimSequence.h"

#include "ChaosCloth/ChaosClothConfig.h"
#include "ChaosCloth/ChaosClothingSimulationInteractor.h"
#include "ClothingAsset.h"
#include "ClothingSimulationInstance.h"
#include "ClothingSimulationInteractor.h"
#include "Camera/CameraComponent.h"
#include "Components/CapsuleComponent.h"
#include "Components/SkeletalMeshComponent.h"
#include "Components/WindDirectionalSourceComponent.h"
#include "Engine/World.h"
#include "Engine/SkeletalMesh.h"
#include "GameFramework/CharacterMovementComponent.h"
#include "GameFramework/Controller.h"
#include "GameFramework/SpringArmComponent.h"
#include "Navigation/PathFollowingComponent.h"
#include "PhysicsEngine/PhysicsAsset.h"
#include "PhysicsEngine/SkeletalBodySetup.h"
#include "Materials/MaterialInterface.h"
#include "Materials/MaterialInstanceDynamic.h"
#include "HAL/IConsoleManager.h"
#include "SparrowSkillComponent.h"
#include "SceneProxies/WindSourceSceneProxy.h"
#include "TimerManager.h"
#include "UObject/ConstructorHelpers.h"

namespace
{
	TAutoConsoleVariable<int32> CVarSparrowIvoryHood(
		TEXT("Sparrow.Appearance.IvoryHood"), 1,
		TEXT("Use the dedicated ivory cloth material on the original Rogue hood only at pawn spawn."));
	TAutoConsoleVariable<float> CVarSparrowAttackSpeed(
		TEXT("Sparrow.Attack.Speed"), 1.8f,
		TEXT("Bow basic-attack speed multiplier at pawn spawn, clamped to 0.5..2.0; skills retain their cast rates."));
	TAutoConsoleVariable<int32> CVarSparrowNaturalBasicAttack(
		TEXT("Sparrow.Attack.Natural"), 1,
		TEXT("Regular bow attack at pawn spawn: 0=original full-body, 1=upper-body draw then release."));
	TAutoConsoleVariable<int32> CVarSparrowHeldAim(
		TEXT("Sparrow.Attack.HeldAim"), 1,
		TEXT("Held bow aim at pawn spawn: 0=approved Natural baseline, 1=aimed upper-body bridge and forward reload."));
	TAutoConsoleVariable<int32> CVarSparrowClothPresentation(
		TEXT("Sparrow.Cloth.Presentation"), 1,
		TEXT("Rogue cape at pawn spawn: 0=stable baseline, 1=gentle horizontal flutter and softer damping."));
	TAutoConsoleVariable<float> CVarSparrowClothWindSpeed(
		TEXT("Sparrow.Cloth.WindSpeed"), 180.0f,
		TEXT("Rogue cape maximum target horizontal airflow at pawn spawn, clamped to 0..200 cm/s."));
	TAutoConsoleVariable<float> CVarSparrowClothDamping(
		TEXT("Sparrow.Cloth.Damping"), 0.08f,
		TEXT("Rogue cape global damping at pawn spawn, clamped to 0.06..0.15."));
	TAutoConsoleVariable<float> CVarSparrowClothLocalDamping(
		TEXT("Sparrow.Cloth.LocalDamping"), 0.12f,
		TEXT("Rogue cape local damping at pawn spawn, clamped to 0.10..0.25."));

	bool ConfigureSparrowCapePointWind(USkeletalMeshComponent* CharacterMesh, float WindSpeed)
	{
		AActor* Owner = CharacterMesh->GetOwner();
		if (!Owner || WindSpeed <= 0.0f)
		{
			return false;
		}
		const FName WindTag(TEXT("SparrowCapeWind"));
		UWindDirectionalSourceComponent* Wind = Owner->FindComponentByTag<UWindDirectionalSourceComponent>(WindTag);
		if (!Wind)
		{
			Wind = NewObject<UWindDirectionalSourceComponent>(Owner, TEXT("SparrowCapeWind"), RF_Transient);
			Owner->AddInstanceComponent(Wind);
			Wind->ComponentTags.Add(WindTag);
			Wind->SetupAttachment(CharacterMesh);
			// 메시의 -90도 회전 기준으로 캐릭터 앞 5 cm에 두어 바람이 뒤로 흐르게 한다.
			Wind->SetRelativeLocation(FVector(0.0f, 5.0f, 0.0f));
		}
		constexpr float WindRadius = 20.0f;
		constexpr float SourceOffset = 5.0f;
		constexpr float SourceFalloff = 1.0f - FMath::Square(SourceOffset / WindRadius);
		// Scene 바람은 m/s이며 Chaos가 cm 변환 100배, legacy 모델이 추가 25배를 적용한다.
		constexpr float LegacyWindScale = 100.0f * 25.0f;
		const float SourceSpeed = WindSpeed / (LegacyWindScale * SourceFalloff);
		Wind->SetWindType(EWindSourceType::Point);
		Wind->SetRadius(WindRadius);
		Wind->SetStrength(1.0f);
		Wind->SetSpeed(SourceSpeed);
		Wind->SetMinimumGustAmount(0.0f);
		Wind->SetMaximumGustAmount(0.0f);
		if (!Wind->IsRegistered())
		{
			Wind->RegisterComponent();
		}
		FWindData MeshWind;
		float MeshWeight = 0.0f;
		const bool bMeshInRange = Wind->GetWindParameters(CharacterMesh->GetComponentLocation(), MeshWind, MeshWeight);
		FWindData OutsideWind;
		float OutsideWeight = 0.0f;
		const bool bOutsideInRange = Wind->GetWindParameters(Wind->GetComponentLocation() + FVector(0.0f, 0.0f, WindRadius + 1.0f), OutsideWind, OutsideWeight);
		// GetWindForCloth는 난수 순서를 바꾸므로 호출하지 않고 공개 컴포넌트 API로만 확인한다.
		UE_LOG(LogTemp, Display, TEXT("SparrowCapePointWind registered=%d mesh_wind_enabled=%d radius_cm=%.3f offset_cm=%.3f source_speed_scene_m_s=%.9f mesh_query_in_range=%d mesh_query_weight=%.6f mesh_query_speed_scene_m_s=%.9f source_equivalent_legacy_cm_s=%.6f mesh_query_direction=(%.6f,%.6f,%.6f) outside_query_in_range=%d outside_query_weight=%.6f"),
			Wind->IsRegistered(), CharacterMesh->IsWindEnabled(), WindRadius, SourceOffset, SourceSpeed,
			bMeshInRange, MeshWeight, MeshWind.Speed, MeshWind.Speed * LegacyWindScale,
			MeshWind.Direction.X, MeshWind.Direction.Y, MeshWind.Direction.Z, bOutsideInRange, OutsideWeight);
		return Wind->IsRegistered() && CharacterMesh->IsWindEnabled() && bMeshInRange && MeshWeight > 0.0f;
	}

	void ConfigureSparrowCapeBodyCollisions(USkeletalMeshComponent* CharacterMesh, const USkeletalMesh* SourceMesh)
	{
		UPhysicsAsset* BodyPhysics = SourceMesh->GetPhysicsAsset();
		int32 ValidBodies = 0;
		int32 Spheres = 0;
		int32 Capsules = 0;
		if (BodyPhysics)
		{
			for (const USkeletalBodySetup* Body : BodyPhysics->SkeletalBodySetups)
			{
				if (Body && SourceMesh->GetRefSkeleton().FindBoneIndex(Body->BoneName) != INDEX_NONE)
				{
					++ValidBodies;
					Spheres += Body->AggGeom.SphereElems.Num();
					Capsules += Body->AggGeom.SphylElems.Num();
				}
			}
		}
		if (Spheres + Capsules == 0)
		{
			UE_LOG(LogTemp, Warning, TEXT("SparrowCapeBodyCollision skipped: mesh physics asset has no compatible sphere/capsule bodies; asset=%s"), *GetPathNameSafe(BodyPhysics));
			return;
		}
		// Chaos cloth는 cloth asset의 PhysicsAsset이 없을 때 mesh의 몸 충돌체를 자동으로 사용하지 않는다.
		// 공식 외부 충돌원 API로 자신의 기존 몸 충돌체를 본 위치에 맞춰 매 프레임 제공한다.
		CharacterMesh->AddClothCollisionSource(CharacterMesh, BodyPhysics);
		UE_LOG(LogTemp, Display, TEXT("SparrowCapeBodyCollision asset=%s compatible_bodies=%d spheres=%d capsules=%d registered_sources=%d self_source=1 original_assets_unchanged=1"),
			*BodyPhysics->GetPathName(), ValidBodies, Spheres, Capsules, CharacterMesh->GetClothCollisionSources().Num());
	}

	void ConfigureSparrowRogueCape(USkeletalMeshComponent* CharacterMesh)
	{
		const USkeletalMesh* SourceMesh = CharacterMesh ? CharacterMesh->GetSkeletalMeshAsset() : nullptr;
		if (!SourceMesh || SourceMesh->GetPathName() !=
			TEXT("/Game/ParagonSparrow/Characters/Heroes/Sparrow/Skins/Rogue/Meshes/Sparrow_Rogue.Sparrow_Rogue"))
		{
			return;
		}
		const int32 Presentation = FMath::Clamp(CVarSparrowClothPresentation.GetValueOnGameThread(), 0, 1);
		const float Damping = Presentation ? FMath::Clamp(CVarSparrowClothDamping.GetValueOnGameThread(), 0.06f, 0.15f) : 0.15f;
		const float LocalDamping = Presentation ? FMath::Clamp(CVarSparrowClothLocalDamping.GetValueOnGameThread(), 0.10f, 0.25f) : 0.25f;
		const float WindSpeed = Presentation ? FMath::Clamp(CVarSparrowClothWindSpeed.GetValueOnGameThread(), 0.0f, 200.0f) : 0.0f;
		for (const UClothingAssetBase* ClothingAsset : SourceMesh->GetMeshClothingAssets())
		{
			const UClothingAssetCommon* CommonAsset = Cast<UClothingAssetCommon>(ClothingAsset);
			if (!CommonAsset || CommonAsset->GetPathName() != SourceMesh->GetPathName() + TEXT(":Sparrow_Rogue_APEX"))
			{
				continue;
			}
			const UChaosClothConfig* SourceConfig = CommonAsset->GetClothConfig<UChaosClothConfig>();
			if (!SourceConfig)
			{
				UE_LOG(LogTemp, Warning, TEXT("SparrowCape skipped: no original Chaos cloth configuration for %s"), *CommonAsset->GetPathName());
				continue;
			}
			if (Presentation && !CommonAsset->PhysicsAsset)
			{
				ConfigureSparrowCapeBodyCollisions(CharacterMesh, SourceMesh);
			}
			const FVector2D Drag(SourceConfig->Drag.Low, SourceConfig->Drag.High);
			const FVector2D Lift(SourceConfig->Lift.Low, SourceConfig->Lift.High);
			const FVector2D OuterDrag(SourceConfig->OuterDrag.Low, SourceConfig->OuterDrag.High);
			const FVector2D OuterLift(SourceConfig->OuterLift.Low, SourceConfig->OuterLift.High);
			// 엔진의 원본 Chaos 설정은 공기 밀도 1.225 kg/m^3를 사용한다. SetWind는 kg/cm^3를 받는다.
			constexpr float SourceAirDensity = 1.225e-6f;
			for (const FClothingSimulationInstance& Instance : CharacterMesh->GetClothingSimulationInstances())
			{
				UClothingSimulationInteractor* Simulation = Instance.GetClothingSimulationInteractor();
				UChaosClothingInteractor* Cloth = Simulation ?
					Cast<UChaosClothingInteractor>(Simulation->GetClothingInteractor(CommonAsset->GetFName())) : nullptr;
				if (!Cloth)
				{
					continue;
				}
				bool bWindApplied = false;
				if (Presentation)
				{
					// 급회전 보호와 관성 제한은 유지하고 등록된 Rogue 망토 인스턴스만 부드럽게 한다.
					Cloth->SetVelocityScale(FVector(0.35f), 0.1f, 0.0f);
					Cloth->SetDamping(Damping, LocalDamping);
					// 정지 직전 빠르게 접근하는 몸 충돌체를 놓치지 않도록 기존 충돌체에만 여유와 CCD를 보탠다.
					const float CollisionThickness = FMath::Max(SourceConfig->CollisionThickness, 2.0f);
					Cloth->SetCollision(CollisionThickness, SourceConfig->FrictionCoefficient, true,
						SourceConfig->SelfCollisionThickness);
					UE_LOG(LogTemp, Display, TEXT("SparrowCapeCollision original_thickness_cm=%.6f queued_thickness_cm=%.6f original_ccd=%d queued_ccd=1 cloth_physics_asset_present=%d original_self_collision=%d self_collision_thickness_cm=%.6f original_anim_drive_stiffness=(%.6f,%.6f) original_anim_drive_damping=(%.6f,%.6f)"),
						SourceConfig->CollisionThickness, CollisionThickness, SourceConfig->bUseCCD,
						CommonAsset->PhysicsAsset != nullptr, SourceConfig->bUseSelfCollisions,
						SourceConfig->SelfCollisionThickness,
						SourceConfig->AnimDriveStiffness.Low, SourceConfig->AnimDriveStiffness.High,
						SourceConfig->AnimDriveDamping.Low, SourceConfig->AnimDriveDamping.High);
					if (!SourceConfig->bUsePointBasedWindModel)
					{
						// 원본 저항·양력 범위와 마스크는 보존한다. 바람에 수직 성분은 추가하지 않는다.
						Cloth->SetWind(Drag, Lift, SourceAirDensity, FVector(WindSpeed, 0.0f, 0.0f), OuterDrag, OuterLift);
						bWindApplied = true;
					}
					else
					{
						// 원본 legacy 바람 모델은 유지하고 이 캐릭터의 천 query점만 작은 점풍 범위에 둔다.
						bWindApplied = ConfigureSparrowCapePointWind(CharacterMesh, WindSpeed);
					}
				}
				UE_LOG(LogTemp, Display, TEXT("SparrowCape mode=%d asset=%s original_damping=(%.6f,%.6f) queued_damping=(%.6f,%.6f) drag=(%.6f,%.6f) lift=(%.6f,%.6f) outer_drag=(%.6f,%.6f) outer_lift=(%.6f,%.6f) outer_enabled=(%d,%d) legacy_wind=%d air_density_kg_cm3=%.9f requested_wind_speed_cm_s=%.3f wind_applied=%d"),
					Presentation, *CommonAsset->GetPathName(), SourceConfig->DampingCoefficient, SourceConfig->LocalDampingCoefficient,
					Damping, LocalDamping, Drag.X, Drag.Y, Lift.X, Lift.Y, OuterDrag.X, OuterDrag.Y, OuterLift.X, OuterLift.Y,
					SourceConfig->bEnableOuterDrag, SourceConfig->bEnableOuterLift, SourceConfig->bUsePointBasedWindModel,
					SourceAirDensity, WindSpeed, bWindApplied);
			}
		}
	}
}

ASparrowCharacter::ASparrowCharacter(const FObjectInitializer& ObjectInitializer)
	: Super(ObjectInitializer.SetDefaultSubobjectClass<USparrowSkillComponent>(SkillComponentName))
{
	GetCapsuleComponent()->InitCapsuleSize(42.0f, 96.0f);
	// 커서의 지면 선택이 캐릭터 자신에게 가로막히지 않도록 기존 필드 캐릭터와 맞춘다.
	GetCapsuleComponent()->SetCollisionResponseToChannel(ECC_Visibility, ECR_Ignore);
	GetMesh()->SetCollisionResponseToChannel(ECC_Visibility, ECR_Ignore);
	GetMesh()->SetRelativeLocation(FVector(0.0f, 0.0f, -90.0f));
	GetMesh()->SetRelativeRotation(FRotator(0.0f, -90.0f, 0.0f));

	UCharacterMovementComponent* Movement = GetCharacterMovement();
	Movement->MaxWalkSpeed = 600.0f;
	Movement->MaxAcceleration = 5000.0f;
	Movement->BrakingDecelerationWalking = 6000.0f;
	Movement->RotationRate = FRotator(0.0f, 720.0f, 0.0f);
	static ConstructorHelpers::FClassFinder<UAnimInstance> SmoothLocomotion(
		TEXT("/Game/TopDown/Characters/Sparrow/Animations/ABP_Sparrow_SmoothStop"));
	SmoothLocomotionClass = SmoothLocomotion.Class;
	static ConstructorHelpers::FClassFinder<UAnimInstance> NaturalAttack(
		TEXT("/Game/TopDown/Characters/Sparrow/Animations/ABP_Sparrow_BasicNatural"));
	NaturalBasicAttackClass = NaturalAttack.Class;
	static ConstructorHelpers::FObjectFinder<UAnimMontage> NaturalMontage(
		TEXT("/Game/TopDown/Characters/Sparrow/Animations/AM_Sparrow_PrimaryNatural.AM_Sparrow_PrimaryNatural"));
	NaturalBasicAttackMontage = NaturalMontage.Object;
	HeldAimAnimationClass = TSoftClassPtr<UAnimInstance>(FSoftObjectPath(
		TEXT("/Game/TopDown/Characters/Sparrow/Animations/ABP_Sparrow_HeldAim.ABP_Sparrow_HeldAim_C")));
	static ConstructorHelpers::FObjectFinder<UAnimSequence> HeldPrimary(
		TEXT("/Game/ParagonSparrow/Characters/Heroes/Sparrow/Animations/Primary_Fire_Fast.Primary_Fire_Fast"));
	static ConstructorHelpers::FObjectFinder<UAnimSequence> HeldInnerFire(
		TEXT("/Game/ParagonSparrow/Characters/Heroes/Sparrow/Animations/R_Ability_Fast_Fire.R_Ability_Fast_Fire"));
	static ConstructorHelpers::FObjectFinder<UAnimSequence> HeldReady(
		TEXT("/Game/ParagonSparrow/Characters/Heroes/Sparrow/Animations/idle.idle"));
	HeldPrimarySequence = HeldPrimary.Object;
	HeldInnerFireSequence = HeldInnerFire.Object;
	HeldReadySequence = HeldReady.Object;
	IvoryHoodMaterial = TSoftObjectPtr<UMaterialInterface>(FSoftObjectPath(
		TEXT("/Game/TopDown/Characters/Sparrow/Materials/MI_Sparrow_IvoryHood.MI_Sparrow_IvoryHood")));

	CameraBoom = CreateDefaultSubobject<USpringArmComponent>(TEXT("CameraBoom"));
	CameraBoom->SetupAttachment(RootComponent);
	CameraBoom->TargetArmLength = 2000.0f;
	CameraBoom->SetUsingAbsoluteRotation(true);
	// 기존 카운테스 필드의 실제 SpringArm/Camera 설정과 같은 시점을 사용한다.
	CameraBoom->SetRelativeRotation(FRotator(-50.0f, 45.0f, 0.0f));
	CameraBoom->bDoCollisionTest = false;
	CameraBoom->bEnableCameraLag = true;
	CameraBoom->CameraLagSpeed = 3.0f;
	TopDownCamera = CreateDefaultSubobject<UCameraComponent>(TEXT("TopDownCamera"));
	TopDownCamera->SetupAttachment(CameraBoom, USpringArmComponent::SocketName);
	TopDownCamera->bUsePawnControlRotation = false;
	TopDownCamera->SetFieldOfView(55.0f);
	TopDownCamera->OrthoWidth = 512.0f;
	TopDownCamera->OrthoNearClipPlane = 0.0f;
	TopDownCamera->bAutoCalculateOrthoPlanes = false;
}

USparrowSkillComponent* ASparrowCharacter::GetSparrowSkills() const
{
	return Cast<USparrowSkillComponent>(GetSkills());
}

bool ASparrowCharacter::ShouldUseCombatLocomotion(AActor* CharacterOwner)
{
	const ASparrowCharacter* Character = Cast<ASparrowCharacter>(CharacterOwner);
	if (!IsValid(Character))
	{
		return false;
	}
	const USparrowSkillComponent* Skills = Character->GetSparrowSkills();
	// 평타는 전용 상체 슬롯이 활을 올린다. 하체를 무장 자세로 다시 바꾸지 않는다.
	const bool bCombatPose = Character->bUseNaturalBasicAttack ?
		(Skills && Skills->IsCasting()) : Character->IsCombatBusy();
	return bCombatPose || (Skills && Skills->IsInnerFireActive());
}

float ASparrowCharacter::GetBasicAttackCycleSeconds() const
{
	const bool bUsesCombo = !ComboAttacks.IsEmpty();
	UAnimMontage* Configured = bUsesCombo ? ComboAttacks[0].Montage.Get() : BasicAttackMontage.Get();
	const UAnimMontage* Montage = GetBasicAttackMontage(Configured);
	const float PlayRate = bUsesCombo ? FMath::Max(ComboAttacks[0].PlayRate, 0.1f) : 1.0f;
	const float EffectiveRate = Montage ? PlayRate * Montage->RateScale : 0.0f;
	if (EffectiveRate <= 0.0f) { return 0.0f; }
	// 본체의 한 발 완료 시간과 재시작 대기를 그대로 읽는다. 공격 상태나 공속을 변경하지 않는다.
	return Montage->GetPlayLength() / EffectiveRate + (bUsesCombo ? FMath::Max(ComboRestartCooldown, 0.0f) : 0.0f);
}

void ASparrowCharacter::ExecuteBasicAttackHit()
{
	if (USparrowSkillComponent* Skills = GetSparrowSkills())
	{
		if (Skills->FireBasicAttackAt(GetActiveAttackAimLocation()))
		{
			bHeldAttackReady = HasHeldBasicAttackInput();
		}
	}
}

UAnimMontage* ASparrowCharacter::GetBasicAttackMontage(UAnimMontage* ConfiguredMontage) const
{
	const USparrowSkillComponent* Skills = GetSparrowSkills();
	UAnimMontage* UltimateMontage = Skills ? Skills->GetInnerFireAttackMontage() : nullptr;
	if (UltimateMontage)
	{
		// 첫 발과 연사 모두 같은 기울인 상체 모션을 써 전신/상체 슬롯이 번갈아 전환되지 않게 한다.
		return bUseHeldAimPresentation ?
			HeldInnerFireMontage.Get() : UltimateMontage;
	}
	if (bUseNaturalBasicAttack && ConfiguredMontage && ConfiguredMontage->GetPathName() ==
		TEXT("/Game/TopDown/Characters/Sparrow/Animations/AM_Sparrow_Primary.AM_Sparrow_Primary"))
	{
		return bUseHeldAimPresentation && bHeldAttackReady && HasHeldBasicAttackInput() ?
			HeldPrimaryMontage.Get() : NaturalBasicAttackMontage.Get();
	}
	return Super::GetBasicAttackMontage(ConfiguredMontage);
}

float ASparrowCharacter::GetBasicAttackHitDelay(UAnimMontage* Montage, float Duration, float HitFraction) const
{
	// 준비 0.2초 뒤 원본 발사 0.05초에 맞춘다. R 강화 사격은 기존 시점을 유지한다.
	return bUseNaturalBasicAttack && (Montage == NaturalBasicAttackMontage || Montage == HeldPrimaryMontage) ?
		Duration * 0.25f : Super::GetBasicAttackHitDelay(Montage, Duration, HitFraction);
}

bool ASparrowCharacter::ShouldHoldBowReady(AActor* CharacterOwner)
{
	const ASparrowCharacter* Character = Cast<ASparrowCharacter>(CharacterOwner);
	const USparrowSkillComponent* Skills = IsValid(Character) ? Character->GetSparrowSkills() : nullptr;
	// 버튼 해제는 다음 발만 막는다. 이미 시작한 발의 회복이 끝날 때까지 활의 base 자세를 보존한다.
	return Skills && Character->bUseHeldAimPresentation &&
		(Character->HasHeldBasicAttackInput() || Character->IsAttacking()) &&
		!Skills->IsCasting() && Character->GetCharacterMovement() &&
		Character->GetCharacterMovement()->MovementMode == MOVE_Walking;
}

bool ASparrowCharacter::ShouldHoldInnerFireReady(AActor* CharacterOwner)
{
	const ASparrowCharacter* Character = Cast<ASparrowCharacter>(CharacterOwner);
	return ShouldHoldBowReady(CharacterOwner) && Character->GetSparrowSkills()->IsInnerFireActive();
}

void ASparrowCharacter::Tick(float DeltaSeconds)
{
	Super::Tick(DeltaSeconds);
	const USparrowSkillComponent* Skills = GetSparrowSkills();
	if ((!HasHeldBasicAttackInput() && !IsAttacking()) || !Skills || Skills->IsCasting())
	{
		bHeldAttackReady = false;
	}
}

bool ASparrowCharacter::CreateHeldAttackMontages()
{
	if (!NaturalBasicAttackMontage || !HeldPrimarySequence || !HeldInnerFireSequence || !HeldReadySequence ||
		!GetMesh() || !GetMesh()->GetSkeletalMeshAsset())
	{
		return false;
	}
	const USkeleton* Skeleton = GetMesh()->GetSkeletalMeshAsset()->GetSkeleton();
	if (HeldPrimarySequence->GetSkeleton() != Skeleton || HeldInnerFireSequence->GetSkeleton() != Skeleton ||
		HeldReadySequence->GetSkeleton() != Skeleton || HeldPrimarySequence->GetPlayLength() < 0.6f - KINDA_SMALL_NUMBER ||
		HeldInnerFireSequence->GetPlayLength() < 0.6f - KINDA_SMALL_NUMBER)
	{
		return false;
	}
	HeldPrimaryMontage = DuplicateObject<UAnimMontage>(NaturalBasicAttackMontage, this, TEXT("HeldPrimary"));
	HeldInnerFireMontage = UAnimMontage::CreateSlotAnimationAsDynamicMontage(HeldInnerFireSequence,
		TEXT("SparrowUpperBody"), 0.06f, 0.12f, 1.0f, 1);
	if (!HeldPrimaryMontage || !HeldInnerFireMontage)
	{
		return false;
	}
	TArray<float> NotifyTimes;
	TArray<float> NotifyEndTimes;
	TArray<float> SectionTimes;
	for (const FAnimNotifyEvent& Notify : HeldPrimaryMontage->Notifies)
	{
		NotifyTimes.Add(Notify.GetTime());
		NotifyEndTimes.Add(Notify.EndLink.GetTime());
	}
	for (const FCompositeSection& Section : HeldPrimaryMontage->CompositeSections)
	{
		SectionTimes.Add(Section.GetTime());
	}
	const auto ResetMontage = [](UAnimMontage* Montage)
	{
		Montage->SetFlags(RF_Transient);
		Montage->ClearFlags(RF_Public | RF_Standalone);
		Montage->SlotAnimTracks[0].SlotName = TEXT("SparrowUpperBody");
		Montage->SlotAnimTracks[0].AnimTrack.AnimSegments.Reset();
	};
	const auto AddSegment = [](UAnimMontage* Montage, UAnimSequence* Sequence,
		float Start, float SourceStart, float SourceEnd, float Duration)
	{
		FAnimSegment Segment;
		Segment.SetAnimReference(Sequence);
		Segment.StartPos = Start;
		Segment.AnimStartTime = SourceStart;
		Segment.AnimEndTime = SourceEnd;
		Segment.AnimPlayRate = (SourceEnd - SourceStart) /
			(Duration * FMath::Max(FMath::Abs(Sequence->RateScale), 0.001f));
		Segment.LoopingCount = 1;
		Montage->SlotAnimTracks[0].AnimTrack.AnimSegments.Add(Segment);
	};
	ResetMontage(HeldPrimaryMontage);
	// 첫 발은 기존 당김 모션을 유지한다. 연속 발사는 활을 겨눈 준비 자세에서 정방향 재장전만 한다.
	AddSegment(HeldPrimaryMontage, HeldReadySequence, 0.0f, 0.0f, 0.2f, 0.2f);
	AddSegment(HeldPrimaryMontage, HeldPrimarySequence, 0.2f, 0.0f, 0.05f, 0.05f);
	AddSegment(HeldPrimaryMontage, HeldPrimarySequence, 0.25f, 0.05f, 0.6f, 0.75f);
	HeldPrimaryMontage->SetCompositeLength(1.0f);
	// 세그먼트 개수가 바뀌어도 SaveAttack/ResetCombo의 절대 시각과 재시작 쿨타임은 유지한다.
	for (int32 Index = 0; Index < HeldPrimaryMontage->Notifies.Num(); ++Index)
	{
		HeldPrimaryMontage->Notifies[Index].Link(HeldPrimaryMontage, NotifyTimes[Index], 0);
		HeldPrimaryMontage->Notifies[Index].EndLink.Link(HeldPrimaryMontage, NotifyEndTimes[Index], 0);
	}
	for (int32 Index = 0; Index < HeldPrimaryMontage->CompositeSections.Num(); ++Index)
	{
		HeldPrimaryMontage->CompositeSections[Index].Link(HeldPrimaryMontage, SectionTimes[Index], 0);
	}
	// R도 원본의 기울인 빠른 재장전을 사용하되 기존 1초 길이와 .05 발사 시점은 보존한다.
	ResetMontage(HeldInnerFireMontage);
	AddSegment(HeldInnerFireMontage, HeldInnerFireSequence, 0.0f, 0.0f, 0.05f, 0.05f);
	AddSegment(HeldInnerFireMontage, HeldInnerFireSequence, 0.05f, 0.05f, 0.6f, 0.95f);
	HeldInnerFireMontage->SetCompositeLength(1.0f);
	HeldInnerFireMontage->RateScale = 1.5f;
	return true;
}

void ASparrowCharacter::BeginPlay()
{
	const float AttackSpeed = FMath::Clamp(CVarSparrowAttackSpeed.GetValueOnGameThread(), 0.5f, 2.0f);
	USkeletalMeshComponent* CharacterMesh = GetMesh();
	UClass* ConfiguredAnimClass = CharacterMesh ? CharacterMesh->GetAnimClass() : nullptr;
	// 기존 기본 AnimBP만 전용 보강본으로 바꾼다. 별도로 지정한 커스텀 자세는 보존한다.
	if (SmoothLocomotionClass && ConfiguredAnimClass && ConfiguredAnimClass->GetPathName() ==
		TEXT("/Game/TopDown/Characters/Sparrow/Animations/ABP_Sparrow_TopDown.ABP_Sparrow_TopDown_C"))
	{
		CharacterMesh->SetAnimInstanceClass(SmoothLocomotionClass.Get());
	}
	UClass* CurrentAnimClass = CharacterMesh ? CharacterMesh->GetAnimClass() : nullptr;
	if (CVarSparrowNaturalBasicAttack.GetValueOnGameThread() > 0 && NaturalBasicAttackClass &&
		NaturalBasicAttackMontage && CurrentAnimClass == SmoothLocomotionClass.Get())
	{
		CharacterMesh->SetAnimInstanceClass(NaturalBasicAttackClass.Get());
		bUseNaturalBasicAttack = true;
		// 원본 에셋을 보존하고 발사 전후 자세 전환 시간도 공속에 맞춘다.
		if (UAnimMontage* Presentation = DuplicateObject<UAnimMontage>(NaturalBasicAttackMontage, this,
			TEXT("AM_Sparrow_PrimaryNatural")))
		{
			Presentation->SetFlags(RF_Transient);
			Presentation->ClearFlags(RF_Public | RF_Standalone);
			Presentation->BlendIn.SetBlendTime(Presentation->BlendIn.GetBlendTime() / AttackSpeed);
			Presentation->BlendOut.SetBlendTime(Presentation->BlendOut.GetBlendTime() / AttackSpeed);
			NaturalBasicAttackMontage = Presentation;
		}
	}
	if (bUseNaturalBasicAttack && CVarSparrowHeldAim.GetValueOnGameThread() > 0 && CreateHeldAttackMontages())
	{
		HeldInnerFireMontage->BlendIn.SetBlendTime(HeldInnerFireMontage->BlendIn.GetBlendTime() / AttackSpeed);
		HeldInnerFireMontage->BlendOut.SetBlendTime(HeldInnerFireMontage->BlendOut.GetBlendTime() / AttackSpeed);
		if (UClass* HeldClass = HeldAimAnimationClass.LoadSynchronous())
		{
			CharacterMesh->SetAnimInstanceClass(HeldClass);
			bUseHeldAimPresentation = true;
		}
	}
	if (ComboAttacks.Num() == 1 && ComboAttacks[0].Montage && ComboAttacks[0].Montage->GetPathName() ==
		TEXT("/Game/TopDown/Characters/Sparrow/Animations/AM_Sparrow_Primary.AM_Sparrow_Primary"))
	{
		ComboAttacks[0].PlayRate *= AttackSpeed;
		// 한 발의 모션은 끝까지 재생하되 완료 후 같은 준비 자세로 멈춰 있는 시간은 줄인다.
		ComboRestartCooldown = FMath::Min(ComboRestartCooldown, 0.08f) / AttackSpeed;
	}
	Super::BeginPlay();
	if (CharacterMesh && CVarSparrowIvoryHood.GetValueOnGameThread() > 0)
	{
		const int32 HoodSlot = CharacterMesh->GetMaterialIndex(TEXT("M14_CloakHood"));
		UMaterialInterface* CurrentMaterial = HoodSlot != INDEX_NONE ? CharacterMesh->GetMaterial(HoodSlot) : nullptr;
		while (UMaterialInstanceDynamic* Dynamic = Cast<UMaterialInstanceDynamic>(CurrentMaterial))
		{
			CurrentMaterial = Dynamic->Parent;
		}
		// 후드의 기존 천·금속 마스크만 재사용하며 얼굴, 끈, 망토와 커스텀 재질은 보존한다.
		if (CurrentMaterial && CurrentMaterial->GetPathName() ==
			TEXT("/Game/ParagonSparrow/Characters/Heroes/Sparrow/Skins/Rogue/Materials/M_Sparrow_Rogue_Cloak.M_Sparrow_Rogue_Cloak"))
		{
			if (UMaterialInterface* HoodMaterial = IvoryHoodMaterial.LoadSynchronous())
			{
				CharacterMesh->SetMaterial(HoodSlot, HoodMaterial);
				UE_LOG(LogTemp, Display, TEXT("SparrowIvoryHood applied slot=%d material=%s"), HoodSlot, *HoodMaterial->GetPathName());
			}
			else
			{
				UE_LOG(LogTemp, Warning, TEXT("SparrowIvoryHood missing material: %s"), *IvoryHoodMaterial.ToSoftObjectPath().ToString());
			}
		}
	}
	ConfigureTopDownCloth(GetMesh(), true);
	ConfigureSparrowRogueCape(GetMesh());
	StartCapeFlutter();
}

void ASparrowCharacter::StartCapeFlutter()
{
	StopCapeFlutter();
	if (CVarSparrowClothPresentation.GetValueOnGameThread() <= 0)
	{
		return;
	}
	UWindDirectionalSourceComponent* Wind = FindComponentByTag<UWindDirectionalSourceComponent>(TEXT("SparrowCapeWind"));
	if (!Wind || !Wind->IsRegistered() || !GetMesh()->IsWindEnabled())
	{
		return;
	}
	CapeFlutterMaxSpeed = FMath::Clamp(CVarSparrowClothWindSpeed.GetValueOnGameThread(), 0.0f, 200.0f);
	if (CapeFlutterMaxSpeed <= 0.0f)
	{
		return;
	}
	CapeFlutterWind = Wind;
	CapeFlutterStartTime = GetWorld()->GetTimeSeconds();
	CapeFlutterLastUpdateTime = CapeFlutterStartTime;
	UpdateCapeFlutter();
	FTimerManagerTimerParameters TimerParameters;
	TimerParameters.bLoop = true;
	TimerParameters.bMaxOncePerFrame = true;
	TimerParameters.FirstDelay = 0.05f;
	GetWorldTimerManager().SetTimer(CapeFlutterTimer, this, &ASparrowCharacter::UpdateCapeFlutter, 0.05f, TimerParameters);
	FWindData InitialWind;
	float InitialWeight = 0.0f;
	Wind->GetWindParameters(GetMesh()->GetComponentLocation(), InitialWind, InitialWeight);
	UE_LOG(LogTemp, Display, TEXT("SparrowCapeFlutter start owner=%s start_time=%.6f max_wind_speed_cm_s=%.6f interval_seconds=0.050 initial_lateral_cm=%.6f initial_source_speed_scene_m_s=%.9f initial_source_equivalent_legacy_cm_s=%.6f max_once_per_frame=1"),
		*GetName(), CapeFlutterStartTime, CapeFlutterMaxSpeed, Wind->GetRelativeLocation().X, Wind->Speed, InitialWind.Speed * 100.0f * 25.0f);
}

void ASparrowCharacter::UpdateCapeFlutter()
{
	UWorld* World = GetWorld();
	UWindDirectionalSourceComponent* Wind = CapeFlutterWind.Get();
	USkeletalMeshComponent* CharacterMesh = GetMesh();
	if (!World || !Wind || !Wind->IsRegistered() || Wind->GetOwner() != this ||
		Wind->GetAttachParent() != CharacterMesh || !CharacterMesh || !CharacterMesh->IsWindEnabled())
	{
		StopCapeFlutter();
		return;
	}
	// 실제 게임 시간을 사용하므로 지연 프레임 뒤에도 누적 타이머 오차나 일괄 갱신이 없다.
	const double Now = static_cast<double>(World->GetTimeSeconds());
	const double Age = FMath::Max(0.0, Now - CapeFlutterStartTime);
	const float Elapsed = static_cast<float>(FMath::Max(0.0, Now - CapeFlutterLastUpdateTime));
	CapeFlutterLastUpdateTime = Now;
	const float MovementTarget = FMath::Clamp(GetVelocity().Size2D() /
		FMath::Max(GetCharacterMovement()->MaxWalkSpeed, 1.0f), 0.0f, 1.0f);
	// 이동·정지 경계에서 천에 힘이 갑자기 바뀌지 않도록 실제 속도를 완만하게 반영한다.
	CapeFlutterMovementBlend = FMath::Lerp(CapeFlutterMovementBlend, MovementTarget,
		1.0f - FMath::Exp(-Elapsed / 0.25f));
	constexpr double TwoPi = 2.0 * UE_DOUBLE_PI;
	const float IdleSpeed = static_cast<float>(110.0 + 50.0 * FMath::Sin(TwoPi * 0.65 * Age) +
		20.0 * FMath::Sin(TwoPi * 1.15 * Age + 0.8));
	// 이동 중 좌우 강제 흔들림은 없애고 원본 이동 관성에 완만한 저진폭 바람만 보탠다.
	const float MovingSpeed = static_cast<float>(110.0 + 14.0 * FMath::Sin(TwoPi * 0.37 * Age) +
		8.0 * FMath::Sin(TwoPi * 0.83 * Age + 0.9));
	const float TargetSpeed = FMath::Clamp(FMath::Lerp(IdleSpeed, MovingSpeed, CapeFlutterMovementBlend) *
		(CapeFlutterMaxSpeed / 180.0f), 0.0f, CapeFlutterMaxSpeed);
	const float IdleLateral = static_cast<float>(1.3 * FMath::Sin(TwoPi * 0.48 * Age) +
		0.7 * FMath::Sin(TwoPi * 0.83 * Age + 0.5));
	const float Lateral = FMath::Lerp(IdleLateral, 0.0f, CapeFlutterMovementBlend);
	// 앞 5 cm, 좌우 최대 2 cm와 반경 20 cm를 유지하고 거리 감쇠만 정확히 보정한다.
	const float Falloff = 1.0f - (25.0f + FMath::Square(Lateral)) / 400.0f;
	Wind->SetRelativeLocation(FVector(Lateral, 5.0f, 0.0f));
	Wind->SetSpeed(TargetSpeed / (100.0f * 25.0f * Falloff));
}

void ASparrowCharacter::StopCapeFlutter()
{
	const bool bWasRunning = CapeFlutterTimer.IsValid() || CapeFlutterWind.IsValid();
	UWorld* World = GetWorld();
	if (World)
	{
		World->GetTimerManager().ClearTimer(CapeFlutterTimer);
	}
	else
	{
		CapeFlutterTimer.Invalidate();
	}
	CapeFlutterWind.Reset();
	CapeFlutterMaxSpeed = 0.0f;
	CapeFlutterMovementBlend = 0.0f;
	CapeFlutterLastUpdateTime = 0.0;
	if (bWasRunning)
	{
		UE_LOG(LogTemp, Display, TEXT("SparrowCapeFlutter stop owner=%s time=%.6f active_timer_after_cleanup=%d"),
			*GetName(), World ? static_cast<double>(World->GetTimeSeconds()) : 0.0,
			World && World->GetTimerManager().IsTimerActive(CapeFlutterTimer));
	}
}

void ASparrowCharacter::NotifyControllerChanged()
{
	ClearStopHeading();
	if (UPathFollowingComponent* PreviousFollowing = StopHeadingPathFollowing.Get())
	{
		PreviousFollowing->OnRequestFinished.Remove(NavigationFinishedHandle);
	}
	StopHeadingPathFollowing.Reset();
	NavigationFinishedHandle.Reset();
	Super::NotifyControllerChanged();
	// PossessedBy 알림은 PlayerController::SetPawn보다 먼저 도착할 수 있다.
	if (Controller)
	{
		UPathFollowingComponent* Following = Controller->FindComponentByClass<UPathFollowingComponent>();
		if (Following)
		{
			StopHeadingPathFollowing = Following;
			NavigationFinishedHandle = Following->OnRequestFinished.AddUObject(this, &ASparrowCharacter::OnNavigationFinished);
		}
	}
}

void ASparrowCharacter::ClearStopHeading()
{
	OnCharacterMovementUpdated.RemoveDynamic(this, &ASparrowCharacter::FinishStopHeading);
	bFinishingStopHeading = false;
	StopHeadingDeadline = 0.0f;
}

void ASparrowCharacter::OnNavigationFinished(FAIRequestID RequestId, const FPathFollowingResult& Result)
{
	ClearStopHeading();
	const UCharacterMovementComponent* Movement = GetCharacterMovement();
	if (!RequestId.IsValid() || !Result.IsSuccess() || Result.IsInterrupted() ||
		Result.HasFlag(FPathFollowingResultFlags::AlreadyAtGoal) ||
		!Controller || Controller->GetPawn() != this || IsCombatBusy() ||
		Movement->MovementMode != MOVE_Walking || !Movement->bOrientRotationToMovement)
	{
		return;
	}
	const FVector Direction = GetVelocity().GetSafeNormal2D();
	if (Direction.IsNearlyZero())
	{
		return;
	}
	// 정상 도착 직후에만 짧게 남은 회전을 마친다. 새 이동과 중단은 이 예약을 재사용하지 않는다.
	StopHeadingYaw = Direction.Rotation().Yaw;
	StopHeadingDeadline = GetWorld()->GetTimeSeconds() + 0.18f;
	bFinishingStopHeading = true;
	OnCharacterMovementUpdated.AddUniqueDynamic(this, &ASparrowCharacter::FinishStopHeading);
}

void ASparrowCharacter::FinishStopHeading(float DeltaSeconds, FVector OldLocation, FVector OldVelocity)
{
	const UCharacterMovementComponent* Movement = GetCharacterMovement();
	const UPathFollowingComponent* Following = StopHeadingPathFollowing.Get();
	if (!bFinishingStopHeading || !Following || Following->GetStatus() != EPathFollowingStatus::Idle ||
		!Controller || Controller->GetPawn() != this || IsCombatBusy() ||
		Movement->MovementMode != MOVE_Walking || !Movement->bOrientRotationToMovement ||
		GetWorld()->GetTimeSeconds() > StopHeadingDeadline)
	{
		ClearStopHeading();
		return;
	}
	// 마지막 이동 프레임의 기본 회전은 CharacterMovement가 수행한다.
	if (!Movement->GetCurrentAcceleration().IsNearlyZero() || !Movement->GetLastUpdateRequestedVelocity().IsNearlyZero())
	{
		return;
	}
	const FRotator CurrentRotation = GetActorRotation();
	const float RemainingYaw = FMath::FindDeltaAngleDegrees(CurrentRotation.Yaw, StopHeadingYaw);
	if (FMath::Abs(RemainingYaw) > 30.0f || FMath::Abs(RemainingYaw) <= 0.01f)
	{
		ClearStopHeading();
		return;
	}
	const float YawStep = FMath::Max(Movement->RotationRate.Yaw, 0.0f) * FMath::Max(DeltaSeconds, 0.0f);
	SetActorRotation(FRotator(CurrentRotation.Pitch,
		FMath::FixedTurn(CurrentRotation.Yaw, StopHeadingYaw, YawStep), CurrentRotation.Roll));
	if (FMath::Abs(RemainingYaw) <= YawStep)
	{
		ClearStopHeading();
	}
}

void ASparrowCharacter::EndPlay(const EEndPlayReason::Type EndPlayReason)
{
	StopCapeFlutter();
	if (USkeletalMeshComponent* CharacterMesh = GetMesh())
	{
		if (const USkeletalMesh* CharacterAsset = CharacterMesh->GetSkeletalMeshAsset())
		{
			CharacterMesh->RemoveClothCollisionSource(CharacterMesh, CharacterAsset->GetPhysicsAsset());
		}
	}
	ClearStopHeading();
	if (UPathFollowingComponent* Following = StopHeadingPathFollowing.Get())
	{
		Following->OnRequestFinished.Remove(NavigationFinishedHandle);
	}
	StopHeadingPathFollowing.Reset();
	NavigationFinishedHandle.Reset();
	Super::EndPlay(EndPlayReason);
}
