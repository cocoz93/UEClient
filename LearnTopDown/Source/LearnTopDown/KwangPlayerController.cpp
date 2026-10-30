#include "KwangPlayerController.h"

#include "AITypes.h"
#include "Camera/CameraComponent.h"
#include "Camera/PlayerCameraManager.h"
#include "Components/CapsuleComponent.h"
#include "Components/InputComponent.h"
#include "CharacterSkillComponent.h"
#include "CharacterSkillHUD.h"
#include "CountessSkillComponent.h"
#include "Engine/World.h"
#include "EngineUtils.h"
#include "GameFramework/CharacterMovementComponent.h"
#include "GameFramework/SpringArmComponent.h"
#include "HAL/IConsoleManager.h"
#include "InputCoreTypes.h"
#include "KwangTrainingDummy.h"
#include "SparrowCharacter.h"
#include "SparrowSkillComponent.h"
#include "TopDownCombatCharacter.h"
#include "PlayerCombatComponent.h"
#include "Navigation/PathFollowingComponent.h"
#include "NavigationSystem.h"

namespace
{
	TAutoConsoleVariable<int32> CVarTraceMoveInput(TEXT("Character.Input.TraceMove"), 0,
		TEXT("Trace pending movement input and navigation readiness."));

	UCameraComponent* FindCharacterCamera(ATopDownCombatCharacter* Character)
	{
		TInlineComponentArray<UCameraComponent*> Cameras(Character);
		for (UCameraComponent* Camera : Cameras)
		{
			if (Camera->IsActive())
			{
				return Camera;
			}
		}
		return Cameras.IsEmpty() ? nullptr : Cameras[0];
	}

