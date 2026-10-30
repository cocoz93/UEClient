#if WITH_EDITOR && WITH_DEV_AUTOMATION_TESTS

#include "CharacterPipelineQA.h"
#include "../CharacterSkillComponent.h"
#include "../TopDownCombatCharacter.h"
#include "../SparrowArrow.h"
#include "../KwangTrainingDummy.h"
#include "Animation/AnimInstance.h"
#include "Animation/AnimMontage.h"
#include "Animation/AnimClassInterface.h"
#include "Animation/AnimNode_StateMachine.h"
#include "Animation/AnimStateMachineTypes.h"
#include "Components/AudioComponent.h"
#include "Components/SkeletalMeshComponent.h"
#include "ClothingSystemRuntimeTypes.h"
#include "Rendering/SkeletalMeshRenderData.h"
#include "Components/StaticMeshComponent.h"
#include "Dom/JsonObject.h"
#include "EngineUtils.h"
#include "Engine/GameViewportClient.h"
#include "UnrealClient.h"
#include "GameFramework/CharacterMovementComponent.h"
#include "GameFramework/PlayerController.h"
#include "HAL/IConsoleManager.h"
#include "Kismet/GameplayStatics.h"
#include "Misc/FileHelper.h"
#include "NavigationSystem.h"
#include "Particles/ParticleSystem.h"
#include "Particles/ParticleEmitter.h"
#include "Particles/ParticleLODLevel.h"
#include "Particles/ParticleModuleRequired.h"
#include "Particles/TypeData/ParticleModuleTypeDataMesh.h"
#include "Engine/StaticMesh.h"
#include "Materials/MaterialInterface.h"
#include "Particles/ParticleSystemComponent.h"
#include "ParticleEmitterInstances.h"
#include "Serialization/JsonSerializer.h"
#include "UObject/UnrealType.h"

