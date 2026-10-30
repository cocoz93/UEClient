#if WITH_EDITOR && WITH_DEV_AUTOMATION_TESTS

#include "CharacterPipelineQA.h"

#include "Animation/AnimBlueprint.h"
#include "Animation/AnimInstance.h"
#include "Animation/AnimMontage.h"
#include "Animation/AnimSequence.h"
#include "Animation/AnimData/IAnimationDataController.h"
#include "Animation/AnimData/IAnimationDataModel.h"
#include "Animation/BlendSpace.h"
#include "Animation/Skeleton.h"
#include "Animation/AnimNotifies/AnimNotify.h"
#include "Animation/AnimNotifies/AnimNotifyState.h"
#include "Animation/AnimNotifies/AnimNotify_PlaySound.h"
#include "AnimGraphNode_BlendSpacePlayer.h"
#include "AnimGraphNode_BlendListByBool.h"
#include "AnimGraphNode_SequencePlayer.h"
#include "AnimGraphNode_Root.h"
#include "AnimGraphNode_RotationOffsetBlendSpace.h"
#include "AnimGraphNode_Slot.h"
#include "AnimStateNode.h"
#include "AnimStateTransitionNode.h"
#include "../TopDownCombatCharacter.h"
#include "../SparrowCharacter.h"
#include "Components/SkeletalMeshComponent.h"
#include "Dom/JsonObject.h"
#include "EdGraph/EdGraph.h"
#include "EdGraph/EdGraphNode.h"
#include "EdGraph/EdGraphPin.h"
#include "EdGraphSchema_K2.h"
#include "Engine/Blueprint.h"
#include "Engine/SkeletalMesh.h"
#include "Engine/SkeletalMeshSocket.h"
#include "GameFramework/Character.h"
#include "K2Node_CallFunction.h"
#include "K2Node_DynamicCast.h"
#include "K2Node_VariableGet.h"
#include "K2Node_VariableSet.h"
#include "Kismet/KismetMathLibrary.h"
#include "Kismet2/BlueprintEditorUtils.h"
#include "Misc/FileHelper.h"
#include "Particles/ParticleSystem.h"
#include "Particles/ParticleEmitter.h"
#include "Particles/ParticleLODLevel.h"
#include "Particles/ParticleModule.h"
#include "Particles/ParticleModuleRequired.h"
#include "Particles/Spawn/ParticleModuleSpawn.h"
#include "Particles/TypeData/ParticleModuleTypeDataBase.h"
#include "Serialization/JsonSerializer.h"
#include "UObject/UObjectHash.h"
#include "UObject/UnrealType.h"

namespace SparrowAssetQA
{
	using FObject = TSharedRef<FJsonObject>;
	using FValues = TArray<TSharedPtr<FJsonValue>>;

	static FValues Strings(const TArray<FString>& Values)
	{
		FValues Result;
		for (const FString& Value : Values)
		{
			Result.Add(MakeShared<FJsonValueString>(Value));
		}
		return Result;
	}

	// 텍스트 export는 원본의 struct/enum/배열 값을 읽기만 한다.
	static FObject Properties(const UObject* Object)
	{
		const FObject Result = MakeShared<FJsonObject>();
		if (Object)
		{
			for (TFieldIterator<FProperty> It(Object->GetClass()); It; ++It)
			{
				const FProperty* Property = *It;
				if (Property->HasAnyPropertyFlags(CPF_Transient | CPF_DuplicateTransient))
				{
					continue;
				}
				FString Value;
				Property->ExportText_InContainer(0, Value, Object, nullptr, const_cast<UObject*>(Object), PPF_None);
				Result->SetStringField(Property->GetName(), Value);
			}
		}
		return Result;
	}

	static FObject Describe(UObject* Object, int32 ChildDepth = 0)
	{
		const FObject Result = MakeShared<FJsonObject>();
		Result->SetBoolField(TEXT("present"), Object != nullptr);
		if (!Object)
		{
			return Result;
		}
		Result->SetStringField(TEXT("path"), Object->GetPathName());
		Result->SetStringField(TEXT("class"), Object->GetClass()->GetPathName());
		Result->SetObjectField(TEXT("properties"), Properties(Object));
		if (ChildDepth > 0)
		{
			TArray<UObject*> Children;
			GetObjectsWithOuter(Object, Children, EGetObjectsFlags::None);
			FValues Inner;
			for (UObject* Child : Children)
			{
				Inner.Add(MakeShared<FJsonValueObject>(Describe(Child, ChildDepth - 1)));
			}
			Result->SetArrayField(TEXT("inner_objects"), Inner);
		}
		return Result;
	}

