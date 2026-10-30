#if WITH_EDITOR && WITH_DEV_AUTOMATION_TESTS

#include "CharacterPipelineQA.h"

#include "Animation/AnimBlueprint.h"
#include "Animation/BlendSpace.h"
#include "Animation/AnimClassInterface.h"
#include "Animation/AnimInstance.h"
#include "Animation/AnimMontage.h"
#include "Animation/AnimNode_StateMachine.h"
#include "Animation/AnimStateMachineTypes.h"
#include "AnimStateNode.h"
#include "AnimStateTransitionNode.h"
#include "AnimGraphNode_BlendSpacePlayer.h"
#include "Components/SkeletalMeshComponent.h"
#include "Components/CapsuleComponent.h"
#include "Dom/JsonObject.h"
#include "Engine/GameViewportClient.h"
#include "Engine/LocalPlayer.h"
#include "Engine/World.h"
#include "GameFramework/Character.h"
#include "HAL/IConsoleManager.h"
#include "HAL/PlatformFileManager.h"
#include "InputKeyEventArgs.h"
#include "K2Node_CallFunction.h"
#include "K2Node_VariableGet.h"
#include "../KwangCharacter.h"
#include "Kismet2/BlueprintEditorUtils.h"
#include "Kismet/GameplayStatics.h"
#include "Kismet/KismetMathLibrary.h"
#include "Misc/FileHelper.h"
#include "Misc/Paths.h"
#include "NavigationSystem.h"
#include "Navigation/PathFollowingComponent.h"
#include "GameFramework/CharacterMovementComponent.h"
#include "Serialization/JsonSerializer.h"
#include "Slate/SceneViewport.h"

// 편집기의 연결 API로 전환 규칙을 보존하며 시작·정지 중간 상태를 우회한다.
static FAutoConsoleCommand ConfigureImmediateCountessLocomotion(
	TEXT("CountessInputQA.ConfigureLocomotion"), TEXT("Editor only: connect Idle and Run directly"),
	FConsoleCommandDelegate::CreateLambda([]()
	{
		UAnimBlueprint* Blueprint = LoadObject<UAnimBlueprint>(nullptr,
			TEXT("/Game/TopDown/Characters/Countess/Animations/ABP_Countess_TopDown.ABP_Countess_TopDown"));
		if (!Blueprint)
		{
			return;
		}
		const FString Graph = Blueprint->GetPathName() +
			TEXT(":AnimGraph.AnimGraphNode_StateMachine_5.Ground Locomotion.");
		UAnimStateNode* Idle = FindObject<UAnimStateNode>(nullptr, *(Graph + TEXT("AnimStateNode_1")));
		UAnimStateNode* Run = FindObject<UAnimStateNode>(nullptr, *(Graph + TEXT("AnimStateNode_2")));
		UAnimStateTransitionNode* Start = FindObject<UAnimStateTransitionNode>(nullptr,
			*(Graph + TEXT("AnimStateTransitionNode_1")));
		UAnimStateTransitionNode* Stop = FindObject<UAnimStateTransitionNode>(nullptr,
			*(Graph + TEXT("AnimStateTransitionNode_6")));
		if (!Idle || !Run || !Start || !Stop || Start->GetPreviousState() != Idle || Stop->GetPreviousState() != Run)
		{
			UE_LOG(LogTemp, Error, TEXT("Countess immediate locomotion nodes do not match the expected graph"));
			return;
		}
		Blueprint->Modify();
		Start->Modify();
		Stop->Modify();
		if (Start->GetNextState() != Run)
		{
			Start->RelinkHead(Run);
		}
		if (Stop->GetNextState() != Idle)
		{
			Stop->RelinkHead(Idle);
		}
		Start->CrossfadeDuration = 0.0f;
		Stop->CrossfadeDuration = 0.0f;
		FBlueprintEditorUtils::MarkBlueprintAsStructurallyModified(Blueprint);
		UE_LOG(LogTemp, Display, TEXT("COUNTESS_IMMEDIATE_LOCOMOTION_CONFIGURED"));
	}));