	USpringArmComponent* CopyCharacterCamera(ATopDownCombatCharacter* Previous, ATopDownCombatCharacter* Next)
	{
		UCameraComponent* PreviousCamera = FindCharacterCamera(Previous);
		UCameraComponent* NextCamera = FindCharacterCamera(Next);
		if (!PreviousCamera || !NextCamera)
		{
			return nullptr;
		}
		USpringArmComponent* PreviousArm = Cast<USpringArmComponent>(PreviousCamera->GetAttachParent());
		USpringArmComponent* NextArm = Cast<USpringArmComponent>(NextCamera->GetAttachParent());
		if (PreviousArm && NextArm)
		{
			NextArm->SetAbsolute(PreviousArm->IsUsingAbsoluteLocation(), PreviousArm->IsUsingAbsoluteRotation(),
				PreviousArm->IsUsingAbsoluteScale());
			NextArm->SetRelativeTransform(PreviousArm->GetRelativeTransform());
			// 발 위치는 유지하되 캡슐 높이가 다르면 카메라 피벗의 월드 높이는 기존 시점에 맞춘다.
			NextArm->SetWorldLocation(PreviousArm->GetComponentLocation(), false, nullptr, ETeleportType::TeleportPhysics);
			NextArm->TargetArmLength = PreviousArm->TargetArmLength;
			NextArm->SocketOffset = PreviousArm->SocketOffset;
			NextArm->TargetOffset = PreviousArm->TargetOffset;
			NextArm->ProbeSize = PreviousArm->ProbeSize;
			NextArm->ProbeChannel = PreviousArm->ProbeChannel;
			NextArm->bDoCollisionTest = PreviousArm->bDoCollisionTest;
			NextArm->bUsePawnControlRotation = PreviousArm->bUsePawnControlRotation;
			NextArm->bInheritPitch = PreviousArm->bInheritPitch;
			NextArm->bInheritYaw = PreviousArm->bInheritYaw;
			NextArm->bInheritRoll = PreviousArm->bInheritRoll;
			NextArm->bEnableCameraLag = PreviousArm->bEnableCameraLag;
			NextArm->bEnableCameraRotationLag = PreviousArm->bEnableCameraRotationLag;
			NextArm->bUseCameraLagSubstepping = PreviousArm->bUseCameraLagSubstepping;
			NextArm->bDrawDebugLagMarkers = PreviousArm->bDrawDebugLagMarkers;
			NextArm->CameraLagSpeed = PreviousArm->CameraLagSpeed;
			NextArm->CameraRotationLagSpeed = PreviousArm->CameraRotationLagSpeed;
			NextArm->CameraLagMaxTimeStep = PreviousArm->CameraLagMaxTimeStep;
			NextArm->CameraLagMaxDistance = PreviousArm->CameraLagMaxDistance;
			// UE 5.8 공개 지연 상태를 이어받아 시작 직후·이동 중에도 기존 보간을 연속적으로 유지한다.
			NextArm->PreviousDesiredLoc = PreviousArm->PreviousDesiredLoc;
			NextArm->PreviousArmOrigin = PreviousArm->PreviousArmOrigin;
			NextArm->PreviousDesiredRot = PreviousArm->PreviousDesiredRot;
			NextArm->bClampToMaxPhysicsDeltaTime = PreviousArm->bClampToMaxPhysicsDeltaTime;
		}
		NextCamera->SetAbsolute(PreviousCamera->IsUsingAbsoluteLocation(), PreviousCamera->IsUsingAbsoluteRotation(),
			PreviousCamera->IsUsingAbsoluteScale());
		NextCamera->SetRelativeTransform(PreviousCamera->GetRelativeTransform());
		NextCamera->FieldOfView = PreviousCamera->FieldOfView;
		NextCamera->FirstPersonFieldOfView = PreviousCamera->FirstPersonFieldOfView;
		NextCamera->FirstPersonScale = PreviousCamera->FirstPersonScale;
		NextCamera->ProjectionMode = PreviousCamera->ProjectionMode;
		NextCamera->OrthoWidth = PreviousCamera->OrthoWidth;
		NextCamera->bAutoCalculateOrthoPlanes = PreviousCamera->bAutoCalculateOrthoPlanes;
		NextCamera->AutoPlaneShift = PreviousCamera->AutoPlaneShift;
		NextCamera->OrthoNearClipPlane = PreviousCamera->OrthoNearClipPlane;
		NextCamera->OrthoFarClipPlane = PreviousCamera->OrthoFarClipPlane;
		NextCamera->bUpdateOrthoPlanes = PreviousCamera->bUpdateOrthoPlanes;
		NextCamera->bUseCameraHeightAsViewTarget = PreviousCamera->bUseCameraHeightAsViewTarget;
		NextCamera->AspectRatio = PreviousCamera->AspectRatio;
		NextCamera->AspectRatioAxisConstraint = PreviousCamera->AspectRatioAxisConstraint;
		NextCamera->bConstrainAspectRatio = PreviousCamera->bConstrainAspectRatio;
		NextCamera->bOverrideAspectRatioAxisConstraint = PreviousCamera->bOverrideAspectRatioAxisConstraint;
		NextCamera->bUseFieldOfViewForLOD = PreviousCamera->bUseFieldOfViewForLOD;
		NextCamera->Overscan = PreviousCamera->Overscan;
		NextCamera->SetAsymmetricOverscan(PreviousCamera->AsymmetricOverscan);
		NextCamera->bScaleResolutionWithOverscan = PreviousCamera->bScaleResolutionWithOverscan;
		NextCamera->bCropOverscan = PreviousCamera->bCropOverscan;
		NextCamera->bLockToHmd = PreviousCamera->bLockToHmd;
		NextCamera->bUsePawnControlRotation = PreviousCamera->bUsePawnControlRotation;
		NextCamera->bEnableFirstPersonFieldOfView = PreviousCamera->bEnableFirstPersonFieldOfView;
		NextCamera->bEnableFirstPersonScale = PreviousCamera->bEnableFirstPersonScale;
		NextCamera->PostProcessBlendWeight = PreviousCamera->PostProcessBlendWeight;
		NextCamera->PostProcessSettings = PreviousCamera->PostProcessSettings;
		FTransform AdditiveOffset;
		float AdditiveFOV = 0.0f;
		PreviousCamera->GetAdditiveOffset(AdditiveOffset, AdditiveFOV);
		NextCamera->ClearAdditiveOffset();
		if (!AdditiveOffset.Equals(FTransform::Identity) || !FMath::IsNearlyZero(AdditiveFOV))
		{
			NextCamera->AddAdditiveOffset(AdditiveOffset, AdditiveFOV);
		}
		TArray<FPostProcessSettings> PostProcessBlends;
		TArray<float> BlendWeights;
		PreviousCamera->GetExtraPostProcessBlends(PostProcessBlends, BlendWeights);
		NextCamera->ClearExtraPostProcessBlends();
		for (int32 Index = 0; Index < PostProcessBlends.Num() && Index < BlendWeights.Num(); ++Index)
		{
			NextCamera->AddExtraPostProcessBlend(PostProcessBlends[Index], BlendWeights[Index]);
		}
		NextCamera->SetActive(PreviousCamera->IsActive());
		return NextArm;
	}

}