	static FObject Blueprint(UBlueprint* Asset)
	{
		const FObject Result = Describe(Asset);
		Result->SetStringField(TEXT("parent_class"), GetPathNameSafe(Asset->ParentClass.Get()));
		Result->SetStringField(TEXT("generated_class"), GetPathNameSafe(Asset->GeneratedClass));
		if (Asset->GeneratedClass)
		{
			UObject* CDO = Asset->GeneratedClass->GetDefaultObject();
			Result->SetObjectField(TEXT("cdo"), Describe(CDO));
			if (const ACharacter* Character = Cast<ACharacter>(CDO))
			{
				Result->SetObjectField(TEXT("mesh_component"), Describe(Character->GetMesh()));
			}
		}
		if (const UAnimBlueprint* AnimBlueprint = Cast<UAnimBlueprint>(Asset))
		{
			Result->SetStringField(TEXT("target_skeleton"), GetPathNameSafe(AnimBlueprint->TargetSkeleton));
		}
		FValues Variables;
		for (const FBPVariableDescription& Variable : Asset->NewVariables)
		{
			const FObject Item = MakeShared<FJsonObject>();
			Item->SetStringField(TEXT("name"), Variable.VarName.ToString());
			Item->SetStringField(TEXT("category"), Variable.Category.ToString());
			Item->SetStringField(TEXT("pin_category"), Variable.VarType.PinCategory.ToString());
			Item->SetStringField(TEXT("pin_subcategory"), Variable.VarType.PinSubCategory.ToString());
			Item->SetStringField(TEXT("pin_subcategory_object"), GetPathNameSafe(Variable.VarType.PinSubCategoryObject.Get()));
			Item->SetStringField(TEXT("default_value"), Variable.DefaultValue);
			Variables.Add(MakeShared<FJsonValueObject>(Item));
		}
		Result->SetArrayField(TEXT("variables"), Variables);
		TArray<UEdGraph*> Graphs;
		Asset->GetAllGraphs(Graphs);
		FValues GraphValues;
		for (UEdGraph* Graph : Graphs)
		{
			const FObject GraphValue = MakeShared<FJsonObject>();
			GraphValue->SetStringField(TEXT("path"), Graph->GetPathName());
			GraphValue->SetStringField(TEXT("name"), Graph->GetName());
			FValues Nodes;
			for (UEdGraphNode* Node : Graph->Nodes)
			{
				if (!Node)
				{
					continue;
				}
				const FObject NodeValue = Describe(Node);
				NodeValue->SetStringField(TEXT("title"), Node->GetNodeTitle(ENodeTitleType::FullTitle).ToString());
				FValues Pins;
				for (const UEdGraphPin* Pin : Node->Pins)
				{
					if (!Pin)
					{
						continue;
					}
					const FObject PinValue = MakeShared<FJsonObject>();
					PinValue->SetStringField(TEXT("name"), Pin->PinName.ToString());
					PinValue->SetStringField(TEXT("category"), Pin->PinType.PinCategory.ToString());
					PinValue->SetStringField(TEXT("direction"), Pin->Direction == EGPD_Input ? TEXT("input") : TEXT("output"));
					PinValue->SetStringField(TEXT("default"), Pin->DefaultValue);
					PinValue->SetStringField(TEXT("default_object"), GetPathNameSafe(Pin->DefaultObject));
					FValues Links;
					for (const UEdGraphPin* Linked : Pin->LinkedTo)
					{
						Links.Add(MakeShared<FJsonValueString>(Linked->GetOwningNode()->GetPathName() + TEXT(":") + Linked->PinName.ToString()));
					}
					PinValue->SetArrayField(TEXT("links"), Links);
					Pins.Add(MakeShared<FJsonValueObject>(PinValue));
				}
				NodeValue->SetArrayField(TEXT("pins"), Pins);
				Nodes.Add(MakeShared<FJsonValueObject>(NodeValue));
			}
			GraphValue->SetArrayField(TEXT("nodes"), Nodes);
			GraphValues.Add(MakeShared<FJsonValueObject>(GraphValue));
		}
		Result->SetArrayField(TEXT("graphs"), GraphValues);
		return Result;
	}

	static FObject Mesh(USkeletalMesh* Asset)
	{
		const FObject Result = Describe(Asset);
		Result->SetStringField(TEXT("skeleton"), GetPathNameSafe(Asset->GetSkeleton()));
		const FReferenceSkeleton& Reference = Asset->GetRefSkeleton();
		FValues Bones;
		for (int32 Index = 0; Index < Reference.GetNum(); ++Index)
		{
			const FObject Bone = MakeShared<FJsonObject>();
			Bone->SetStringField(TEXT("name"), Reference.GetBoneName(Index).ToString());
			Bone->SetNumberField(TEXT("index"), Index);
			Bone->SetNumberField(TEXT("parent_index"), Reference.GetParentIndex(Index));
			Bone->SetStringField(TEXT("reference_pose"), Reference.GetRefBonePose()[Index].ToString());
			Bones.Add(MakeShared<FJsonValueObject>(Bone));
		}
		Result->SetArrayField(TEXT("bones"), Bones);
		FValues Sockets;
		for (USkeletalMeshSocket* Socket : Asset->GetActiveSocketList())
		{
			Sockets.Add(MakeShared<FJsonValueObject>(Describe(Socket)));
		}
		Result->SetArrayField(TEXT("sockets"), Sockets);
		if (USkeleton* Skeleton = Asset->GetSkeleton())
		{
			Result->SetObjectField(TEXT("skeleton_data"), Describe(Skeleton));
		}
		return Result;
	}

	static FObject Animation(UAnimSequenceBase* Asset)
	{
		const FObject Result = Describe(Asset);
		Result->SetNumberField(TEXT("length"), Asset->GetPlayLength());
		Result->SetStringField(TEXT("skeleton"), GetPathNameSafe(Asset->GetSkeleton()));
		Result->SetBoolField(TEXT("root_motion_enabled"), Asset->HasRootMotion());
		FValues Notifies;
		for (const FAnimNotifyEvent& Notify : Asset->Notifies)
		{
			const FObject Item = MakeShared<FJsonObject>();
			Item->SetStringField(TEXT("name"), Notify.NotifyName.ToString());
			Item->SetNumberField(TEXT("time"), Notify.GetTime());
			Item->SetNumberField(TEXT("trigger_time"), Notify.GetTriggerTime());
			Item->SetNumberField(TEXT("duration"), Notify.GetDuration());
			Item->SetObjectField(TEXT("notify"), Describe(Notify.Notify, 1));
			Item->SetObjectField(TEXT("notify_state"), Describe(Notify.NotifyStateClass, 1));
			Notifies.Add(MakeShared<FJsonValueObject>(Item));
		}
		Result->SetArrayField(TEXT("notifies"), Notifies);
		if (const UAnimMontage* Montage = Cast<UAnimMontage>(Asset))
		{
			FValues Slots;
			for (const FSlotAnimationTrack& Track : Montage->SlotAnimTracks)
			{
				Slots.Add(MakeShared<FJsonValueString>(Track.SlotName.ToString()));
			}
			Result->SetArrayField(TEXT("slots"), Slots);
			Result->SetNumberField(TEXT("blend_in"), Montage->GetDefaultBlendInTime());
			Result->SetNumberField(TEXT("blend_out"), Montage->GetDefaultBlendOutTime());
		}
		return Result;
	}

	static FObject BlendSpace(UBlendSpace* Asset)
	{
		const FObject Result = Describe(Asset);
		FValues Axes;
		for (int32 Index = 0; Index < 3; ++Index)
		{
			const FBlendParameter& Parameter = Asset->GetBlendParameter(Index);
			const FObject Axis = MakeShared<FJsonObject>();
			Axis->SetStringField(TEXT("name"), Parameter.DisplayName);
			Axis->SetNumberField(TEXT("minimum"), Parameter.Min);
			Axis->SetNumberField(TEXT("maximum"), Parameter.Max);
			Axis->SetNumberField(TEXT("grid_divisions"), Parameter.GridNum);
			Axes.Add(MakeShared<FJsonValueObject>(Axis));
		}
		Result->SetArrayField(TEXT("axes"), Axes);
		FValues Samples;
		for (const FBlendSample& Sample : Asset->GetBlendSamples())
		{
			const FObject Item = MakeShared<FJsonObject>();
			Item->SetStringField(TEXT("animation"), GetPathNameSafe(Sample.Animation));
			Item->SetStringField(TEXT("value"), Sample.SampleValue.ToString());
			Item->SetNumberField(TEXT("rate_scale"), Sample.RateScale);
			Samples.Add(MakeShared<FJsonValueObject>(Item));
		}
		Result->SetArrayField(TEXT("samples"), Samples);
		return Result;
	}

