#if WITH_EDITOR && WITH_DEV_AUTOMATION_TESTS

#include "CharacterPipelineQA.h"
#include "../SparrowCharacter.h"
#include "Animation/AnimBlueprint.h"
#include "Animation/AnimSequence.h"
#include "AnimGraphNode_SequencePlayer.h"
#include "Components/SkeletalMeshComponent.h"
#include "EdGraph/EdGraphPin.h"
#include "Dom/JsonObject.h"
#include "Editor.h"
#include "Engine/World.h"
#include "HAL/IConsoleManager.h"
#include "Kismet/GameplayStatics.h"
#include "Kismet2/BlueprintEditorUtils.h"
#include "Misc/FileHelper.h"
#include "Serialization/JsonSerializer.h"

struct FSparrowStopQA
{
	static TSharedRef<FJsonObject> State(ASparrowCharacter* Character)
	{
		const TSharedRef<FJsonObject> Report = MakeShared<FJsonObject>();
		Report->SetBoolField(TEXT("pending"), Character->bFinishingStopHeading);
		Report->SetNumberField(TEXT("desired_yaw"), Character->StopHeadingYaw);
		Report->SetNumberField(TEXT("deadline"), Character->StopHeadingDeadline);
		Report->SetNumberField(TEXT("time"), Character->GetWorld()->GetTimeSeconds());
		Report->SetNumberField(TEXT("current_yaw"), Character->GetActorRotation().Yaw);
		Report->SetStringField(TEXT("anim_class"), GetPathNameSafe(Character->GetMesh()->GetAnimClass()));
		return Report;
	}
};

static FAutoConsoleCommandWithWorldAndArgs SnapshotSparrowStop(
	TEXT("SparrowStopQA.State"), TEXT("PIE only: filename token, read-only bounded stop-heading state"),
	FConsoleCommandWithWorldAndArgsDelegate::CreateLambda([](const TArray<FString>& Args, UWorld* World)
	{
		if (!World || World->WorldType != EWorldType::PIE || Args.Num() != 1 ||
			Args[0].Contains(TEXT("/")) || Args[0].Contains(TEXT("\\")) || Args[0].Contains(TEXT("..")))
		{
			return;
		}
		ASparrowCharacter* Character = Cast<ASparrowCharacter>(UGameplayStatics::GetPlayerCharacter(World, 0));
		if (!Character || !Character->GetMesh())
		{
			return;
		}
		FString Text;
		FJsonSerializer::Serialize(FSparrowStopQA::State(Character), TJsonWriterFactory<>::Create(&Text));
		FFileHelper::SaveStringToFile(Text, *(CharacterPipelineQA::GetOutputDirectory(TEXT("QA/SparrowInventory")) /
			(Args[0] + TEXT(".json"))), FFileHelper::EEncodingOptions::ForceUTF8WithoutBOM);
	}));

// 원본 자세와 이동 그래프는 보존하고 새 전용 AnimBP의 평상시 대기 시퀀스만 연결한다.
static FAutoConsoleCommand ConfigureSparrowTravelIdle(
	TEXT("SparrowStopQA.ConfigureIdle"), TEXT("Editor only: connect the owned travel idle in the smooth-stop copy; no asset saves"),
	FConsoleCommandDelegate::CreateLambda([]()
	{
		const TSharedRef<FJsonObject> Report = MakeShared<FJsonObject>();
		Report->SetBoolField(TEXT("passed"), false);
		Report->SetBoolField(TEXT("saved_packages"), false);
		const auto Write = [&Report]()
		{
			FString Text;
			FJsonSerializer::Serialize(Report, TJsonWriterFactory<>::Create(&Text));
			FFileHelper::SaveStringToFile(Text, *(CharacterPipelineQA::GetOutputDirectory(TEXT("QA/SparrowInventory")) /
				TEXT("sparrow-stop-idle-configuration.json")), FFileHelper::EEncodingOptions::ForceUTF8WithoutBOM);
		};
		const auto Fail = [&Report, &Write](const TCHAR* Error)
		{
			Report->SetStringField(TEXT("error"), Error);
			Write();
		};
		if (!GEditor || GEditor->PlayWorld)
		{
			Fail(TEXT("Owned idle installation requires the editor outside PIE"));
			return;
		}
		UAnimBlueprint* Blueprint = LoadObject<UAnimBlueprint>(nullptr,
			TEXT("/Game/TopDown/Characters/Sparrow/Animations/ABP_Sparrow_SmoothStop.ABP_Sparrow_SmoothStop"));
		UAnimSequence* Idle = LoadObject<UAnimSequence>(nullptr,
			TEXT("/Game/TopDown/Characters/Sparrow/Animations/A_Sparrow_TravelIdle.A_Sparrow_TravelIdle"));
		if (!Blueprint || !Idle || Blueprint->TargetSkeleton != Idle->GetSkeleton())
		{
			Fail(TEXT("Owned smooth-stop blueprint and travel idle must use the same skeleton"));
			return;
		}
		UAnimGraphNode_SequencePlayer* Player = FindObject<UAnimGraphNode_SequencePlayer>(nullptr,
			*(Blueprint->GetPathName() + TEXT(":AnimGraph.AnimGraphNode_StateMachine_5.Ground Locomotion.AnimStateNode_1.Idle.SparrowRelaxedIdle")));
		const FString Previous = Player ? GetPathNameSafe(Player->Node.GetSequence()) : FString();
		UEdGraphPin* Pose = Player ? Player->FindPin(TEXT("Pose")) : nullptr;
		if (!Player || !Pose || Pose->LinkedTo.Num() != 1 ||
			Pose->LinkedTo[0]->PinName != TEXT("BlendPose_1") ||
			Pose->LinkedTo[0]->GetOwningNode()->GetFName() != TEXT("SparrowCombatPose") ||
			(Previous != TEXT("/Game/TopDown/Characters/Sparrow/Animations/A_Sparrow_RelaxedIdle.A_Sparrow_RelaxedIdle") &&
			 Previous != Idle->GetPathName()))
		{
			Fail(TEXT("Inspected relaxed-idle player or its combat/neutral branch changed"));
			return;
		}
		Blueprint->Modify();
		Player->Modify();
		const bool bConfigured = Player->Node.SetSequence(Idle) && Player->Node.SetLoopAnimation(true);
		FBlueprintEditorUtils::MarkBlueprintAsStructurallyModified(Blueprint);
		Report->SetStringField(TEXT("blueprint"), Blueprint->GetPathName());
		Report->SetStringField(TEXT("player"), Player->GetPathName());
		Report->SetStringField(TEXT("sequence_before"), Previous);
		Report->SetStringField(TEXT("sequence_after"), GetPathNameSafe(Player->Node.GetSequence()));
		Report->SetBoolField(TEXT("passed"), bConfigured && Player->Node.GetSequence() == Idle);
		Write();
	}));

#endif