AKwangPlayerController::AKwangPlayerController()
{
	bShowMouseCursor = true;
	DefaultMouseCursor = EMouseCursor::Default;
	PathFollowingComponent = CreateDefaultSubobject<UPathFollowingComponent>(TEXT("PathFollowingComponent"));
	PlayerCombat = CreateDefaultSubobject<UPlayerCombatComponent>(TEXT("PlayerCombat"));
}

void AKwangPlayerController::BeginPlay()
{
	Super::BeginPlay();
	FInputModeGameAndUI InputMode;
	InputMode.SetHideCursorDuringCapture(false);
	InputMode.SetLockMouseToViewportBehavior(EMouseLockMode::DoNotLock);
	SetInputMode(InputMode);
	ClientSetHUD(ACharacterSkillHUD::StaticClass());
}

void AKwangPlayerController::SetupInputComponent()
{
	Super::SetupInputComponent();
	if (InputComponent && IsLocalPlayerController())
	{
		InputComponent->BindKey(EKeys::AnyKey, IE_Pressed, this,
			&AKwangPlayerController::InterruptIntroAnimation).bConsumeInput = false;
		InputComponent->BindKey(EKeys::RightMouseButton, IE_Pressed, this, &AKwangPlayerController::MovePressed);
		InputComponent->BindKey(EKeys::RightMouseButton, IE_Released, this, &AKwangPlayerController::MoveReleased);
		InputComponent->BindKey(EKeys::LeftMouseButton, IE_Pressed, this, &AKwangPlayerController::AttackPressed);
		InputComponent->BindKey(EKeys::LeftMouseButton, IE_Released, this, &AKwangPlayerController::AttackReleased);
		InputComponent->BindKey(EKeys::Q, IE_Pressed, this, &AKwangPlayerController::SkillQPressed);
		InputComponent->BindKey(EKeys::W, IE_Pressed, this, &AKwangPlayerController::SkillWPressed);
		InputComponent->BindKey(EKeys::E, IE_Pressed, this, &AKwangPlayerController::SkillEPressed);
		InputComponent->BindKey(EKeys::R, IE_Pressed, this, &AKwangPlayerController::SkillRPressed);
		// HUD 오른쪽 칸 A·S·D·F는 칸 번호 8..11이다(CharacterSkillHUD의 16칸 배열).
		InputComponent->BindKey(EKeys::A, IE_Pressed, this, &AKwangPlayerController::SkillAPressed);
		InputComponent->BindKey(EKeys::S, IE_Pressed, this, &AKwangPlayerController::SkillSPressed);
		InputComponent->BindKey(EKeys::D, IE_Pressed, this, &AKwangPlayerController::SkillDPressed);
		InputComponent->BindKey(EKeys::F, IE_Pressed, this, &AKwangPlayerController::SkillFPressed);
		InputComponent->BindKey(EKeys::V, IE_Pressed, this, &AKwangPlayerController::SkillVPressed);
		InputComponent->BindKey(EKeys::SpaceBar, IE_Pressed, this, &AKwangPlayerController::SkillSpacePressed);
		InputComponent->BindKey(EKeys::One, IE_Pressed, this, &AKwangPlayerController::SelectCountess);
		InputComponent->BindKey(EKeys::Two, IE_Pressed, this, &AKwangPlayerController::SelectSparrow);
		InputComponent->BindKey(EKeys::Three, IE_Pressed, this, &AKwangPlayerController::SelectGideon);
		InputComponent->BindKey(EKeys::Four, IE_Pressed, this, &AKwangPlayerController::SelectAurora);
	}
}

void AKwangPlayerController::InterruptIntroAnimation()
{
	if (ATopDownCombatCharacter* ControlledCharacter = Cast<ATopDownCombatCharacter>(GetPawn()))
	{
		ControlledCharacter->InterruptIntroAnimation();
	}
}

void AKwangPlayerController::MovePressed()
{
	InterruptIntroAnimation();
	ClearHeldAttackInput();
	ClearPendingMoveInput();
	bMoveHeld = true;
	MoveRefreshTime = 0.0f;
	TraceMovementInput(TEXT("Press"));
	MoveToCursor();
}

void AKwangPlayerController::MoveReleased()
{
	bMoveHeld = false;
	TraceMovementInput(TEXT("Release"));
}

void AKwangPlayerController::SetPawn(APawn* InPawn)
{
	if (InPawn != GetPawn())
	{
		// 물리 버튼이 계속 눌려 있어도 새 직업이 이전 직업의 유지 공격을 이어받지 않는다.
		ClearHeldAttackInput();
		ClearPendingMoveInput();
		bMoveHeld = false;
		MoveRefreshTime = 0.0f;
	}
	Super::SetPawn(InPawn);
}