	static FObject Particles(UParticleSystem* Asset)
	{
		const FObject Result = Describe(Asset);
		TArray<TArray<FString>> SystemParameters, DistributionParameters;
		Asset->GetParametersUtilized(SystemParameters, DistributionParameters);
		FValues Emitters;
		for (int32 Index = 0; Index < Asset->Emitters.Num(); ++Index)
		{
			UParticleEmitter* Emitter = Asset->Emitters[Index];
			const FObject Item = Describe(Emitter);
			Item->SetNumberField(TEXT("index"), Index);
			if (SystemParameters.IsValidIndex(Index))
			{
				Item->SetArrayField(TEXT("system_parameters"), Strings(SystemParameters[Index]));
			}
			if (DistributionParameters.IsValidIndex(Index))
			{
				Item->SetArrayField(TEXT("distribution_parameters"), Strings(DistributionParameters[Index]));
			}
			FValues LODs;
			if (Emitter)
			{
				for (UParticleLODLevel* Level : Emitter->LODLevels)
				{
					const FObject LOD = Describe(Level);
					if (Level)
					{
						LOD->SetNumberField(TEXT("level"), Level->Level);
						LOD->SetBoolField(TEXT("enabled"), Level->bEnabled);
						LOD->SetObjectField(TEXT("required"), Describe(Level->RequiredModule, 2));
						LOD->SetObjectField(TEXT("spawn"), Describe(Level->SpawnModule, 2));
						LOD->SetObjectField(TEXT("type_data"), Describe(Level->TypeDataModule, 2));
						FValues Modules;
						for (UParticleModule* Module : Level->Modules)
						{
							Modules.Add(MakeShared<FJsonValueObject>(Describe(Module, 2)));
						}
						LOD->SetArrayField(TEXT("modules"), Modules);
					}
					LODs.Add(MakeShared<FJsonValueObject>(LOD));
				}
			}
			Item->SetArrayField(TEXT("lods"), LODs);
			Emitters.Add(MakeShared<FJsonValueObject>(Item));
		}
		Result->SetArrayField(TEXT("emitters"), Emitters);
		return Result;
	}

	static void WriteReport(const TCHAR* Name, const FObject& Report)
	{
		FString Json;
		FJsonSerializer::Serialize(Report, TJsonWriterFactory<>::Create(&Json));
		const FString Output = CharacterPipelineQA::GetOutputDirectory(TEXT("QA/SparrowInventory")) / Name;
		if (!FFileHelper::SaveStringToFile(Json, *Output, FFileHelper::EEncodingOptions::ForceUTF8WithoutBOM))
		{
			UE_LOG(LogTemp, Error, TEXT("Sparrow configuration report write failed: %s"), *Output);
		}
	}

	template<typename T>
	static T* FindNode(const UAnimBlueprint* BlueprintAsset, const TCHAR* RelativePath)
	{
		return FindObject<T>(nullptr, *(BlueprintAsset->GetPathName() + TEXT(":") + RelativePath));
	}

	static bool Connect(UEdGraphPin* Source, UEdGraphPin* Target)
	{
		return Source && Target && (Source->LinkedTo.Contains(Target) ||
			Source->GetOwningNode()->GetSchema()->TryCreateConnection(Source, Target));
	}

	static bool ReplaceVelocityFunction(UK2Node_CallFunction* Node, UEdGraphPin* Movement)
	{
		UFunction* Function = ATopDownCombatCharacter::StaticClass()->FindFunctionByName(TEXT("GetLocomotionAnimationVelocity"));
		UEdGraphPin* Return = Node ? Node->FindPin(TEXT("ReturnValue")) : nullptr;
		if (!Function || !Return || !Movement)
		{
			return false;
		}
		if (Node->GetTargetFunction() == Function)
		{
			return Connect(Movement, Node->FindPin(TEXT("Movement")));
		}
		const TArray<UEdGraphPin*> Consumers = Return->LinkedTo;
		Node->Modify();
		if (UEdGraphPin* Owner = Node->FindPin(TEXT("self")))
		{
			Owner->BreakAllPinLinks();
		}
		Return->BreakAllPinLinks();
		Node->SetFromFunction(Function);
		Node->ReconstructNode();
		bool bConnected = Connect(Movement, Node->FindPin(TEXT("Movement")));
		for (UEdGraphPin* Consumer : Consumers)
		{
			bConnected &= Connect(Node->FindPin(TEXT("ReturnValue")), Consumer);
		}
		for (int32 Index = Node->Pins.Num() - 1; Index >= 0; --Index)
		{
			if (Node->Pins[Index]->bOrphanedPin)
			{
				Node->RemovePin(Node->Pins[Index]);
			}
		}
		return bConnected;
	}

	static bool ConfigureGaitRate(UAnimGraphNode_BlendSpacePlayer* Player)
	{
		Player->Modify();
		for (int32 Index = 0; Index < Player->ShowPinForProperties.Num(); ++Index)
		{
			if (Player->ShowPinForProperties[Index].PropertyName == TEXT("PlayRate"))
			{
				Player->SetPinVisibility(true, Index);
				break;
			}
		}
		UEdGraphPin* Rate = Player->FindPin(TEXT("PlayRate"));
		if (!Rate)
		{
			return false;
		}
		if (Rate->LinkedTo.Num() == 1)
		{
			const UK2Node_CallFunction* Divide = Cast<UK2Node_CallFunction>(Rate->LinkedTo[0]->GetOwningNode());
			const UEdGraphPin* Divisor = Divide ? Divide->FindPin(TEXT("B")) : nullptr;
			return Divide && Divide->FunctionReference.GetMemberName() == TEXT("Divide_DoubleDouble") &&
				Divisor && FMath::IsNearlyEqual(FCString::Atod(*Divisor->DefaultValue), 600.0);
		}
		if (!Rate->LinkedTo.IsEmpty())
		{
			return false;
		}
		UEdGraph* Graph = Player->GetGraph();
		Graph->Modify();
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
		Graph->GetSchema()->TrySetDefaultValue(*Divide->FindPinChecked(TEXT("B")), TEXT("600.0"));
		return Connect(Speed->FindPin(TEXT("Speed")), Divide->FindPin(TEXT("A"))) &&
			Connect(Divide->FindPin(TEXT("ReturnValue")), Rate);
	}

