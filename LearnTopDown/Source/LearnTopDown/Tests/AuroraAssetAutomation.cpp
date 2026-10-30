#if WITH_EDITOR && WITH_DEV_AUTOMATION_TESTS

#include "CharacterPipelineQA.h"

#include "Animation/AnimBlueprint.h"
#include "Animation/AnimationAsset.h"
#include "AnimGraphNode_AssetPlayerBase.h"
#include "AnimGraphNode_Root.h"
#include "AnimGraphNode_Slot.h"
#include "AnimStateConduitNode.h"
#include "AnimStateEntryNode.h"
#include "AnimStateNode.h"
#include "AnimStateNodeBase.h"
#include "AnimStateTransitionNode.h"
#include "AnimationStateMachineGraph.h"
#include "Dom/JsonObject.h"
#include "EdGraph/EdGraph.h"
#include "EdGraph/EdGraphNode.h"
#include "EdGraph/EdGraphPin.h"
#include "Kismet2/BlueprintEditorUtils.h"
#include "Kismet2/KismetEditorUtilities.h"
#include "Misc/FileHelper.h"
#include "Serialization/JsonSerializer.h"

// 4번(Aurora) 이동 애니 진단용 읽기 전용 덤프. 상태 기계마다 상태(안에서 재생하는 애셋)와 전환(앞·뒤 상태, 섞는 시간,
// 자동 규칙 여부, 규칙 그래프의 노드 제목)을 적는다. 1번(Countess) 사본과 비교하려고 그 경로도 읽기만 허용한다.
namespace AuroraAssetQA
{
	using FObject = TSharedRef<FJsonObject>;
	using FValues = TArray<TSharedPtr<FJsonValue>>;

	static FString StateName(const UAnimStateNodeBase* Node)
	{
		return Node ? Node->GetStateName() : FString(TEXT("-"));
	}

	static FValues GraphNodeTitles(const UEdGraph* Graph)
	{
		FValues Titles;
		if (!Graph)
		{
			return Titles;
		}
		for (const UEdGraphNode* Node : Graph->Nodes)
		{
			FString Title = Node->GetNodeTitle(ENodeTitleType::ListView).ToString();
			if (const UAnimGraphNode_AssetPlayerBase* Player = Cast<UAnimGraphNode_AssetPlayerBase>(Node))
			{
				if (const UAnimationAsset* Asset = Player->GetAnimationAsset())
				{
					Title += TEXT(" [") + Asset->GetName() + TEXT("]");
				}
			}
			// 연결된 입력 핀의 기본값(비교 상수 등)도 같이 적어 규칙을 읽을 수 있게 한다.
			for (const UEdGraphPin* Pin : Node->Pins)
			{
				if (Pin->Direction == EGPD_Input && Pin->LinkedTo.IsEmpty() && !Pin->DefaultValue.IsEmpty() && !Pin->bHidden)
				{
					Title += FString::Printf(TEXT(" %s=%s"), *Pin->PinName.ToString(), *Pin->DefaultValue);
				}
			}
			Titles.Add(MakeShared<FJsonValueString>(Title));
		}
		return Titles;
	}

	static FObject Machine(const UAnimationStateMachineGraph* Graph)
	{
		const FObject Result = MakeShared<FJsonObject>();
		Result->SetStringField(TEXT("graph"), Graph->GetPathName());
		FValues States;
		FValues Transitions;
		for (const UEdGraphNode* Node : Graph->Nodes)
		{
			if (const UAnimStateTransitionNode* Transition = Cast<UAnimStateTransitionNode>(Node))
			{
				const FObject Item = MakeShared<FJsonObject>();
				Item->SetStringField(TEXT("node"), Transition->GetName());
				Item->SetStringField(TEXT("from"), StateName(Transition->GetPreviousState()));
				Item->SetStringField(TEXT("to"), StateName(Transition->GetNextState()));
				Item->SetNumberField(TEXT("crossfade"), Transition->CrossfadeDuration);
				Item->SetNumberField(TEXT("priority"), Transition->PriorityOrder);
				Item->SetBoolField(TEXT("automatic_rule"), Transition->bAutomaticRuleBasedOnSequencePlayerInState);
				Item->SetNumberField(TEXT("automatic_trigger_time"), Transition->AutomaticRuleTriggerTime);
				Item->SetArrayField(TEXT("rule"), GraphNodeTitles(Transition->BoundGraph));
				Transitions.Add(MakeShared<FJsonValueObject>(Item));
			}
			else if (const UAnimStateNodeBase* State = Cast<UAnimStateNodeBase>(Node))
			{
				const FObject Item = MakeShared<FJsonObject>();
				Item->SetStringField(TEXT("node"), State->GetName());
				Item->SetStringField(TEXT("name"), StateName(State));
				Item->SetStringField(TEXT("kind"), State->GetClass()->GetName());
				Item->SetArrayField(TEXT("contents"), GraphNodeTitles(State->GetBoundGraph()));
				States.Add(MakeShared<FJsonValueObject>(Item));
			}
		}
		Result->SetArrayField(TEXT("states"), States);
		Result->SetArrayField(TEXT("transitions"), Transitions);
		return Result;
	}