static FAutoConsoleCommand ConfigureCountessVelocityPredicate(
	TEXT("CountessInputQA.ConfigureVelocity"), TEXT("Editor only: raw|stable locomotion predicate"),
	FConsoleCommandWithArgsDelegate::CreateLambda([](const TArray<FString>& Args)
	{
		if (Args.Num() != 1 || (Args[0] != TEXT("raw") && Args[0] != TEXT("stable")))
		{
			return;
		}
		UAnimBlueprint* Blueprint = LoadObject<UAnimBlueprint>(nullptr,
			TEXT("/Game/TopDown/Characters/Countess/Animations/ABP_Countess_TopDown.ABP_Countess_TopDown"));
		UK2Node_CallFunction* Node = Blueprint ? FindObject<UK2Node_CallFunction>(nullptr,
			*(Blueprint->GetPathName() + TEXT(":EventGraph.K2Node_CallFunction_96"))) : nullptr;
		if (!Node)
		{
			return;
		}
		const bool bStable = Args[0] == TEXT("stable");
		UFunction* Function = bStable ? AKwangCharacter::StaticClass()->FindFunctionByName(TEXT("GetLocomotionAnimationVelocity")) :
			UCharacterMovementComponent::StaticClass()->FindFunctionByName(TEXT("GetLastUpdateVelocity"));
		if (!Function || Node->GetTargetFunction() == Function)
		{
			return;
		}
		UEdGraphPin* MovementPin = Node->FindPin(TEXT("Movement"));
		if (!MovementPin)
		{
			MovementPin = Node->FindPin(TEXT("self"));
		}
		UEdGraphPin* ReturnPin = Node->FindPin(TEXT("ReturnValue"));
		if (!MovementPin || MovementPin->LinkedTo.Num() != 1 || !ReturnPin)
		{
			UE_LOG(LogTemp, Error, TEXT("Countess movement predicate pins do not match the expected graph"));
			return;
		}
		UEdGraphPin* Source = MovementPin->LinkedTo[0];
		const TArray<UEdGraphPin*> Consumers = ReturnPin->LinkedTo;
		Blueprint->Modify();
		Node->Modify();
		MovementPin->BreakAllPinLinks();
		Node->SetFromFunction(Function);
		Node->ReconstructNode();
		const UEdGraphSchema* Schema = Node->GetSchema();
		check(Schema->TryCreateConnection(Source, Node->FindPinChecked(bStable ? TEXT("Movement") : TEXT("self"))));
		ReturnPin = Node->FindPinChecked(TEXT("ReturnValue"));
		for (UEdGraphPin* Consumer : Consumers)
		{
			if (!ReturnPin->LinkedTo.Contains(Consumer))
			{
				check(Schema->TryCreateConnection(ReturnPin, Consumer));
			}
		}
		for (int32 PinIndex = Node->Pins.Num() - 1; PinIndex >= 0; --PinIndex)
		{
			if (Node->Pins[PinIndex]->bOrphanedPin)
			{
				Node->RemovePin(Node->Pins[PinIndex]);
			}
		}
		FBlueprintEditorUtils::MarkBlueprintAsStructurallyModified(Blueprint);
		UE_LOG(LogTemp, Display, TEXT("COUNTESS_VELOCITY_PREDICATE %s"), *Args[0]);
	}));