void AKwangPlayerController::FlushPressedKeys()
{
	ClearHeldAttackInput();
	ClearPendingMoveInput();
	bMoveHeld = false;
	MoveRefreshTime = 0.0f;
	Super::FlushPressedKeys();
}

void AKwangPlayerController::PlayerTick(float DeltaTime)
{
	Super::PlayerTick(DeltaTime);
	// 포커스를 잃어 키 해제 이벤트가 누락돼도 이동 입력을 붙잡지 않는다.
	if (bMoveHeld && !IsInputKeyDown(EKeys::RightMouseButton))
	{
		bMoveHeld = false;
	}
	if (bAttackHeld)
	{
		ATopDownCombatCharacter* ControlledCharacter = HeldAttackOwner.Get();
		if (!IsInputKeyDown(EKeys::LeftMouseButton) || !ControlledCharacter || GetPawn() != ControlledCharacter)
		{
			ClearHeldAttackInput();
		}
		else
		{
			FVector AimLocation;
			if (UpdateHeldAttackAim(AimLocation) && !ControlledCharacter->IsCombatBusy())
			{
				// 공격 중에는 다음 입력을 쌓지 않는다. 종료 뒤에는 기존 재시작 쿨타임을 그대로 검사한다.
				if (ControlledCharacter->TryBasicAttack(AimLocation) &&
					(Cast<ASparrowCharacter>(ControlledCharacter) || PendingMoveOwner.Get() == ControlledCharacter))
				{
					ClearPendingMoveInput();
					bMoveHeld = false;
					MoveRefreshTime = 0.0f;
				}
			}
		}
	}
	if (bMoveHeld)
	{
		MoveRefreshTime += DeltaTime;
		// 가까운 목표에 도착하기 전에 유지 입력을 갱신한다. 같은 목표는 경로를 재요청하지 않는다.
		constexpr float MoveRefreshInterval = 1.0f / 30.0f;
		if (MoveRefreshTime >= MoveRefreshInterval)
		{
			MoveRefreshTime = 0.0f;
			MoveToCursor(true);
		}
	}
	if (ATopDownCombatCharacter* PendingOwner = PendingMoveOwner.Get())
	{
		TraceMovementInput(TEXT("PendingTick"));
		if (PendingOwner == GetPawn())
		{
			if (USparrowSkillComponent* Skills = Cast<USparrowSkillComponent>(PendingOwner->GetSkills()))
			{
				Skills->FinishRecoveryForMovement();
			}
		}
		if (PendingOwner != GetPawn())
		{
			ClearPendingMoveInput();
		}
		else if (!PendingOwner->IsCombatBusy() && PathFollowingComponent->IsPathFollowingAllowed())
		{
			TraceMovementInput(TEXT("Consume"));
			// 우클릭을 먼저 떼더라도 후딜 중 마지막으로 지정한 지점까지 이동한다.
			const FVector Destination = PendingMoveDestination;
			const bool bContinuousInput = bPendingMoveContinuousInput;
			ClearPendingMoveInput();
			MoveToLocation(Destination, bContinuousInput);
		}
	}
}

void AKwangPlayerController::ClearPendingMoveInput()
{
	if (PendingMoveOwner.IsValid()) { TraceMovementInput(TEXT("Clear")); }
	PendingMoveOwner.Reset();
	PendingMoveDestination = FVector::ZeroVector;
	bPendingMoveContinuousInput = false;
}

void AKwangPlayerController::TraceMovementInput(const TCHAR* Event) const
{
	if (CVarTraceMoveInput.GetValueOnGameThread() == 0) { return; }
	const ATopDownCombatCharacter* ControlledCharacter = Cast<ATopDownCombatCharacter>(GetPawn());
	UE_LOG(LogTemp, Display, TEXT("TOPDOWN_MOVE_INPUT event=%s t=%.3f busy=%d pending=%s goal=%s held=%d pathAllowed=%d path=%s"),
		Event, GetWorld() ? GetWorld()->GetTimeSeconds() : 0.0, ControlledCharacter && ControlledCharacter->IsCombatBusy(),
		*GetNameSafe(PendingMoveOwner.Get()), *PendingMoveDestination.ToCompactString(), bMoveHeld,
		PathFollowingComponent && PathFollowingComponent->IsPathFollowingAllowed(),
		PathFollowingComponent ? *PathFollowingComponent->GetStatusDesc() : TEXT("None"));
}