	static bool InstallFullBodySlot(UAnimBlueprint* BlueprintAsset, UAnimGraphNode_Root* Root)
	{
		UEdGraphPin* Result = Root->FindPin(TEXT("Result"));
		if (!Result || Result->LinkedTo.Num() != 1)
		{
			return false;
		}
		if (const UAnimGraphNode_Slot* Existing = Cast<UAnimGraphNode_Slot>(Result->LinkedTo[0]->GetOwningNode()))
		{
			return Existing->Node.SlotName == TEXT("SparrowFullBody");
		}
		UEdGraph* Graph = Root->GetGraph();
		Graph->Modify();
		Root->Modify();
		UEdGraphPin* Source = Result->LinkedTo[0];
		FGraphNodeCreator<UAnimGraphNode_Slot> Creator(*Graph);
		UAnimGraphNode_Slot* Slot = Creator.CreateNode();
		Slot->Node.SlotName = TEXT("SparrowFullBody");
		Slot->NodePosX = Root->NodePosX - 200;
		Slot->NodePosY = Root->NodePosY + 160;
		Creator.Finalize();
		Result->BreakAllPinLinks();
		if (!Connect(Source, Slot->FindPin(TEXT("Source"))) || !Connect(Slot->FindPin(TEXT("Pose")), Result))
		{
			Slot->BreakAllNodeLinks();
			FBlueprintEditorUtils::RemoveNode(BlueprintAsset, Slot, true);
			Connect(Source, Result);
			return false;
		}
		return true;
	}