static FAutoConsoleCommandWithWorldAndArgs ProbeSparrowGround(
	TEXT("SparrowQA.Ground"), TEXT("PIE only: filename token x y reference_z"),
	FConsoleCommandWithWorldAndArgsDelegate::CreateLambda([](const TArray<FString>& Args, UWorld* World)
	{
		if (!World || World->WorldType != EWorldType::PIE || Args.Num() != 4 ||
			Args[0].Contains(TEXT("/")) || Args[0].Contains(TEXT("\\")) || Args[0].Contains(TEXT(".."))) { return; }
		ACharacter* Character = UGameplayStatics::GetPlayerCharacter(World, 0);
		APlayerController* Controller = UGameplayStatics::GetPlayerController(World, 0);
		if (!Character || !Controller) { return; }
		const FVector Point(FCString::Atod(*Args[1]), FCString::Atod(*Args[2]), FCString::Atod(*Args[3]));
		FCollisionQueryParams Query(SCENE_QUERY_STAT(SparrowQAGround), true, Character);
		for (TActorIterator<APawn> Iterator(World); Iterator; ++Iterator) { Query.AddIgnoredActor(*Iterator); }
		for (TActorIterator<AKwangTrainingDummy> Iterator(World); Iterator; ++Iterator) { Query.AddIgnoredActor(*Iterator); }
		FHitResult Hit;
		const bool bGround = World->LineTraceSingleByChannel(Hit, Point + FVector(0, 0, 1200),
			Point - FVector(0, 0, 2400), ECC_Visibility, Query);
		UNavigationSystemV1* Navigation = FNavigationSystem::GetCurrent<UNavigationSystemV1>(World);
		FNavLocation Nav;
		const bool bProjected = bGround && Navigation && Navigation->ProjectPointToNavigation(Hit.ImpactPoint, Nav,
			FVector(100, 100, 250), &Character->GetNavAgentPropertiesRef());
		const auto Position = [](const FVector& Value)
		{
			TSharedRef<FJsonObject> Result = MakeShared<FJsonObject>();
			Result->SetNumberField(TEXT("x"), Value.X);
			Result->SetNumberField(TEXT("y"), Value.Y);
			Result->SetNumberField(TEXT("z"), Value.Z);
			return Result;
		};
		TSharedRef<FJsonObject> Json = MakeShared<FJsonObject>();
		Json->SetBoolField(TEXT("ground_hit"), bGround);
		Json->SetObjectField(TEXT("ground"), Position(Hit.ImpactPoint));
		Json->SetNumberField(TEXT("normal_z"), Hit.ImpactNormal.Z);
		Json->SetStringField(TEXT("ground_actor"), GetNameSafe(Hit.GetActor()));
		Json->SetBoolField(TEXT("navigation_projected"), bProjected);
		Json->SetObjectField(TEXT("nav"), Position(Nav.Location));
		FVector2D RequestedScreen = FVector2D::ZeroVector;
		const bool bScreen = bGround && Controller->ProjectWorldLocationToScreen(Hit.ImpactPoint, RequestedScreen);
		float MouseX = 0, MouseY = 0;
		const bool bMouse = Controller->GetMousePosition(MouseX, MouseY);
		int32 ViewX = 0, ViewY = 0;
		Controller->GetViewportSize(ViewX, ViewY);
		TSharedRef<FJsonObject> Requested = MakeShared<FJsonObject>();
		Requested->SetBoolField(TEXT("valid"), bScreen);
		Requested->SetNumberField(TEXT("x"), RequestedScreen.X);
		Requested->SetNumberField(TEXT("y"), RequestedScreen.Y);
		Json->SetObjectField(TEXT("requested_screen"), Requested);
		TSharedRef<FJsonObject> Mouse = MakeShared<FJsonObject>();
		Mouse->SetBoolField(TEXT("valid"), bMouse);
		Mouse->SetNumberField(TEXT("x"), MouseX);
		Mouse->SetNumberField(TEXT("y"), MouseY);
		Json->SetObjectField(TEXT("cursor_screen"), Mouse);
		TSharedRef<FJsonObject> Viewport = MakeShared<FJsonObject>();
		Viewport->SetNumberField(TEXT("x"), ViewX);
		Viewport->SetNumberField(TEXT("y"), ViewY);
		Json->SetObjectField(TEXT("viewport"), Viewport);
		double OnePixelGroundStep = 0;
		for (const FVector2D& PixelOffset : { FVector2D(1, 0), FVector2D(-1, 0), FVector2D(0, 1), FVector2D(0, -1) })
		{
			FVector RayOrigin, RayDirection;
			FHitResult Adjacent;
			if (bScreen && Controller->DeprojectScreenPositionToWorld(RequestedScreen.X + PixelOffset.X,
				RequestedScreen.Y + PixelOffset.Y, RayOrigin, RayDirection) &&
				World->LineTraceSingleByChannel(Adjacent, RayOrigin, RayOrigin + RayDirection * 100000, ECC_Visibility, Query))
			{
				OnePixelGroundStep = FMath::Max(OnePixelGroundStep, FVector::Distance(Adjacent.ImpactPoint, Hit.ImpactPoint));
			}
		}
		Json->SetNumberField(TEXT("one_pixel_ground_step_cm"), OnePixelGroundStep);
		FHitResult CursorHit;
		const bool bCursor = Controller->GetHitResultUnderCursor(ECC_Visibility, true, CursorHit);
		FNavLocation CursorNav;
		const bool bCursorNav = bCursor && Navigation && Navigation->ProjectPointToNavigation(CursorHit.ImpactPoint, CursorNav,
			FVector(100, 100, 250), &Character->GetNavAgentPropertiesRef());
		TSharedRef<FJsonObject> Cursor = Position(CursorHit.ImpactPoint);
		Cursor->SetBoolField(TEXT("hit"), bCursor);
		Cursor->SetStringField(TEXT("actor"), GetNameSafe(CursorHit.GetActor()));
		Json->SetObjectField(TEXT("cursor_visibility_hit"), Cursor);
		Json->SetBoolField(TEXT("cursor_navigation_projected"), bCursorNav);
		Json->SetObjectField(TEXT("cursor_nav"), Position(CursorNav.Location));
		FString Text;
		FJsonSerializer::Serialize(Json, TJsonWriterFactory<>::Create(&Text));
		FFileHelper::SaveStringToFile(Text,
			*(CharacterPipelineQA::GetOutputDirectory(TEXT("QA/Sparrow")) / (Args[0] + TEXT(".json"))),
			FFileHelper::EEncodingOptions::ForceUTF8WithoutBOM);
	}));