	static bool Allowed(const FString& Path)
	{
		return Path.StartsWith(TEXT("/Game/ParagonAurora/")) || Path.StartsWith(TEXT("/Game/TopDown/Characters/Aurora/")) ||
			Path.StartsWith(TEXT("/Game/TopDown/Characters/Countess/")) || Path.StartsWith(TEXT("/Game/ParagonCountess/"));
	}

	static UAnimStateNodeBase* FindState(const UAnimationStateMachineGraph* Graph, const TCHAR* Name)
	{
		for (UEdGraphNode* Node : Graph->Nodes)
		{
			UAnimStateNodeBase* State = Cast<UAnimStateNodeBase>(Node);
			if (State && !State->IsA<UAnimStateTransitionNode>() && State->GetStateName() == Name)
			{
				return State;
			}
		}
		return nullptr;
	}

	static TArray<UAnimStateTransitionNode*> FindTransitions(const UAnimationStateMachineGraph* Graph, const TCHAR* From, const TCHAR* To)
	{
		TArray<UAnimStateTransitionNode*> Result;
		for (UEdGraphNode* Node : Graph->Nodes)
		{
			UAnimStateTransitionNode* Transition = Cast<UAnimStateTransitionNode>(Node);
			if (Transition && StateName(Transition->GetPreviousState()) == From && StateName(Transition->GetNextState()) == To)
			{
				Result.Add(Transition);
			}
		}
		return Result;
	}