// 실제 속도가 0이면 보행 주기도 멈춘다. 퇴장 중인 Run 포즈는 대기 자세로만 블렌드된다.
static FAutoConsoleCommand ConfigureCountessGaitRate(
	TEXT("CountessInputQA.ConfigureGaitRate"), TEXT("Editor only: drive Countess gait rate from actual speed"),
	FConsoleCommandDelegate::CreateLambda([]()
	{
		UAnimBlueprint* Blueprint = LoadObject<UAnimBlueprint>(nullptr,
			TEXT("/Game/TopDown/Characters/Countess/Animations/ABP_Countess_TopDown.ABP_Countess_TopDown"));
		UAnimGraphNode_BlendSpacePlayer* Player = Blueprint ? FindObject<UAnimGraphNode_BlendSpacePlayer>(nullptr,
			*(Blueprint->GetPathName() + TEXT(":AnimGraph.AnimGraphNode_StateMachine_5.Ground Locomotion.AnimStateNode_2.Run.AnimGraphNode_BlendSpacePlayer_2"))) : nullptr;
		if (!Player || !Player->Node.GetBlendSpace() || Player->Node.GetBlendSpace()->GetFName() != TEXT("JogFwdSlopeLean"))
		{
			UE_LOG(LogTemp, Error, TEXT("Countess Run player does not match the expected original blendspace"));
			return;
		}
		Blueprint->Modify();
		Player->Modify();
		UEdGraph* Graph = Player->GetGraph();
		Graph->Modify();
		for (int32 Index = 0; Index < Player->ShowPinForProperties.Num(); ++Index)
		{
			if (Player->ShowPinForProperties[Index].PropertyName == TEXT("PlayRate"))
			{
				Player->SetPinVisibility(true, Index);
				break;
			}
		}
		UEdGraphPin* RatePin = Player->FindPin(TEXT("PlayRate"));
		if (!RatePin || !RatePin->LinkedTo.IsEmpty())
		{
			UE_LOG(LogTemp, Error, TEXT("Countess Run rate is missing or already configured"));
			return;
		}
		UK2Node_VariableGet* Speed = NewObject<UK2Node_VariableGet>(Graph);
		Speed->VariableReference.SetSelfMember(TEXT("Speed"));
		Graph->AddNode(Speed, false, false);
		Speed->CreateNewGuid();
		Speed->PostPlacedNewNode();
		Speed->AllocateDefaultPins();
		Speed->NodePosX = Player->NodePosX - 480;
		Speed->NodePosY = Player->NodePosY + 180;
		UK2Node_CallFunction* Divide = NewObject<UK2Node_CallFunction>(Graph);
		Divide->SetFromFunction(UKismetMathLibrary::StaticClass()->FindFunctionByName(TEXT("Divide_DoubleDouble")));
		Graph->AddNode(Divide, false, false);
		Divide->CreateNewGuid();
		Divide->PostPlacedNewNode();
		Divide->AllocateDefaultPins();
		Divide->NodePosX = Player->NodePosX - 260;
		Divide->NodePosY = Player->NodePosY + 180;
		const UEdGraphSchema* Schema = Graph->GetSchema();
		Schema->TrySetDefaultValue(*Divide->FindPinChecked(TEXT("B")), TEXT("600.0"));
		check(Schema->TryCreateConnection(Speed->FindPinChecked(TEXT("Speed")), Divide->FindPinChecked(TEXT("A"))));
		check(Schema->TryCreateConnection(Divide->FindPinChecked(TEXT("ReturnValue")), RatePin));
		FBlueprintEditorUtils::MarkBlueprintAsStructurallyModified(Blueprint);
		UE_LOG(LogTemp, Display, TEXT("COUNTESS_SPEED_DRIVEN_GAIT_CONFIGURED"));
	}));

// 회전 반응을 두 배로 높여도 원본 보행의 기울기 입력은 같은 범위로 유지한다.
static FAutoConsoleCommand ConfigureCountessTurnLean(
	TEXT("CountessInputQA.ConfigureTurnLean"), TEXT("Editor only: scale original gait lean for 720 degree turns"),
	FConsoleCommandDelegate::CreateLambda([]()
	{
		UAnimBlueprint* Blueprint = LoadObject<UAnimBlueprint>(nullptr,
			TEXT("/Game/TopDown/Characters/Countess/Animations/ABP_Countess_TopDown.ABP_Countess_TopDown"));
		UAnimGraphNode_BlendSpacePlayer* Player = Blueprint ? FindObject<UAnimGraphNode_BlendSpacePlayer>(nullptr,
			*(Blueprint->GetPathName() + TEXT(":AnimGraph.AnimGraphNode_StateMachine_5.Ground Locomotion.AnimStateNode_2.Run.AnimGraphNode_BlendSpacePlayer_2"))) : nullptr;
		UK2Node_CallFunction* Scale = Player ? FindObject<UK2Node_CallFunction>(nullptr,
			*(Player->GetGraph()->GetPathName() + TEXT(".K2Node_CommutativeAssociativeBinaryOperator_79"))) : nullptr;
		UEdGraphPin* Input = Scale ? Scale->FindPin(TEXT("A")) : nullptr;
		UEdGraphPin* Factor = Scale ? Scale->FindPin(TEXT("B")) : nullptr;
		UK2Node_VariableGet* Yaw = Input && Input->LinkedTo.Num() == 1 ?
			Cast<UK2Node_VariableGet>(Input->LinkedTo[0]->GetOwningNode()) : nullptr;
		if (!Yaw || Yaw->VariableReference.GetMemberName() != TEXT("YawDelta") ||
			!Factor || !Factor->LinkedTo.IsEmpty() ||
			!FMath::IsNearlyEqual(FCString::Atod(*Factor->DefaultValue), -1.0))
		{
			UE_LOG(LogTemp, Error, TEXT("Countess original lean pin does not match YawDelta"));
			return;
		}
		Blueprint->Modify();
		Scale->Modify();
		Scale->GetSchema()->TrySetDefaultValue(*Factor, TEXT("-0.5"));
		FBlueprintEditorUtils::MarkBlueprintAsModified(Blueprint);
		UE_LOG(LogTemp, Display, TEXT("COUNTESS_TURN_LEAN_NORMALIZED"));
	}));