// PIE 내부 상태만 읽으며 물리 마우스·키보드·창 포커스는 조작하지 않는다.
static FAutoConsoleCommandWithWorldAndArgs SnapshotSparrowState(
	TEXT("SparrowQA.State"), TEXT("PIE only: sample filename token"),
	FConsoleCommandWithWorldAndArgsDelegate::CreateLambda([](const TArray<FString>& Args, UWorld* World)
	{
		if (!World || World->WorldType != EWorldType::PIE || Args.Num() != 1 ||
			Args[0].Contains(TEXT("/")) || Args[0].Contains(TEXT("\\")) || Args[0].Contains(TEXT("..")))
		{
			return;
		}
		ATopDownCombatCharacter* Character = Cast<ATopDownCombatCharacter>(UGameplayStatics::GetPlayerCharacter(World, 0));
		UCharacterSkillComponent* Skills = Character ? Character->GetSkills() : nullptr;
		UAnimInstance* Anim = Character && Character->GetMesh() ? Character->GetMesh()->GetAnimInstance() : nullptr;
		if (!Skills || !Anim) { return; }
		TSharedRef<FJsonObject> Json = MakeShared<FJsonObject>();
		Json->SetNumberField(TEXT("time"), World->GetTimeSeconds());
		const FBoolProperty* PoseProperty = FindFProperty<FBoolProperty>(Anim->GetClass(), TEXT("UseCombatLocomotion"));
		Json->SetBoolField(TEXT("combat_locomotion"), PoseProperty && PoseProperty->GetPropertyValue_InContainer(Anim));
		const FVector DrawHand = Character->GetMesh()->GetSocketTransform(TEXT("hand_r"), RTS_Component).GetLocation();
		const FVector Head = Character->GetMesh()->GetSocketTransform(TEXT("head"), RTS_Component).GetLocation();
		Json->SetNumberField(TEXT("head_minus_draw_hand_z"), Head.Z - DrawHand.Z);
		// QA에서만 동기화해 실제 천 입자를 월드 좌표로 측정한다.
		USkeletalMeshComponent* Mesh = Character->GetMesh();
		const double HeadWorldZ = Mesh->GetSocketLocation(TEXT("head")).Z;
		TArray<TSharedPtr<FJsonValue>> Cloths;
		Mesh->WaitForExistingParallelClothSimulation_GameThread();
		for (const auto& Pair : Mesh->GetCurrentClothingData_AnyThread())
		{
			TSharedRef<FJsonObject> Cloth = MakeShared<FJsonObject>();
			double MaxZ = TNumericLimits<double>::Lowest();
			double MaxRadius = 0;
			TArray<double> Heights;
			for (const FVector3f& Position : Pair.Value.Positions)
			{
				// GPU 스키닝과 같은 cloth-to-component-to-world 경로를 사용한다.
				const FVector WorldPosition = Mesh->GetComponentTransform().TransformPosition(
					Pair.Value.ComponentRelativeTransform.TransformPosition(FVector(Position)));
				MaxZ = FMath::Max(MaxZ, WorldPosition.Z);
				MaxRadius = FMath::Max(MaxRadius, FVector::Dist2D(WorldPosition, Character->GetActorLocation()));
				Heights.Add(WorldPosition.Z - HeadWorldZ);
			}
			Heights.Sort();
			Cloth->SetNumberField(TEXT("index"), Pair.Key);
			Cloth->SetNumberField(TEXT("vertices"), Heights.Num());
			Cloth->SetNumberField(TEXT("max_above_head_cm"), Heights.IsEmpty() ? 0 : MaxZ - HeadWorldZ);
			Cloth->SetNumberField(TEXT("p95_above_head_cm"), Heights.IsEmpty() ? 0 : Heights[FMath::FloorToInt((Heights.Num() - 1) * 0.95)]);
			Cloth->SetNumberField(TEXT("max_radius_cm"), MaxRadius);
			Cloths.Add(MakeShared<FJsonValueObject>(Cloth));
		}
		Json->SetArrayField(TEXT("cloth"), Cloths);
		Json->SetBoolField(TEXT("cloth_suspended"), Mesh->IsClothingSimulationSuspended());
		Json->SetBoolField(TEXT("cloth_disabled"), Mesh->bDisableClothSimulation != 0);
		const int32 ClothLOD = Mesh->GetPredictedLODLevel();
		const FSkeletalMeshRenderData* RenderData = Mesh->GetSkeletalMeshRenderData();
		Json->SetNumberField(TEXT("cloth_lod"), ClothLOD);
		Json->SetBoolField(TEXT("cloth_lod_has_data"), RenderData && RenderData->LODRenderData.IsValidIndex(ClothLOD) &&
			RenderData->LODRenderData[ClothLOD].HasClothData());
		Json->SetNumberField(TEXT("cloth_rotation_threshold"), Mesh->GetTeleportRotationThreshold());
		UGameViewportClient* ViewportClient = World->GetGameViewport();
		const FIntPoint ViewportSize = ViewportClient && ViewportClient->Viewport ? ViewportClient->Viewport->GetSizeXY() : FIntPoint::ZeroValue;
		TArray<TSharedPtr<FJsonValue>> Dimensions;
		Dimensions.Add(MakeShared<FJsonValueNumber>(ViewportSize.X));
		Dimensions.Add(MakeShared<FJsonValueNumber>(ViewportSize.Y));
		Json->SetArrayField(TEXT("viewport_size"), Dimensions);
		Json->SetBoolField(TEXT("viewport_lighting"), ViewportClient && ViewportClient->GetEngineShowFlags()->Lighting);
		Json->SetBoolField(TEXT("viewport_wireframe"), ViewportClient && ViewportClient->GetEngineShowFlags()->Wireframe);
		Json->SetNumberField(TEXT("speed"), Character->GetVelocity().Size2D());
		Json->SetBoolField(TEXT("attacking"), Character->IsAttacking());
		Json->SetBoolField(TEXT("casting"), Skills->IsCasting());
		Json->SetBoolField(TEXT("combat_busy"), Character->IsCombatBusy());
		Json->SetNumberField(TEXT("active_skill"), Skills->GetActiveSkillNumber());
		Json->SetStringField(TEXT("feedback"), Skills->GetInputFeedback());
		Json->SetBoolField(TEXT("orient_to_movement"), Character->GetCharacterMovement()->bOrientRotationToMovement);
		Json->SetNumberField(TEXT("root_motion_mode"), static_cast<int32>(Anim->RootMotionMode));
		UAnimMontage* Montage = Anim->GetCurrentActiveMontage();
		Json->SetStringField(TEXT("montage"), Montage ? Montage->GetName() : TEXT(""));
		Json->SetNumberField(TEXT("montage_position"), Montage ? Anim->Montage_GetPosition(Montage) : 0.0f);
		const FAnimSegment* Segment = Montage && !Montage->SlotAnimTracks.IsEmpty() ?
			Montage->SlotAnimTracks[0].AnimTrack.GetSegmentAtTime(Anim->Montage_GetPosition(Montage)) : nullptr;
		Json->SetStringField(TEXT("montage_sequence"), Segment ? GetNameSafe(Segment->GetAnimReference().Get()) : TEXT(""));
		Json->SetStringField(TEXT("montage_slot"), Montage && !Montage->SlotAnimTracks.IsEmpty() ?
			Montage->SlotAnimTracks[0].SlotName.ToString() : TEXT(""));
		TArray<TSharedPtr<FJsonValue>> Slots;
		for (int32 Index = 0; Index < Skills->GetSkillCount(); ++Index)
		{
			TSharedRef<FJsonObject> Slot = MakeShared<FJsonObject>();
			Slot->SetNumberField(TEXT("slot"), Index);
			Slot->SetStringField(TEXT("name"), Skills->GetSkillDisplayName(Index).ToString());
			Slot->SetBoolField(TEXT("passive"), Skills->IsSkillPassive(Index));
			Slot->SetNumberField(TEXT("cooldown"), Skills->GetSlotCooldownRemaining(Index));
			Slot->SetStringField(TEXT("status"), Skills->GetSkillStatusText(Index).ToString());
			Slots.Add(MakeShared<FJsonValueObject>(Slot));
		}
		Json->SetArrayField(TEXT("slots"), Slots);
		TArray<TSharedPtr<FJsonValue>> Effects;
		int32 AudioComponents = 0;
		for (TObjectIterator<UAudioComponent> Iterator; Iterator; ++Iterator)
		{
			if (IsValid(*Iterator) && Iterator->GetWorld() == World && Iterator->IsRegistered())
			{
				++AudioComponents;
			}
		}
		for (TObjectIterator<UParticleSystemComponent> Iterator; Iterator; ++Iterator)
		{
			UParticleSystemComponent* Particle = *Iterator;
			if (!IsValid(Particle) || Particle->GetWorld() != World || !Particle->IsRegistered() ||
				!Particle->Template) { continue; }
			TSharedRef<FJsonObject> Effect = MakeShared<FJsonObject>();
			Effect->SetStringField(TEXT("template"), Particle->Template ? Particle->Template->GetPathName() : TEXT(""));
			Effect->SetBoolField(TEXT("active"), Particle->IsActive());
			Effect->SetNumberField(TEXT("particles"), Particle->GetNumActiveParticles());
			Effect->SetNumberField(TEXT("lod"), Particle->GetCurrentLODIndex());
			Particle->ForceAsyncWorkCompletion(UParticleSystemComponent::SILENT);
			TArray<TSharedPtr<FJsonValue>> RenderEmitters;
			for (const FParticleEmitterInstance* Instance : Particle->EmitterInstances)
			{
				if (!Instance || !Instance->SpriteTemplate || Instance->ActiveParticles <= 0) { continue; }
				const UParticleLODLevel* LOD = Instance->SpriteTemplate->GetLODLevel(Particle->GetCurrentLODIndex());
				if (!LOD || !LOD->RequiredModule) { continue; }
				TSharedRef<FJsonObject> Emitter = MakeShared<FJsonObject>();
				Emitter->SetStringField(TEXT("name"), Instance->SpriteTemplate->EmitterName.ToString());
				Emitter->SetNumberField(TEXT("particles"), Instance->ActiveParticles);
				Emitter->SetBoolField(TEXT("renders_surface"), Instance->SpriteTemplate->EmitterRenderMode != ERM_LightsOnly &&
					Instance->SpriteTemplate->EmitterRenderMode != ERM_None);
				TArray<TSharedPtr<FJsonValue>> Materials;
				const UParticleModuleTypeDataMesh* MeshData = Cast<UParticleModuleTypeDataMesh>(LOD->TypeDataModule);
				if (MeshData)
				{
					// 렌더러와 같은 경로를 사용해 MeshMaterial 모듈·런타임 덮어쓰기도 반영한다.
					TArray<UMaterialInterface*, TInlineAllocator<2>> ResolvedMaterials;
					static_cast<const FParticleMeshEmitterInstance*>(Instance)->GetMeshMaterials(ResolvedMaterials, LOD);
					for (const UMaterialInterface* Material : ResolvedMaterials)
					{
						Materials.Add(MakeShared<FJsonValueString>(GetPathNameSafe(Material)));
					}
				}
				else
				{
					Materials.Add(MakeShared<FJsonValueString>(GetPathNameSafe(Instance->CurrentMaterial ?
						Instance->CurrentMaterial : LOD->RequiredModule->Material.Get())));
				}
				Emitter->SetArrayField(TEXT("materials"), Materials);
				RenderEmitters.Add(MakeShared<FJsonValueObject>(Emitter));
			}
			Effect->SetArrayField(TEXT("render_emitters"), RenderEmitters);
			const FVector EffectLocation = Particle->GetComponentLocation();
			TArray<TSharedPtr<FJsonValue>> Location;
			for (double Value : { EffectLocation.X, EffectLocation.Y, EffectLocation.Z })
			{
				Location.Add(MakeShared<FJsonValueNumber>(Value));
			}
			Effect->SetArrayField(TEXT("position"), Location);
			if (Particle->Template && Particle->Template->GetName().Contains(TEXT("RainofArrows")))
			{
				Particle->ForceAsyncWorkCompletion(UParticleSystemComponent::SILENT);
				TArray<TSharedPtr<FJsonValue>> Emitters;
				for (FParticleEmitterInstance* Instance : Particle->EmitterInstances)
				{
					if (!Instance || !Instance->SpriteTemplate) { continue; }
					TSharedRef<FJsonObject> Emitter = MakeShared<FJsonObject>();
					const FString Name = Instance->SpriteTemplate->EmitterName.ToString();
					Emitter->SetStringField(TEXT("name"), Name);
					Emitter->SetNumberField(TEXT("particles"), Instance->ActiveParticles);
					if (Name.StartsWith(TEXT("Falling")) && Instance->ActiveParticles > 0)
					{
						double MinZ = TNumericLimits<double>::Max();
						double MaxZ = TNumericLimits<double>::Lowest();
						double MaxRadius = 0;
						for (int32 Index = 0; Index < Instance->ActiveParticles; ++Index)
						{
							if (FBaseParticle* Base = Instance->GetParticle(Index))
							{
							const FVector Position = Instance->SimulationToWorld.TransformPosition(
								Instance->GetParticleLocationWithOrbitOffset(Base));
								MinZ = FMath::Min(MinZ, Position.Z);
								MaxZ = FMath::Max(MaxZ, Position.Z);
								MaxRadius = FMath::Max(MaxRadius, FVector::Dist2D(Position, EffectLocation));
							}
						}
						Emitter->SetNumberField(TEXT("min_z"), MinZ);
						Emitter->SetNumberField(TEXT("max_z"), MaxZ);
						Emitter->SetNumberField(TEXT("max_radius_xy"), MaxRadius);
					}
					Emitters.Add(MakeShared<FJsonValueObject>(Emitter));
				}
				Effect->SetArrayField(TEXT("emitters"), Emitters);
			}
			Effect->SetStringField(TEXT("socket"), Particle->GetAttachSocketName().ToString());
			AActor* BoneSource = nullptr;
			Particle->GetActorParameter(TEXT("BoneSocketActor"), BoneSource);
			Effect->SetBoolField(TEXT("bone_source_valid"), IsValid(BoneSource));
			Effects.Add(MakeShared<FJsonValueObject>(Effect));
		}
		Json->SetNumberField(TEXT("audio_components"), AudioComponents);
		Json->SetArrayField(TEXT("effects"), Effects);
		TArray<TSharedPtr<FJsonValue>> Projectiles;
		for (TActorIterator<AActor> Iterator(World); Iterator; ++Iterator)
		{
			if (!Iterator->IsA<ASparrowArrow>()) { continue; }
			TSharedRef<FJsonObject> Projectile = MakeShared<FJsonObject>();
			Projectile->SetStringField(TEXT("name"), Iterator->GetName());
			const ASparrowArrow* Arrow = Cast<ASparrowArrow>(*Iterator);
			const UStaticMeshComponent* Visual = Iterator->FindComponentByClass<UStaticMeshComponent>();
			// OBJ로 확인한 원본 화살촉의 로컬 -Z축이 실제 비행 방향과 일치해야 한다.
			const FVector VisualForward = Visual ? Visual->GetComponentTransform().TransformVectorNoScale(
				FVector::DownVector).GetSafeNormal() : FVector::ZeroVector;
			Projectile->SetNumberField(TEXT("mesh_forward_dot_flight"), FVector::DotProduct(VisualForward, Arrow->GetFlightDirection()));
			const FVector Position = Iterator->GetActorLocation();
			Projectile->SetNumberField(TEXT("x"), Position.X);
			Projectile->SetNumberField(TEXT("y"), Position.Y);
			Projectile->SetNumberField(TEXT("z"), Position.Z);
			Projectiles.Add(MakeShared<FJsonValueObject>(Projectile));
		}
		Json->SetArrayField(TEXT("projectiles"), Projectiles);
		if (const FAnimNode_StateMachine* Machine = Anim->GetStateMachineInstanceFromName(TEXT("Ground Locomotion")))
		{
			IAnimClassInterface* Interface = IAnimClassInterface::GetFromClass(Anim->GetClass());
			const FBakedAnimationStateMachine* Description = Interface ?
				Anim->GetMachineDescription(Interface, const_cast<FAnimNode_StateMachine*>(Machine)) : nullptr;
			if (Description && Description->States.IsValidIndex(Machine->GetCurrentState()))
			{
				Json->SetStringField(TEXT("ground_state"), Description->States[Machine->GetCurrentState()].StateName.ToString());
				for (int32 Index = 0; Index < Description->States.Num(); ++Index)
				{
					if (Description->States[Index].StateName == TEXT("Run"))
					{
						Json->SetNumberField(TEXT("run_weight"), Machine->GetStateWeight(Index));
					}
				}
			}
		}
		FString Text;
		FJsonSerializer::Serialize(Json, TJsonWriterFactory<>::Create(&Text));
		FFileHelper::SaveStringToFile(Text,
			*(CharacterPipelineQA::GetOutputDirectory(TEXT("QA/Sparrow")) / (Args[0] + TEXT(".json"))),
			FFileHelper::EEncodingOptions::ForceUTF8WithoutBOM);
	}));

#endif