	// 1번(Countess) 사본과 같은 수정: 출발·멈춤 동작 상태(JogStart·JogStop)를 건너뛰고 Idle↔Run을 바로 섞는다.
	// 짧게 움직이면 멈춤 동작(약 1초)이 이동보다 길어 몸이 낮게 굽었다 일어서던 문제(short-move 진단 2026-10-18)를 없앤다.
	// 원본 Paragon 애셋은 건드리지 않고, 미리 복사해 둔 사본만 고친다. 저장은 호출한 파이썬이 한다.
	static FAutoConsoleCommand BuildTopDown(
		TEXT("AuroraAssetQA.RewireTopDownLocomotion"),
		TEXT("Editor only: in /Game/TopDown/Characters/Aurora copy, link Idle<->Run directly like the Countess copy; writes aurora-rewire.json"),
		FConsoleCommandWithArgsDelegate::CreateLambda([](const TArray<FString>& Args)
		{
			const FObject Report = MakeShared<FJsonObject>();
			bool bPassed = Args.Num() == 1 && Args[0].StartsWith(TEXT("/Game/TopDown/Characters/Aurora/"));
			UAnimBlueprint* Asset = bPassed ? LoadObject<UAnimBlueprint>(nullptr, *Args[0]) : nullptr;
			const UAnimationStateMachineGraph* Ground = nullptr;
			if (Asset)
			{
				TArray<UEdGraph*> Graphs;
				Asset->GetAllGraphs(Graphs);
				for (UEdGraph* Graph : Graphs)
				{
					const UAnimationStateMachineGraph* Machine = Cast<UAnimationStateMachineGraph>(Graph);
					if (Machine && FindState(Machine, TEXT("JogStop")) && FindState(Machine, TEXT("JogStart")))
					{
						Ground = Machine;
					}
				}
			}
			UAnimStateNodeBase* Idle = Ground ? FindState(Ground, TEXT("Idle")) : nullptr;
			UAnimStateNodeBase* Run = Ground ? FindState(Ground, TEXT("Run")) : nullptr;
			const TArray<UAnimStateTransitionNode*> RunToStop = Ground ? FindTransitions(Ground, TEXT("Run"), TEXT("JogStop")) : TArray<UAnimStateTransitionNode*>();
			const TArray<UAnimStateTransitionNode*> IdleToStart = Ground ? FindTransitions(Ground, TEXT("Idle"), TEXT("JogStart")) : TArray<UAnimStateTransitionNode*>();
			const TArray<UAnimStateTransitionNode*> StartToStop = Ground ? FindTransitions(Ground, TEXT("JogStart"), TEXT("JogStop")) : TArray<UAnimStateTransitionNode*>();
			const TArray<UAnimStateTransitionNode*> IdleToRun = Ground ? FindTransitions(Ground, TEXT("Idle"), TEXT("Run")) : TArray<UAnimStateTransitionNode*>();
			// 이미 고친 사본이면(Run→JogStop이 없음) 다시 고치지 않는다.
			bPassed = bPassed && Asset && Idle && Run && RunToStop.Num() == 1 && IdleToStart.Num() == 1;
			if (bPassed)
			{
				Asset->Modify();
				// 원본의 Idle→Run(속도 > 50)과 JogStart→JogStop은 1번 사본에 없다. 바로 잇는 전환과 겹치지 않게 지운다.
				for (UAnimStateTransitionNode* Extra : IdleToRun)
				{
					Extra->BreakAllNodeLinks();
					FBlueprintEditorUtils::RemoveNode(Asset, Extra, true);
				}
				for (UAnimStateTransitionNode* Extra : StartToStop)
				{
					Extra->BreakAllNodeLinks();
					FBlueprintEditorUtils::RemoveNode(Asset, Extra, true);
				}
				// 멈출 때(가속 없음) Run→Idle 0.18초, 출발할 때(속도 > 0·가속) Idle→Run 0.14초 — 1번 사본 값.
				UAnimStateTransitionNode* Stop = RunToStop[0];
				Stop->Modify();
				Stop->BreakAllNodeLinks();
				Stop->CreateConnections(Run, Idle);
				Stop->CrossfadeDuration = 0.18f;
				UAnimStateTransitionNode* Start = IdleToStart[0];
				Start->Modify();
				Start->BreakAllNodeLinks();
				Start->CreateConnections(Idle, Run);
				Start->CrossfadeDuration = 0.14f;
				FBlueprintEditorUtils::MarkBlueprintAsStructurallyModified(Asset);
				FKismetEditorUtilities::CompileBlueprint(Asset);
				Report->SetObjectField(TEXT("ground_after"), Machine(Ground));
			}
			Report->SetBoolField(TEXT("passed"), bPassed);
			Report->SetNumberField(TEXT("removed_idle_to_run"), IdleToRun.Num());
			Report->SetNumberField(TEXT("removed_start_to_stop"), StartToStop.Num());
			FString Text;
			const TSharedRef<TJsonWriter<>> Writer = TJsonWriterFactory<>::Create(&Text);
			FJsonSerializer::Serialize(Report, Writer);
			FFileHelper::SaveStringToFile(Text, *(CharacterPipelineQA::GetOutputDirectory(TEXT("QA/Aurora")) / TEXT("aurora-rewire.json")),
				FFileHelper::EEncodingOptions::ForceUTF8WithoutBOM);
		}));