void AKwangPlayerController::MoveToCursor(bool bContinuousInput)
{
	TraceMovementInput(TEXT("MoveToCursor"));
	const ATopDownCombatCharacter* ControlledCharacter = Cast<ATopDownCombatCharacter>(GetPawn());
	const UCountessSkillComponent* CountessSkills = ControlledCharacter ? Cast<UCountessSkillComponent>(ControlledCharacter->GetSkills()) : nullptr;
	const bool bCanQueueMovement = Cast<ASparrowCharacter>(ControlledCharacter) ||
		(CountessSkills && (CountessSkills->IsBackstepping() || CountessSkills->IsReforgeCasting()));
	if (!ControlledCharacter || (ControlledCharacter->IsCombatBusy() && !bCanQueueMovement))
	{
		return;
	}
	FHitResult Hit;
	if (!GetHitResultUnderCursor(ECC_Visibility, true, Hit))
	{
		TraceMovementInput(TEXT("NoCursorHit"));
		return;
	}
	UNavigationSystemV1* Navigation = FNavigationSystem::GetCurrent<UNavigationSystemV1>(GetWorld());
	FNavLocation Destination;
	if (!Navigation || !Navigation->ProjectPointToNavigation(Hit.ImpactPoint, Destination,
		FVector(100.0f, 100.0f, 250.0f), &ControlledCharacter->GetNavAgentPropertiesRef()))
	{
		TraceMovementInput(TEXT("NoNavProjection"));
		return;
	}
	if (bCanQueueMovement &&
		(ControlledCharacter->IsCombatBusy() || !PathFollowingComponent->IsPathFollowingAllowed()))
	{
		// 궁수는 공격 동작을 끝내되 그 사이의 이동 클릭을 한 개만 보관한다.
		// Countess의 백스텝과 신규 시전도 같은 예약을 사용하며 기존 평타 입력은 유지한다.
		// 종료 블렌드의 루트 모션이 아직 경로 이동을 막는 프레임도 같은 요청으로 기다린다.
		PendingMoveOwner = Cast<ATopDownCombatCharacter>(GetPawn());
		PendingMoveDestination = Destination.Location;
		bPendingMoveContinuousInput = bContinuousInput;
		if (USparrowSkillComponent* Skills = Cast<USparrowSkillComponent>(ControlledCharacter->GetSkills()))
		{
			Skills->FinishRecoveryForMovement();
		}
		TraceMovementInput(TEXT("Queued"));
		return;
	}
	ClearPendingMoveInput();
	MoveToLocation(Destination.Location, bContinuousInput);
}

void AKwangPlayerController::MoveToLocation(const FVector& Destination, bool bContinuousInput)
{
	TraceMovementInput(TEXT("MoveToLocation"));
	const ATopDownCombatCharacter* ControlledCharacter = Cast<ATopDownCombatCharacter>(GetPawn());
	UNavigationSystemV1* Navigation = FNavigationSystem::GetCurrent<UNavigationSystemV1>(GetWorld());
	if (!ControlledCharacter || ControlledCharacter->IsCombatBusy() || !Navigation)
	{
		return;
	}
	if (!PathFollowingComponent->IsPathFollowingAllowed())
	{
		return;
	}

	const EPathFollowingStatus::Type MoveStatus = PathFollowingComponent->GetStatus();
	// 유지 입력은 발 가까이에서만 멈춘다. 이동 중의 작은 커서 흔들림은 정지로 해석하지 않는다.
	const EPathFollowingReachMode StopReachMode = bContinuousInput ?
		EPathFollowingReachMode::ExactLocation : EPathFollowingReachMode::OverlapAgent;
	const float StopAcceptanceRadius = bContinuousInput ? ControlledCharacter->GetSimpleCollisionRadius() * 0.75f :
		UPathFollowingComponent::DefaultAcceptanceRadius;
	if (PathFollowingComponent->HasReached(Destination, StopReachMode, StopAcceptanceRadius))
	{
		// 몸 바로 옆의 클릭은 한 번만 멈춘다. 정지 중에는 이동 요청을 다시 만들지 않는다.
		if (MoveStatus != EPathFollowingStatus::Idle)
		{
			StopMovement();
		}
		return;
	}

	// 도착 경계보다 재출발 경계를 넓혀 짧은 이동과 정지가 반복되는 것을 막는다.
	// 유지 입력의 재출발만 같은 ExactLocation 기준을 쓴다. 새 클릭은 위 도착 판정 밖이면 이동한다.
	constexpr float MoveRestartDistance = 25.0f;
	if (bContinuousInput && MoveStatus == EPathFollowingStatus::Idle && PathFollowingComponent->HasReached(
		Destination, StopReachMode, StopAcceptanceRadius + MoveRestartDistance))
	{
		return;
	}

	// 유효한 경로의 목표가 거의 같으면 현재 경로와 감속을 그대로 이어간다.
	constexpr float MoveGoalUpdateDistance = 10.0f;
	if (MoveStatus == EPathFollowingStatus::Moving && FVector::DistSquared(
		Destination, PathFollowingComponent->GetPathDestination()) <= FMath::Square(MoveGoalUpdateDistance))
	{
		return;
	}

	const FVector AgentNavLocation = GetNavAgentLocation();
	const ANavigationData* NavData = Navigation->GetNavDataForProps(GetNavAgentPropertiesRef(), AgentNavLocation);
	if (!NavData)
	{
		return;
	}
	const FPathFindingQuery Query(this, *NavData, AgentNavLocation, Destination);
	const FPathFindingResult Result = Navigation->FindPathSync(Query);
	if (!Result.IsSuccessful())
	{
		TraceMovementInput(TEXT("NoPath"));
		StopMovement();
		return;
	}

	// 입력의 근거리 제한과 경로의 도착 정밀도는 다르다. 감속 구간 안에서 이동을 끝낸다.
	FAIMoveRequest Request(Destination);
	Request.SetAcceptanceRadius(8.0f);
	Request.SetReachTestIncludesAgentRadius(false);
	Request.SetReachTestIncludesGoalRadius(false);
	PathFollowingComponent->RequestMove(Request, Result.Path);
	TraceMovementInput(TEXT("Requested"));
}