// 상태머신을 이름으로 찾고 클래스의 정적 설명을 사용해 초기화 전에도 안전하게 읽는다.
static FAutoConsoleCommandWithWorldAndArgs SampleCountessInputState(
	TEXT("CountessInputQA.State"), TEXT("PIE only: sample filename without extension"),
	FConsoleCommandWithWorldAndArgsDelegate::CreateLambda([](const TArray<FString>& Args, UWorld* World)
	{
		if (!World || World->WorldType != EWorldType::PIE || Args.Num() != 1 ||
			Args[0].Contains(TEXT("/")) || Args[0].Contains(TEXT("\\")) || Args[0].Contains(TEXT("..")))
		{
			return;
		}
		ACharacter* Character = UGameplayStatics::GetPlayerCharacter(World, 0);
		UAnimInstance* Anim = Character && Character->GetMesh() ? Character->GetMesh()->GetAnimInstance() : nullptr;
		if (!Anim)
		{
			return;
		}
		const TSharedRef<FJsonObject> State = MakeShared<FJsonObject>();
		State->SetNumberField(TEXT("time"), World->GetTimeSeconds());
		State->SetNumberField(TEXT("speed"), Character->GetVelocity().Size2D());
		UNavigationSystemV1* Navigation = FNavigationSystem::GetCurrent<UNavigationSystemV1>(World);
		State->SetBoolField(TEXT("navigation_ready"), Navigation && !Navigation->IsNavigationBuildInProgress());
		APlayerController* Controller = UGameplayStatics::GetPlayerController(World, 0);
		UPathFollowingComponent* Following = Controller ? Controller->FindComponentByClass<UPathFollowingComponent>() : nullptr;
		State->SetBoolField(TEXT("right_mouse_held"), Controller && Controller->IsInputKeyDown(EKeys::RightMouseButton));
		State->SetNumberField(TEXT("capsule_radius"), Character->GetCapsuleComponent()->GetScaledCapsuleRadius());
		State->SetNumberField(TEXT("capsule_visibility_response"), Character->GetCapsuleComponent()->GetCollisionResponseToChannel(ECC_Visibility));
		State->SetNumberField(TEXT("mesh_visibility_response"), Character->GetMesh()->GetCollisionResponseToChannel(ECC_Visibility));
		if (Following)
		{
			State->SetStringField(TEXT("path_status"), Following->GetStatusDesc());
			State->SetNumberField(TEXT("move_request_id"), Following->GetCurrentRequestId().GetID());
			State->SetNumberField(TEXT("default_acceptance_radius"), Following->GetDefaultAcceptanceRadius());
			FHitResult Hit;
			FNavLocation Goal;
			const bool bCursorHit = Controller->GetHitResultUnderCursor(ECC_Visibility, true, Hit);
			State->SetBoolField(TEXT("cursor_has_hit"), bCursorHit);
			State->SetStringField(TEXT("cursor_raw_hit_actor"), GetNameSafe(Hit.GetActor()));
			State->SetNumberField(TEXT("cursor_raw_hit_z"), Hit.ImpactPoint.Z);
			float MouseX = 0.0f, MouseY = 0.0f;
			State->SetBoolField(TEXT("cursor_position_valid"), Controller->GetMousePosition(MouseX, MouseY));
			State->SetNumberField(TEXT("cursor_mouse_x"), MouseX);
			State->SetNumberField(TEXT("cursor_mouse_y"), MouseY);
			if (Navigation && bCursorHit &&
				Navigation->ProjectPointToNavigation(Hit.ImpactPoint, Goal, FVector(100.0f, 100.0f, 250.0f),
					&Character->GetNavAgentPropertiesRef()))
			{
				State->SetStringField(TEXT("cursor_hit_actor"), GetNameSafe(Hit.GetActor()));
				State->SetStringField(TEXT("cursor_hit_component"), GetNameSafe(Hit.GetComponent()));
				State->SetBoolField(TEXT("cursor_hit_self"), Hit.GetActor() == Character);
				State->SetNumberField(TEXT("cursor_hit_z"), Hit.ImpactPoint.Z);
				State->SetNumberField(TEXT("cursor_goal_x"), Goal.Location.X);
				State->SetNumberField(TEXT("cursor_goal_y"), Goal.Location.Y);
				State->SetNumberField(TEXT("cursor_goal_z"), Goal.Location.Z);
				State->SetNumberField(TEXT("cursor_goal_distance"), FVector::Dist2D(Character->GetActorLocation(), Goal.Location));
				State->SetBoolField(TEXT("cursor_goal_reached"), Following->HasReached(Goal.Location, EPathFollowingReachMode::OverlapAgent));
			}
		}
		FName GroundState = NAME_None;
		const FAnimNode_StateMachine* Machine = Anim->GetStateMachineInstanceFromName(TEXT("Ground Locomotion"));
		if (Machine)
		{
			IAnimClassInterface* Interface = IAnimClassInterface::GetFromClass(Anim->GetClass());
			const FBakedAnimationStateMachine* Description = Interface ?
				Anim->GetMachineDescription(Interface, const_cast<FAnimNode_StateMachine*>(Machine)) : nullptr;
			if (Description && Description->States.IsValidIndex(Machine->GetCurrentState()))
			{
				GroundState = Description->States[Machine->GetCurrentState()].StateName;
				const int32 MachineIndex = Anim->GetStateMachineIndex(TEXT("Ground Locomotion"));
				for (int32 StateIndex = 0; Anim->IsInitialized() && StateIndex < Description->States.Num(); ++StateIndex)
				{
					if (Description->States[StateIndex].StateName == TEXT("Run"))
					{
						State->SetNumberField(TEXT("run_weight"), Machine->GetStateWeight(StateIndex));
						State->SetNumberField(TEXT("run_phase"), Anim->GetRelevantAnimTimeFraction(MachineIndex, StateIndex));
						State->SetNumberField(TEXT("run_time"), Anim->GetRelevantAnimTime(MachineIndex, StateIndex));
					}
				}
			}
		}
		State->SetStringField(TEXT("ground_state"), GroundState.ToString());
		UAnimMontage* Intro = FindObject<UAnimMontage>(nullptr,
			TEXT("/Game/ParagonCountess/Characters/Heroes/Countess/Animations/LevelStart_Montage.LevelStart_Montage"));
		State->SetBoolField(TEXT("intro_playing"), Intro && Anim->Montage_IsPlaying(Intro));
		State->SetNumberField(TEXT("intro_weight"), Intro && Anim->GetActiveInstanceForMontage(Intro) ?
			Anim->GetActiveInstanceForMontage(Intro)->GetWeight() : 0.0f);
		FString Json;
		const TSharedRef<TJsonWriter<>> Writer = TJsonWriterFactory<>::Create(&Json);
		FJsonSerializer::Serialize(State, Writer);
		const FString Directory = CharacterPipelineQA::GetOutputDirectory(TEXT("QA/CountessInputStop"));
		FPlatformFileManager::Get().GetPlatformFile().CreateDirectoryTree(*Directory);
		FFileHelper::SaveStringToFile(Json, *(Directory / (Args[0] + TEXT(".json"))),
			FFileHelper::EEncodingOptions::ForceUTF8WithoutBOM);
	}));

static FAutoConsoleCommandWithWorldAndArgs InjectCountessKey(
	TEXT("CountessInputQA.Key"), TEXT("PIE only: key_name Press|Release"),
	FConsoleCommandWithWorldAndArgsDelegate::CreateLambda([](const TArray<FString>& Args, UWorld* World)
	{
		if (!World || World->WorldType != EWorldType::PIE || Args.Num() != 2)
		{
			return;
		}
		APlayerController* Controller = UGameplayStatics::GetPlayerController(World, 0);
		ULocalPlayer* Player = Controller ? Controller->GetLocalPlayer() : nullptr;
		FSceneViewport* Viewport = Player && Player->ViewportClient ? Player->ViewportClient->GetGameViewport() : nullptr;
		const FKey Key(*Args[0]);
		if (Viewport && Key.IsValid())
		{
			Controller->InputKey(FInputKeyEventArgs(Viewport, FInputDeviceId::CreateFromInternalId(0), Key,
				Args[1] == TEXT("Release") ? IE_Released : IE_Pressed, FPlatformTime::Cycles64()));
		}
	}));

#endif