	// native-inventory의 실제 Sparrow 노드 경로를 검증한 후 전용 사본만 수정한다.
	static FAutoConsoleCommand Configure(
		TEXT("SparrowAssetQA.Configure"), TEXT("Editor only: configure Sparrow AnimBP/primary montage copies in memory; never saves packages"),
		FConsoleCommandDelegate::CreateLambda([]()
		{
			const FObject Report = MakeShared<FJsonObject>();
			Report->SetBoolField(TEXT("passed"), false);
			Report->SetBoolField(TEXT("saved_packages"), false);
			Report->SetBoolField(TEXT("runtime_validation_pending"), true);
			Report->SetStringField(TEXT("animation_blueprint"), TEXT("/Game/TopDown/Characters/Sparrow/Animations/ABP_Sparrow_TopDown"));
			Report->SetStringField(TEXT("primary_montage"), TEXT("/Game/TopDown/Characters/Sparrow/Animations/AM_Sparrow_Primary"));
			const auto Fail = [&Report](const TCHAR* Error)
			{
				Report->SetStringField(TEXT("error"), Error);
				WriteReport(TEXT("sparrow-configuration.json"), Report);
				UE_LOG(LogTemp, Error, TEXT("SPARROW_CONFIGURATION_FAILED %s"), Error);
			};
			UAnimBlueprint* BlueprintAsset = LoadObject<UAnimBlueprint>(nullptr,
				TEXT("/Game/TopDown/Characters/Sparrow/Animations/ABP_Sparrow_TopDown.ABP_Sparrow_TopDown"));
			UAnimMontage* Montage = LoadObject<UAnimMontage>(nullptr,
				TEXT("/Game/TopDown/Characters/Sparrow/Animations/AM_Sparrow_Primary.AM_Sparrow_Primary"));
			if (!BlueprintAsset || !Montage || !BlueprintAsset->TargetSkeleton ||
				BlueprintAsset->TargetSkeleton != Montage->GetSkeleton() ||
				BlueprintAsset->TargetSkeleton->GetPathName() != TEXT("/Game/ParagonSparrow/Characters/Heroes/Sparrow/Meshes/Sparrow_Skeleton.Sparrow_Skeleton"))
			{
				Fail(TEXT("Duplicate original Sparrow AnimBP and primary montage into the declared copy paths first; both must retain Sparrow_Skeleton"));
				return;
			}
			const FString Ground = BlueprintAsset->GetPathName() + TEXT(":AnimGraph.AnimGraphNode_StateMachine_5.Ground Locomotion.");
			UAnimStateNode* Idle = FindObject<UAnimStateNode>(nullptr, *(Ground + TEXT("AnimStateNode_1")));
			UAnimStateNode* Run = FindObject<UAnimStateNode>(nullptr, *(Ground + TEXT("AnimStateNode_2")));
			UAnimStateTransitionNode* Start = FindObject<UAnimStateTransitionNode>(nullptr, *(Ground + TEXT("AnimStateTransitionNode_1")));
			UAnimStateTransitionNode* Stop = FindObject<UAnimStateTransitionNode>(nullptr, *(Ground + TEXT("AnimStateTransitionNode_6")));
			UAnimGraphNode_BlendSpacePlayer* Player = FindObject<UAnimGraphNode_BlendSpacePlayer>(nullptr,
				*(Ground + TEXT("AnimStateNode_2.Run.AnimGraphNode_BlendSpacePlayer_2")));
			UK2Node_CallFunction* Lean = FindObject<UK2Node_CallFunction>(nullptr,
				*(Ground + TEXT("AnimStateNode_2.Run.K2Node_CommutativeAssociativeBinaryOperator_79")));
			UAnimGraphNode_Root* Root = FindNode<UAnimGraphNode_Root>(BlueprintAsset, TEXT("AnimGraph.AnimGraphNode_Root_0"));
			UAnimGraphNode_RotationOffsetBlendSpace* AimOffset = FindNode<UAnimGraphNode_RotationOffsetBlendSpace>(BlueprintAsset,
				TEXT("AnimGraph.AnimGraphNode_RotationOffsetBlendSpace_53"));
			UK2Node_CallFunction* Velocity = FindNode<UK2Node_CallFunction>(BlueprintAsset, TEXT("EventGraph.K2Node_CallFunction_4"));
			UK2Node_CallFunction* Acceleration = FindNode<UK2Node_CallFunction>(BlueprintAsset, TEXT("EventGraph.K2Node_CallFunction_96"));
			UK2Node_VariableGet* Movement = FindNode<UK2Node_VariableGet>(BlueprintAsset, TEXT("EventGraph.K2Node_VariableGet_45"));
			UK2Node_DynamicCast* CharacterCast = FindNode<UK2Node_DynamicCast>(BlueprintAsset, TEXT("EventGraph.K2Node_DynamicCast_1"));
			UEdGraphNode* Valid = FindNode<UEdGraphNode>(BlueprintAsset, TEXT("EventGraph.K2Node_MacroInstance_0"));
			UEdGraphNode* SetInAir = FindNode<UEdGraphNode>(BlueprintAsset, TEXT("EventGraph.K2Node_VariableSet_27"));
			UEdGraphNode* SetLastRotation = FindNode<UEdGraphNode>(BlueprintAsset, TEXT("EventGraph.K2Node_VariableSet_65"));
			UEdGraphNode* SetAccelerating = FindNode<UEdGraphNode>(BlueprintAsset, TEXT("EventGraph.K2Node_VariableSet_653"));
			if (!Idle || !Run || !Start || !Stop || Start->GetPreviousState() != Idle || Stop->GetPreviousState() != Run ||
				!Player || !Player->Node.GetBlendSpace() || Player->Node.GetBlendSpace()->GetPathName() !=
				TEXT("/Game/ParagonSparrow/Characters/Heroes/Sparrow/Animations/Blendspaces/JogFwdSlopeLean.JogFwdSlopeLean") ||
				!Lean || !Lean->FindPin(TEXT("B")) || !Root || !AimOffset || !Velocity || !Acceleration || !Movement ||
				!CharacterCast || CharacterCast->TargetType != ACharacter::StaticClass() || !Valid || !SetInAir || !SetLastRotation || !SetAccelerating ||
				!Valid->FindPin(TEXT("Is Valid")) || !SetInAir->FindPin(TEXT("execute")) || !SetLastRotation->FindPin(TEXT("then")) ||
				!SetAccelerating->FindPin(TEXT("execute")) || Montage->SlotAnimTracks.Num() != 1 ||
				Montage->SlotAnimTracks[0].AnimTrack.AnimSegments.Num() != 1)
			{
				Fail(TEXT("Sparrow copy graph or primary montage no longer matches the inspected original structure"));
				return;
			}
			UEdGraphPin* RootResult = Root->FindPin(TEXT("Result"));
			UEdGraphPin* LeanFactor = Lean->FindPin(TEXT("B"));
			UEdGraphPin* BasePose = AimOffset->FindPin(TEXT("BasePose"));
			UEdGraphPin* AimPose = AimOffset->FindPin(TEXT("Pose"));
			if (!RootResult || RootResult->LinkedTo.Num() != 1 || !LeanFactor->LinkedTo.IsEmpty() || !BasePose || !AimPose ||
				(!AimPose->LinkedTo.IsEmpty() && BasePose->LinkedTo.Num() != 1))
			{
				Fail(TEXT("Sparrow output/aim/lean pin links do not match the original or previously configured copy"));
				return;
			}
			BlueprintAsset->Modify();
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
			// CharacterMovement 결과를 Speed보다 먼저 초기화하여 첫 프레임부터 같은 속도를 사용한다.
			Valid->Modify();
			CharacterCast->Modify();
			SetLastRotation->Modify();
			Valid->FindPinChecked(TEXT("Is Valid"))->BreakAllPinLinks();
			CharacterCast->FindPinChecked(TEXT("then"))->BreakAllPinLinks();
			SetLastRotation->FindPinChecked(TEXT("then"))->BreakAllPinLinks();
			bool bConfigured = Connect(Valid->FindPin(TEXT("Is Valid")), CharacterCast->FindPin(TEXT("execute"))) &&
				Connect(CharacterCast->FindPin(TEXT("then")), SetInAir->FindPin(TEXT("execute"))) &&
				Connect(SetLastRotation->FindPin(TEXT("then")), SetAccelerating->FindPin(TEXT("execute")));
			UEdGraphPin* MovementPin = Movement->FindPin(TEXT("CharacterMovement"));
			bConfigured &= ReplaceVelocityFunction(Velocity, MovementPin);
			bConfigured &= ReplaceVelocityFunction(Acceleration, MovementPin);
			bConfigured &= ConfigureGaitRate(Player);
			Lean->Modify();
			Lean->GetSchema()->TrySetDefaultValue(*LeanFactor, TEXT("-0.75"));
			// 클릭 이동은 pawn/camera 상대 조준 오프셋을 사용하지 않는다. 원본 locomotion pose를 그대로 연결한다.
			if (!AimPose->LinkedTo.IsEmpty())
			{
				AimOffset->Modify();
				UEdGraphPin* PoseSource = BasePose->LinkedTo[0];
				const TArray<UEdGraphPin*> Consumers = AimPose->LinkedTo;
				AimPose->BreakAllPinLinks();
				BasePose->BreakAllPinLinks();
				for (UEdGraphPin* Consumer : Consumers)
				{
					bConfigured &= Connect(PoseSource, Consumer);
				}
			}
			FValues RemovedNodes;
			for (const TCHAR* Name : { TEXT("K2Node_DynamicCast_0"), TEXT("K2Node_DynamicCast_2"), TEXT("K2Node_DynamicCast_3"),
				TEXT("K2Node_DynamicCast_133"), TEXT("K2Node_CallFunction_15"), TEXT("K2Node_CallFunction_16"),
				TEXT("K2Node_AddDelegate_8"), TEXT("K2Node_CustomEvent_113"), TEXT("K2Node_VariableSet_0"), TEXT("K2Node_VariableSet_532"),
				TEXT("K2Node_Event_13"), TEXT("K2Node_CallFunction_466"), TEXT("K2Node_Event_173"), TEXT("K2Node_Event_174"),
				TEXT("K2Node_CallFunction_1427"), TEXT("K2Node_CallFunction_1374") })
			{
				if (UEdGraphNode* Node = FindObject<UEdGraphNode>(nullptr, *(BlueprintAsset->GetPathName() + TEXT(":EventGraph.") + Name)))
				{
					RemovedNodes.Add(MakeShared<FJsonValueString>(Node->GetPathName()));
					Node->Modify();
					FBlueprintEditorUtils::RemoveNode(BlueprintAsset, Node, true);
				}
			}
			bConfigured &= InstallFullBodySlot(BlueprintAsset, Root);
			Montage->Modify();
			Montage->SlotAnimTracks[0].SlotName = TEXT("SparrowFullBody");
			const int32 RemovedSoundNotifies = Montage->Notifies.RemoveAll([](const FAnimNotifyEvent& Notify)
			{
				return Notify.Notify && Notify.Notify->IsA<UAnimNotify_PlaySound>();
			});
			Montage->RefreshCacheData();
			Montage->MarkPackageDirty();
			FBlueprintEditorUtils::MarkBlueprintAsStructurallyModified(BlueprintAsset);
			Report->SetBoolField(TEXT("passed"), bConfigured);
			Report->SetBoolField(TEXT("source_skeleton_save_forbidden"), true);
			Report->SetBoolField(TEXT("sequence_copy_required"), false);
			Report->SetBoolField(TEXT("aim_offset_bypassed"), AimPose->LinkedTo.IsEmpty());
			Report->SetStringField(TEXT("locomotion"), TEXT("Sparrow original Idle <-> Run; zero crossfade; velocity predicate; Speed/600 gait"));
			Report->SetNumberField(TEXT("original_rotation_rate"), 540.0);
			Report->SetNumberField(TEXT("target_rotation_rate"), 720.0);
			Report->SetNumberField(TEXT("lean_factor"), -0.75);
			Report->SetNumberField(TEXT("removed_primary_sound_notifies"), RemovedSoundNotifies);
			Report->SetArrayField(TEXT("removed_original_character_nodes"), RemovedNodes);
			Report->SetObjectField(TEXT("configured_primary_montage"), Animation(Montage));
			Report->SetObjectField(TEXT("configured_animation_blueprint"), Blueprint(BlueprintAsset));
			WriteReport(TEXT("sparrow-configuration.json"), Report);
			UE_LOG(LogTemp, Display, TEXT("SPARROW_CONFIGURATION passed=%d; copies changed in memory; compile/save only copy packages"), bConfigured);
		}));