void AKwangPlayerController::AttackPressed()
{
	InterruptIntroAnimation();
	ClearHeldAttackInput();
	ATopDownCombatCharacter* ControlledCharacter = Cast<ATopDownCombatCharacter>(GetPawn());
	if (!ControlledCharacter)
	{
		return;
	}
	const bool bSparrow = Cast<ASparrowCharacter>(ControlledCharacter) != nullptr;
	const UCountessSkillComponent* CountessSkills = Cast<UCountessSkillComponent>(ControlledCharacter->GetSkills());
	const bool bPreservePendingMove = bSparrow || PendingMoveOwner.Get() == ControlledCharacter ||
		(CountessSkills && (CountessSkills->IsBackstepping() || CountessSkills->IsReforgeCasting()));
	if (!bPreservePendingMove)
	{
		ClearPendingMoveInput();
		bMoveHeld = false;
		MoveRefreshTime = 0.0f;
	}
	bAttackHeld = true;
	HeldAttackOwner = ControlledCharacter;
	FVector AimLocation;
	if (UpdateHeldAttackAim(AimLocation))
	{
		if (ControlledCharacter->TryBasicAttack(AimLocation) && bPreservePendingMove)
		{
			// 시전 중 거절된 평타 클릭은 이미 예약한 우클릭 이동을 지우지 않는다.
			ClearPendingMoveInput();
			bMoveHeld = false;
			MoveRefreshTime = 0.0f;
		}
	}
}

void AKwangPlayerController::AttackReleased()
{
	ClearHeldAttackInput();
}

void AKwangPlayerController::ClearHeldAttackInput()
{
	if (ATopDownCombatCharacter* PreviousOwner = HeldAttackOwner.Get())
	{
		PreviousOwner->SetHeldBasicAttackInput(false);
	}
	HeldAttackOwner.Reset();
	bAttackHeld = false;
}

bool AKwangPlayerController::UpdateHeldAttackAim(FVector& AimLocation)
{
	ATopDownCombatCharacter* ControlledCharacter = HeldAttackOwner.Get();
	if (!ControlledCharacter || GetPawn() != ControlledCharacter)
	{
		return false;
	}
	FHitResult Hit;
	const bool bHasAim = GetHitResultUnderCursor(ECC_Visibility, true, Hit);
	AimLocation = bHasAim ? Hit.ImpactPoint : FVector::ZeroVector;
	// 커서가 월드에서 벗어나면 이전 조준으로 계속 공격하지 않고 유효한 조준이 돌아올 때까지 기다린다.
	ControlledCharacter->SetHeldBasicAttackInput(bHasAim, AimLocation);
	return bHasAim;
}