	// 1번(Countess) 사본과 같은 수정: 최종 출력 바로 앞에 전신 스킬 슬롯(AuroraFullBody)을 넣는다. 스킬 동작을 몽타주로 이 슬롯에
	// 재생하면 시작·끝이 보행 자세와 섞인다(숨긴 자세 메시를 따라가던 방식은 끝날 때 자세가 툭 바뀌었다, 2026-10-18 「끊긴다」).
	// 원본 Paragon 애셋은 건드리지 않고 사본만 고친다. 저장은 호출한 파이썬이 한다.
	static FAutoConsoleCommand InstallFullBodySlot(
		TEXT("AuroraAssetQA.InstallFullBodySlot"),
		TEXT("Editor only: in the /Game/TopDown/Characters/Aurora copy, add the AuroraFullBody slot right before the output; writes aurora-slot.json"),
		FConsoleCommandWithArgsDelegate::CreateLambda([](const TArray<FString>& Args)
		{
			const FObject Report = MakeShared<FJsonObject>();
			bool bPassed = Args.Num() == 1 && Args[0].StartsWith(TEXT("/Game/TopDown/Characters/Aurora/"));
			UAnimBlueprint* Asset = bPassed ? LoadObject<UAnimBlueprint>(nullptr, *Args[0]) : nullptr;
			bPassed = Asset != nullptr;
			bool bAlready = false;
			bool bInstalled = false;
			if (Asset)
			{
				TArray<UEdGraph*> Graphs;
				Asset->GetAllGraphs(Graphs);
				for (UEdGraph* Graph : Graphs)
				{
					if (Graph->GetFName() != TEXT("AnimGraph"))
					{
						continue;
					}
					UAnimGraphNode_Root* Root = nullptr;
					for (UEdGraphNode* Node : Graph->Nodes)
					{
						const UAnimGraphNode_Slot* Slot = Cast<UAnimGraphNode_Slot>(Node);
						bAlready |= Slot && Slot->Node.SlotName == TEXT("AuroraFullBody");
						if (UAnimGraphNode_Root* Candidate = Cast<UAnimGraphNode_Root>(Node))
						{
							Root = Candidate;
						}
					}
					UEdGraphPin* Result = Root ? Root->FindPin(TEXT("Result")) : nullptr;
					if (bAlready || !Result || Result->LinkedTo.Num() != 1)
					{
						break;
					}
					Asset->Modify();
					Graph->Modify();
					Root->Modify();
					UEdGraphPin* Source = Result->LinkedTo[0];
					FGraphNodeCreator<UAnimGraphNode_Slot> Creator(*Graph);
					UAnimGraphNode_Slot* Slot = Creator.CreateNode();
					Slot->Node.SlotName = TEXT("AuroraFullBody");
					Slot->NodePosX = Root->NodePosX - 180;
					Slot->NodePosY = Root->NodePosY + 150;
					Creator.Finalize();
					UEdGraphPin* Input = Slot->FindPin(TEXT("Source"));
					UEdGraphPin* Output = Slot->FindPin(TEXT("Pose"));
					Result->BreakAllPinLinks();
					const UEdGraphSchema* Schema = Graph->GetSchema();
					bInstalled = Input && Output && Schema->TryCreateConnection(Source, Input) && Schema->TryCreateConnection(Output, Result);
					if (bInstalled)
					{
						FBlueprintEditorUtils::MarkBlueprintAsStructurallyModified(Asset);
						FKismetEditorUtilities::CompileBlueprint(Asset);
					}
					break;
				}
			}
			Report->SetBoolField(TEXT("passed"), bPassed && (bInstalled || bAlready));
			Report->SetBoolField(TEXT("already_present"), bAlready);
			Report->SetBoolField(TEXT("installed"), bInstalled);
			FString Text;
			const TSharedRef<TJsonWriter<>> Writer = TJsonWriterFactory<>::Create(&Text);
			FJsonSerializer::Serialize(Report, Writer);
			FFileHelper::SaveStringToFile(Text, *(CharacterPipelineQA::GetOutputDirectory(TEXT("QA/Aurora")) / TEXT("aurora-slot.json")),
				FFileHelper::EEncodingOptions::ForceUTF8WithoutBOM);
		}));

	static FAutoConsoleCommand Dump(
		TEXT("AuroraAssetQA.DumpStateMachines"),
		TEXT("Editor only, read-only: state machines (states, transitions, rules) of Aurora/Countess animation blueprints; writes aurora-state-machines.json"),
		FConsoleCommandWithArgsDelegate::CreateLambda([](const TArray<FString>& Args)
		{
			const FObject Report = MakeShared<FJsonObject>();
			FValues Assets;
			bool bPassed = !Args.IsEmpty();
			for (const FString& Path : Args)
			{
				UAnimBlueprint* Asset = Allowed(Path) ? LoadObject<UAnimBlueprint>(nullptr, *Path) : nullptr;
				if (!Asset)
				{
					bPassed = false;
					continue;
				}
				const FObject Item = MakeShared<FJsonObject>();
				Item->SetStringField(TEXT("asset"), Path);
				TArray<UEdGraph*> Graphs;
				Asset->GetAllGraphs(Graphs);
				FValues Machines;
				for (const UEdGraph* Graph : Graphs)
				{
					if (const UAnimationStateMachineGraph* MachineGraph = Cast<UAnimationStateMachineGraph>(Graph))
					{
						Machines.Add(MakeShared<FJsonValueObject>(Machine(MachineGraph)));
					}
				}
				Item->SetArrayField(TEXT("machines"), Machines);
				Assets.Add(MakeShared<FJsonValueObject>(Item));
			}
			Report->SetBoolField(TEXT("passed"), bPassed);
			Report->SetBoolField(TEXT("read_only"), true);
			Report->SetArrayField(TEXT("assets"), Assets);
			FString Text;
			const TSharedRef<TJsonWriter<>> Writer = TJsonWriterFactory<>::Create(&Text);
			FJsonSerializer::Serialize(Report, Writer);
			FFileHelper::SaveStringToFile(Text, *(CharacterPipelineQA::GetOutputDirectory(TEXT("QA/Aurora")) / TEXT("aurora-state-machines.json")),
				FFileHelper::EEncodingOptions::ForceUTF8WithoutBOM);
		}));
}

#endif