	template<typename T>
	static T* PoseNode(UEdGraph* Graph, const TCHAR* Name)
	{
		if (T* Existing = FindObject<T>(Graph, Name)) { return Existing; }
		T* Node = NewObject<T>(Graph, FName(Name));
		Graph->AddNode(Node, false, false);
		Node->CreateNewGuid();
		Node->PostPlacedNewNode();
		return Node;
	}

	static bool BlendCombatPose(UEdGraph* Graph, UEdGraphPin* Armed, UEdGraphPin* Relaxed)
	{
		UAnimGraphNode_BlendListByBool* Blend = PoseNode<UAnimGraphNode_BlendListByBool>(Graph, TEXT("SparrowCombatPose"));
		const FStructProperty* NodeProperty = FindFProperty<FStructProperty>(Blend->GetClass(), TEXT("Node"));
		FArrayProperty* Times = NodeProperty ? FindFProperty<FArrayProperty>(NodeProperty->Struct, TEXT("BlendTime")) : nullptr;
		if (!Times || !Armed || !Relaxed) { return false; }
		FScriptArrayHelper Values(Times, Times->ContainerPtrToValuePtr<void>(&Blend->Node));
		if (Values.Num() != 2) { return false; }
		for (int32 Index = 0; Index < 2; ++Index) { *reinterpret_cast<float*>(Values.GetRawPtr(Index)) = 0.2f; }
		if (Blend->Pins.IsEmpty()) { Blend->AllocateDefaultPins(); }
		UK2Node_VariableGet* Combat = PoseNode<UK2Node_VariableGet>(Graph, TEXT("SparrowCombatPoseValue"));
		Combat->VariableReference.SetSelfMember(TEXT("UseCombatLocomotion"));
		if (Combat->Pins.IsEmpty()) { Combat->AllocateDefaultPins(); }
		UEdGraphPin* TruePose = Blend->FindPin(TEXT("BlendPose_0"));
		const TArray<UEdGraphPin*> Consumers = Armed->LinkedTo;
		bool bPassed = true;
		for (UEdGraphPin* Consumer : Consumers)
		{
			if (Consumer != TruePose)
			{
				Armed->BreakLinkTo(Consumer);
				bPassed &= Connect(Blend->FindPin(TEXT("Pose")), Consumer);
			}
		}
		return bPassed && Connect(Armed, TruePose) && Connect(Relaxed, Blend->FindPin(TEXT("BlendPose_1"))) &&
			Connect(Combat->FindPin(TEXT("UseCombatLocomotion")), Blend->FindPin(TEXT("bActiveValue")));
	}