void AKwangPlayerController::UseSkill(int32 Slot)
{
	InterruptIntroAnimation();
	ATopDownCombatCharacter* ControlledCharacter = Cast<ATopDownCombatCharacter>(GetPawn());
	if (!ControlledCharacter || !ControlledCharacter->GetSkills())
	{
		return;
	}
	UCharacterSkillComponent* Skills = ControlledCharacter->GetSkills();
	const ECharacterSkillTargeting Targeting = Skills->GetSkillTargeting(Slot);
	FHitResult Hit;
	bool bHit = false;
	if (Targeting == ECharacterSkillTargeting::Ground)
	{
		// 범위기는 오브젝트 중심으로 흡착하지 않고 커서 아래 지면을 선택한다.
		FVector RayOrigin, RayDirection;
		if (DeprojectMousePositionToWorld(RayOrigin, RayDirection))
		{
			FCollisionQueryParams Query(SCENE_QUERY_STAT(GroundSkillAim), true, ControlledCharacter);
			for (TActorIterator<APawn> It(GetWorld()); It; ++It) { Query.AddIgnoredActor(*It); }
			for (TActorIterator<AKwangTrainingDummy> It(GetWorld()); It; ++It) { Query.AddIgnoredActor(*It); }
			bHit = GetWorld()->LineTraceSingleByChannel(Hit, RayOrigin, RayOrigin + RayDirection * 100000.0f,
				ECC_Visibility, Query);
		}
		if (!bHit) { return; }
	}
	else { bHit = GetHitResultUnderCursor(ECC_Visibility, true, Hit); }
	const FVector Aim = bHit ? Hit.ImpactPoint : ControlledCharacter->GetActorLocation() + ControlledCharacter->GetActorForwardVector() * 300.0f;
	AActor* Target = bHit ? Hit.GetActor() : nullptr;
	if ((Targeting == ECharacterSkillTargeting::Actor) &&
		!Skills->IsSkillTargetValid(Slot, Target, ControlledCharacter))
	{
		// Pawn 캡슐이 Visibility를 무시해도 적을 선택한다. 시전자 자신은 제외하고 벽 검사는 스킬에서 수행한다.
		FVector RayOrigin, RayDirection;
		if (DeprojectMousePositionToWorld(RayOrigin, RayDirection))
		{
			FCollisionObjectQueryParams Objects;
			Objects.AddObjectTypesToQuery(ECC_Pawn);
			Objects.AddObjectTypesToQuery(ECC_WorldDynamic);
			FCollisionQueryParams Query(SCENE_QUERY_STAT(CountessSkillTarget), false, ControlledCharacter);
			TArray<FHitResult> Hits;
			GetWorld()->LineTraceMultiByObjectType(Hits, RayOrigin, RayOrigin + RayDirection * 100000.0f, Objects, Query);
			for (const FHitResult& Candidate : Hits)
			{
				if (Skills->IsSkillTargetValid(Slot, Candidate.GetActor(), ControlledCharacter))
				{
					Target = Candidate.GetActor();
					break;
				}
			}
		}
	}
	const FVector SkillAim = Targeting != ECharacterSkillTargeting::Ground &&
		Skills->IsSkillTargetValid(Slot, Target, ControlledCharacter) ? Target->GetActorLocation() : Aim;
	if (Skills->TryUseSkillSlot(Slot, SkillAim, Targeting == ECharacterSkillTargeting::Ground ? nullptr : Target))
	{
		TraceMovementInput(TEXT("SkillAccepted"));
		// 성공한 새 행동은 앞서 예약한 이동보다 우선한다. 시전 중 거절된 키는 이동을 지우지 않는다.
		ClearPendingMoveInput();
	}
}

void AKwangPlayerController::SkillQPressed() { UseSkill(0); }
void AKwangPlayerController::SkillWPressed() { UseSkill(1); }
void AKwangPlayerController::SkillEPressed() { UseSkill(2); }
void AKwangPlayerController::SkillRPressed() { UseSkill(3); }
void AKwangPlayerController::SkillAPressed() { UseSkill(8); }
void AKwangPlayerController::SkillSPressed() { UseSkill(9); }
void AKwangPlayerController::SkillDPressed() { UseSkill(10); }
void AKwangPlayerController::SkillFPressed() { UseSkill(11); }
// HUD 칸 번호 16·17. 이 칸을 안 쓰는 캐릭터는 스킬 쪽에서 "Unavailable"로 거절한다.
void AKwangPlayerController::SkillVPressed()
{
	UseSkill(16);
}
void AKwangPlayerController::SkillSpacePressed() { UseSkill(17); }

void AKwangPlayerController::SelectCountess()
{
	SwitchCharacter(TEXT("/Game/TopDown/Blueprints/BP_CountessCharacter.BP_CountessCharacter_C"));
}

void AKwangPlayerController::SelectSparrow()
{
	SwitchCharacter(TEXT("/Game/TopDown/Characters/Sparrow/BP_SparrowCharacter.BP_SparrowCharacter_C"));
}