	// 사용자 요청에 따른 평상시 자세 변형이다. 원작의 상태 전환 복원을 의미하지 않는다.
	static FAutoConsoleCommand ConfigurePose(
		TEXT("SparrowAssetQA.ConfigurePose"), TEXT("Editor only: configure owned relaxed pose copies; never saves source packages"),
		FConsoleCommandWithArgsDelegate::CreateLambda([](const TArray<FString>& Args)
		{
			const FObject Report = MakeShared<FJsonObject>();
			Report->SetBoolField(TEXT("passed"), false);
			Report->SetBoolField(TEXT("saved_packages"), false);
			const auto Fail = [&Report](const TCHAR* Error)
			{
				Report->SetStringField(TEXT("error"), Error);
				WriteReport(TEXT("sparrow-pose-configuration.json"), Report);
			};
			const FString Destination = TEXT("/Game/TopDown/Characters/Sparrow/Animations/");
			UAnimBlueprint* Asset = LoadObject<UAnimBlueprint>(nullptr, *(Destination + TEXT("ABP_Sparrow_TopDown.ABP_Sparrow_TopDown")));
			UAnimSequence* Idle = LoadObject<UAnimSequence>(nullptr, *(Destination + TEXT("A_Sparrow_RelaxedIdle.A_Sparrow_RelaxedIdle")));
			UBlendSpace* Move = LoadObject<UBlendSpace>(nullptr, *(Destination + TEXT("BS_Sparrow_RelaxedMove.BS_Sparrow_RelaxedMove")));
			UBlendSpace* Source = LoadObject<UBlendSpace>(nullptr, TEXT("/Game/ParagonSparrow/Characters/Heroes/Sparrow/Animations/Blendspaces/SprintFwdSlopeLean.SprintFwdSlopeLean"));
			if (Args.Num() != 2 || !Asset || !Idle || !Move || !Source || Move->GetBlendSamples().Num() != Source->GetBlendSamples().Num())
			{
				Fail(TEXT("Missing declared owned pose assets or frame arguments")); return;
			}
			const int32 Start = FCString::Atoi(*Args[0]);
			const int32 End = FCString::Atoi(*Args[1]);
			const int32 Frames = Idle->GetDataModelInterface()->GetNumberOfFrames();
			UAnimSequence* OriginalIdle = LoadObject<UAnimSequence>(nullptr,
				TEXT("/Game/ParagonSparrow/Characters/Heroes/Sparrow/Animations/idle_relaxed.idle_relaxed"));
			if (Start <= 0 || End <= Start || (Frames != End - Start && Frames <= End))
			{
				Fail(TEXT("Relaxed idle frame range does not match original or already trimmed copy")); return;
			}
			if (Frames != End - Start)
			{
				IAnimationDataController& Controller = Idle->GetController();
				Controller.OpenBracket(FText::FromString(TEXT("Sparrow relaxed idle source segment")), false);
				Controller.ResizeInFrames(FFrameNumber(Frames - Start), FFrameNumber(0), FFrameNumber(Start), false);
				Controller.ResizeInFrames(FFrameNumber(End - Start), FFrameNumber(End - Start), FFrameNumber(Frames - Start), false);
				Controller.CloseBracket(false);
			}
			if (Idle->GetDataModelInterface()->GetNumberOfFrames() != End - Start)
			{
				Fail(TEXT("Animation controller did not crop the declared segment")); return;
			}
			bool bPassed = true;
			if (!OriginalIdle || End > OriginalIdle->GetDataModelInterface()->GetNumberOfFrames())
			{
				Fail(TEXT("Selected frames exceed original relaxed idle")); return;
			}
			// ResizeInFrames는 길이와 커브만 바꾼다. 원본 구간의 본 키도 명시적으로 복사한다.
			TArray<FName> TrackNames;
			TArray<FFrameNumber> SelectedFrames;
			OriginalIdle->GetDataModelInterface()->GetBoneTrackNames(TrackNames);
			for (int32 Frame = Start; Frame <= End; ++Frame) { SelectedFrames.Add(FFrameNumber(Frame)); }
			IAnimationDataController& IdleController = Idle->GetController();
			IdleController.OpenBracket(FText::FromString(TEXT("Copy selected source bone keys")), false);
			for (const FName Track : TrackNames)
			{
				TArray<FTransform> Transforms;
				TArray<FVector> Positions, Scales;
				TArray<FQuat> Rotations;
				OriginalIdle->GetDataModelInterface()->GetBoneTrackTransforms(Track, SelectedFrames, Transforms);
				for (const FTransform& Transform : Transforms)
				{
					Positions.Add(Transform.GetTranslation());
					Rotations.Add(Transform.GetRotation());
					Scales.Add(Transform.GetScale3D());
				}
				bPassed &= Transforms.Num() == SelectedFrames.Num() && IdleController.SetBoneTrackKeys(Track, Positions, Rotations, Scales, false);
			}
			IdleController.CloseBracket(false);
			for (int32 Index = 0; Index < Source->GetBlendSamples().Num(); ++Index)
			{
				const FBlendSample& Sample = Source->GetBlendSamples()[Index];
				const FString Name = TEXT("A_Sparrow_Move_") + GetNameSafe(Sample.Animation);
				UAnimSequence* Copy = LoadObject<UAnimSequence>(nullptr, *(Destination + Name + TEXT(".") + Name));
				bPassed &= Copy && Move->ReplaceSampleAnimation(Index, Copy) &&
					Move->GetBlendSamples()[Index].SampleValue == Sample.SampleValue;
			}
			if (!bPassed) { Fail(TEXT("Owned movement sample copies do not match source blendspace")); return; }
			const FString Ground = Asset->GetPathName() + TEXT(":AnimGraph.AnimGraphNode_StateMachine_5.Ground Locomotion.");
			UAnimStateNode* IdleState = FindObject<UAnimStateNode>(nullptr, *(Ground + TEXT("AnimStateNode_1")));
			UAnimStateNode* RunState = FindObject<UAnimStateNode>(nullptr, *(Ground + TEXT("AnimStateNode_2")));
			UAnimGraphNode_BlendSpacePlayer* ArmedMove = FindObject<UAnimGraphNode_BlendSpacePlayer>(nullptr,
				*(Ground + TEXT("AnimStateNode_2.Run.AnimGraphNode_BlendSpacePlayer_2")));
			UEdGraphNode* SetAccelerating = FindNode<UEdGraphNode>(Asset, TEXT("EventGraph.K2Node_VariableSet_653"));
			if (!IdleState || !RunState || !ArmedMove || !SetAccelerating) { Fail(TEXT("Inspected Sparrow locomotion graph changed")); return; }
			UAnimGraphNode_SequencePlayer* ArmedIdle = nullptr;
			for (UEdGraphNode* Node : IdleState->BoundGraph->Nodes)
			{
				UAnimGraphNode_SequencePlayer* Player = Cast<UAnimGraphNode_SequencePlayer>(Node);
				if (Player && Player->Node.GetSequence() && Player->Node.GetSequence()->GetName() == TEXT("idle")) { ArmedIdle = Player; }
			}
			if (!ArmedIdle) { Fail(TEXT("Original armed idle player missing")); return; }
			FEdGraphPinType BoolType;
			BoolType.PinCategory = UEdGraphSchema_K2::PC_Boolean;
			if (FBlueprintEditorUtils::FindNewVariableIndex(Asset, TEXT("UseCombatLocomotion")) == INDEX_NONE)
			{
				bPassed &= FBlueprintEditorUtils::AddMemberVariable(Asset, TEXT("UseCombatLocomotion"), BoolType, TEXT("false"));
			}
			UEdGraph* Events = SetAccelerating->GetGraph();
			UK2Node_CallFunction* Owner = PoseNode<UK2Node_CallFunction>(Events, TEXT("SparrowPoseOwner"));
			Owner->SetFromFunction(UAnimInstance::StaticClass()->FindFunctionByName(TEXT("GetOwningActor")));
			if (Owner->Pins.IsEmpty()) { Owner->AllocateDefaultPins(); }
			UK2Node_CallFunction* Predicate = PoseNode<UK2Node_CallFunction>(Events, TEXT("SparrowPosePredicate"));
			Predicate->SetFromFunction(ASparrowCharacter::StaticClass()->FindFunctionByName(TEXT("ShouldUseCombatLocomotion")));
			if (Predicate->Pins.IsEmpty()) { Predicate->AllocateDefaultPins(); }
			UK2Node_VariableSet* SetCombat = PoseNode<UK2Node_VariableSet>(Events, TEXT("SparrowPoseSetCombat"));
			SetCombat->VariableReference.SetSelfMember(TEXT("UseCombatLocomotion"));
			if (SetCombat->Pins.IsEmpty()) { SetCombat->AllocateDefaultPins(); }
			UEdGraphPin* Then = SetAccelerating->FindPin(TEXT("then"));
			if (!Then) { Fail(TEXT("Animation update execution pin missing")); return; }
			const TArray<UEdGraphPin*> Consumers = Then->LinkedTo;
			for (UEdGraphPin* Consumer : Consumers)
			{
				if (Consumer != SetCombat->FindPin(TEXT("execute")))
				{
					Then->BreakLinkTo(Consumer);
					bPassed &= Connect(SetCombat->FindPin(TEXT("then")), Consumer);
				}
			}
			bPassed &= Connect(Then, SetCombat->FindPin(TEXT("execute"))) &&
				Connect(Owner->FindPin(TEXT("ReturnValue")), Predicate->FindPin(TEXT("CharacterOwner"))) &&
				Connect(Predicate->FindPin(TEXT("ReturnValue")), SetCombat->FindPin(TEXT("UseCombatLocomotion")));
			UAnimGraphNode_SequencePlayer* RelaxedIdle = PoseNode<UAnimGraphNode_SequencePlayer>(IdleState->BoundGraph, TEXT("SparrowRelaxedIdle"));
			RelaxedIdle->Node.SetSequence(Idle);
			RelaxedIdle->Node.SetLoopAnimation(true);
			if (RelaxedIdle->Pins.IsEmpty()) { RelaxedIdle->AllocateDefaultPins(); }
			UAnimGraphNode_BlendSpacePlayer* RelaxedMove = PoseNode<UAnimGraphNode_BlendSpacePlayer>(RunState->BoundGraph, TEXT("SparrowRelaxedMove"));
			RelaxedMove->Node.SetBlendSpace(Move);
			if (RelaxedMove->Pins.IsEmpty()) { RelaxedMove->AllocateDefaultPins(); }
			for (const TCHAR* Axis : { TEXT("X"), TEXT("Y") })
			{
				UEdGraphPin* Original = ArmedMove->FindPin(Axis);
				UEdGraphPin* Copy = RelaxedMove->FindPin(Axis);
				if (!Original || !Copy) { bPassed = false; continue; }
				Copy->DefaultValue = Original->DefaultValue;
				for (UEdGraphPin* Link : Original->LinkedTo) { bPassed &= Connect(Link, Copy); }
			}
			bPassed &= ConfigureGaitRate(RelaxedMove);
			bPassed &= BlendCombatPose(IdleState->BoundGraph, ArmedIdle->FindPin(TEXT("Pose")), RelaxedIdle->FindPin(TEXT("Pose")));
			bPassed &= BlendCombatPose(RunState->BoundGraph, ArmedMove->FindPin(TEXT("Pose")), RelaxedMove->FindPin(TEXT("Pose")));
			FBlueprintEditorUtils::MarkBlueprintAsStructurallyModified(Asset);
			Idle->MarkPackageDirty();
			Move->MarkPackageDirty();
			Report->SetBoolField(TEXT("passed"), bPassed);
			Report->SetNumberField(TEXT("start_frame"), Start);
			Report->SetNumberField(TEXT("end_frame"), End);
			Report->SetNumberField(TEXT("idle_length"), Idle->GetPlayLength());
			Report->SetObjectField(TEXT("animation_blueprint"), Blueprint(Asset));
			WriteReport(TEXT("sparrow-pose-configuration.json"), Report);
		}));