void AKwangPlayerController::SelectGideon()
{
	// 블루프린트 없이 메시·애니·카메라를 C++ 생성자에서 정하는 시험용 몸이다.
	SwitchCharacter(TEXT("/Script/LearnTopDown.GideonCharacter"));
}

void AKwangPlayerController::SelectAurora()
{
	// Gideon과 같은 C++ 전용 몸이다.
	SwitchCharacter(TEXT("/Script/LearnTopDown.AuroraCharacter"));
}

void AKwangPlayerController::SwitchCharacter(const TCHAR* ClassPath)
{
	ATopDownCombatCharacter* Previous = Cast<ATopDownCombatCharacter>(GetPawn());
	if (!IsValid(Previous) || !GetWorld() || !Previous->GetCapsuleComponent())
	{
		return;
	}
	UClass* CharacterClass = LoadClass<ATopDownCombatCharacter>(nullptr, ClassPath);
	if (!CharacterClass || Previous->GetClass() == CharacterClass)
	{
		return;
	}
	const ATopDownCombatCharacter* DefaultCharacter = CharacterClass->GetDefaultObject<ATopDownCombatCharacter>();
	if (!DefaultCharacter || !DefaultCharacter->GetCapsuleComponent())
	{
		return;
	}
	const FVector Feet = Previous->GetActorLocation() -
		FVector(0.0f, 0.0f, Previous->GetCapsuleComponent()->GetScaledCapsuleHalfHeight());
	const FVector NextSpawnLocation = Feet +
		FVector(0.0f, 0.0f, DefaultCharacter->GetCapsuleComponent()->GetScaledCapsuleHalfHeight());
	const FRotator SpawnRotation(0.0f, Previous->GetActorRotation().Yaw, 0.0f);
	const FRotator SavedControlRotation = GetControlRotation();
	const FName SavedCameraMode = PlayerCameraManager ? PlayerCameraManager->CameraStyle : NAME_None;
	FActorSpawnParameters Parameters;
	// 기존 캐릭터를 보존한 채 생성하므로 겹친 캡슐 때문에 스폰 위치가 옆으로 밀리지 않게 한다.
	Parameters.SpawnCollisionHandlingOverride = ESpawnActorCollisionHandlingMethod::AlwaysSpawn;
	ATopDownCombatCharacter* Next = GetWorld()->SpawnActor<ATopDownCombatCharacter>(
		CharacterClass, NextSpawnLocation, SpawnRotation, Parameters);
	if (!IsValid(Next) || !Next->GetCapsuleComponent())
	{
		if (IsValid(Next))
		{
			Next->Destroy();
		}
		return;
	}
	// 같은 위치의 이전 캡슐이 최초 바닥 판정을 가로막지 않도록 전환 중에만 제외한다.
	Next->GetCapsuleComponent()->IgnoreActorWhenMoving(Previous, true);
	// 블루프린트 생성 시 실제 캡슐 크기를 바꾸더라도 기존 발 위치를 유지한다.
	Next->SetActorLocation(Feet + FVector(0.0f, 0.0f, Next->GetCapsuleComponent()->GetScaledCapsuleHalfHeight()),
		false, nullptr, ETeleportType::TeleportPhysics);
	USpringArmComponent* NextArm = CopyCharacterCamera(Previous, Next);
	StopMovement();
	Previous->GetCharacterMovement()->StopMovementImmediately();
	bMoveHeld = false;
	MoveRefreshTime = 0.0f;
	Possess(Next);
	if (GetPawn() != Next)
	{
		Next->GetCapsuleComponent()->IgnoreActorWhenMoving(Previous, false);
		Next->Destroy();
		if (IsValid(Previous) && GetPawn() != Previous)
		{
			Possess(Previous);
		}
		SetControlRotation(SavedControlRotation);
		if (PlayerCameraManager)
		{
			SetCameraMode(SavedCameraMode);
		}
		return;
	}
	SetControlRotation(SavedControlRotation);
	if (PlayerCameraManager)
	{
		SetCameraMode(SavedCameraMode);
	}
	// 이전 캐릭터의 EndPlay가 평타·스킬 타이머와 소유 FX를 정리한다.
	Previous->Destroy();
	Next->GetCapsuleComponent()->IgnoreActorWhenMoving(Previous, false);
	Next->InterruptIntroAnimation();
	if (NextArm)
	{
		// 이어받은 지연 상태에서 시간을 진행하지 않고 새 카메라 소켓을 구성한다.
		NextArm->TickComponent(0.0f, LEVELTICK_All, nullptr);
	}
	SetViewTarget(Next);
}