	static FAutoConsoleCommand Dump(
		TEXT("SparrowAssetQA.Dump"), TEXT("Editor only: read-only Sparrow source asset paths; writes sparrow-native-inventory.json"),
		FConsoleCommandWithArgsDelegate::CreateLambda([](const TArray<FString>& Args)
		{
			const FObject Report = MakeShared<FJsonObject>();
			FValues Assets;
			bool bPassed = !Args.IsEmpty();
			for (const FString& Path : Args)
			{
				if (!Path.StartsWith(TEXT("/Game/ParagonSparrow/")) && !Path.StartsWith(TEXT("/Game/TopDown/Characters/Sparrow/")))
				{
					bPassed = false;
					continue;
				}
				UObject* Asset = LoadObject<UObject>(nullptr, *Path);
				FObject Item = Describe(Asset);
				Item->SetStringField(TEXT("requested_path"), Path);
				if (UBlueprint* BlueprintAsset = Cast<UBlueprint>(Asset))
				{
					Item = Blueprint(BlueprintAsset);
				}
				else if (USkeletalMesh* MeshAsset = Cast<USkeletalMesh>(Asset))
				{
					Item = Mesh(MeshAsset);
				}
				else if (UAnimSequenceBase* AnimationAsset = Cast<UAnimSequenceBase>(Asset))
				{
					Item = Animation(AnimationAsset);
				}
				else if (UBlendSpace* BlendAsset = Cast<UBlendSpace>(Asset))
				{
					Item = BlendSpace(BlendAsset);
				}
				else if (UParticleSystem* ParticleAsset = Cast<UParticleSystem>(Asset))
				{
					Item = Particles(ParticleAsset);
				}
				Item->SetStringField(TEXT("requested_path"), Path);
				bPassed &= Asset != nullptr;
				Assets.Add(MakeShared<FJsonValueObject>(Item));
			}
			Report->SetBoolField(TEXT("passed"), bPassed);
			Report->SetBoolField(TEXT("read_only"), true);
			Report->SetArrayField(TEXT("assets"), Assets);
			FString Json;
			FJsonSerializer::Serialize(Report, TJsonWriterFactory<>::Create(&Json));
			const FString Output = CharacterPipelineQA::GetOutputDirectory(TEXT("QA/SparrowInventory")) / TEXT("sparrow-native-inventory.json");
			const bool bSaved = FFileHelper::SaveStringToFile(Json, *Output, FFileHelper::EEncodingOptions::ForceUTF8WithoutBOM);
			UE_LOG(LogTemp, Display, TEXT("SPARROW_NATIVE_INVENTORY passed=%d saved=%d assets=%d path=%s"), bPassed, bSaved, Assets.Num(), *Output);
		}));
}

#endif
