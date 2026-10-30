#include "CountessRebirthFX.h"
#include "CountessInfernoVisual.h"
#include "Components/InstancedStaticMeshComponent.h"
#include "Engine/StaticMesh.h"
#include "Engine/World.h"
#include "GameFramework/Character.h"
#include "Components/SkeletalMeshComponent.h"
#include "HAL/IConsoleManager.h"
#include "Kismet/GameplayStatics.h"
#include "Materials/MaterialInstanceDynamic.h"
#include "Particles/ParticleSystemComponent.h"
#include "Particles/ParticleSystem.h"

namespace
{
	TAutoConsoleVariable<int32> CVarRebirth(TEXT("Countess.Rebirth"), 1, TEXT("Countess revised skill presentation."));
	constexpr const TCHAR* Root = TEXT("/Game/TopDown/Characters/Countess/Rebirth20261028");
	float Envelope(float T, float Hold = .08f, float End = .42f)
	{
		return FMath::SmoothStep(0.f, .045f, T) * (1.f - FMath::SmoothStep(Hold, End, T));
	}
	UObject* Asset(const TCHAR* Name, UClass* Type)
	{
		return StaticLoadObject(Type, nullptr, *FString::Printf(TEXT("%s/%s.%s"), Root, Name, Name));
	}
}

ACountessRebirthFX::ACountessRebirthFX()
{
	PrimaryActorTick.bCanEverTick = true; PrimaryActorTick.TickGroup = TG_PostPhysics;
	SetRootComponent(CreateDefaultSubobject<USceneComponent>(TEXT("Root")));
	Cuts = CreateDefaultSubobject<UInstancedStaticMeshComponent>(TEXT("SculptedCuts"));
	Fangs = CreateDefaultSubobject<UInstancedStaticMeshComponent>(TEXT("ObsidianFangs"));
	for (auto* Part : {Cuts.Get(), Fangs.Get()})
	{
		Part->SetupAttachment(RootComponent); Part->SetCollisionEnabled(ECollisionEnabled::NoCollision);
		Part->SetGenerateOverlapEvents(false); Part->SetCanEverAffectNavigation(false); Part->SetCastShadow(false);
		Part->SetReceivesDecals(false); Part->NumCustomDataFloats = 4;
	}
	Tags.Append({TEXT("CountessRebirthFX"), TEXT("CountessSkillFX")}); SetActorEnableCollision(false); SetCanBeDamaged(false);
}
bool ACountessRebirthFX::Enabled() { return CVarRebirth.GetValueOnGameThread() != 0; }
ACountessRebirthFX* ACountessRebirthFX::Create(AActor* Owner, FName Kind, const FVector& Point, const FVector& Direction, AActor* Follow)
{
	if (!Enabled() || !IsValid(Owner) || !Owner->GetWorld()) { return nullptr; }
	FActorSpawnParameters Params; Params.Owner = Owner; Params.ObjectFlags |= RF_Transient;
	Params.SpawnCollisionHandlingOverride = ESpawnActorCollisionHandlingMethod::AlwaysSpawn;
	auto* FX = Owner->GetWorld()->SpawnActor<ACountessRebirthFX>(Point, Direction.Rotation(), Params);
	if (FX && !FX->Initialize(Kind, Point, Direction, Follow)) { FX->Destroy(); return nullptr; }
	return FX;
}
bool ACountessRebirthFX::Initialize(FName Kind, const FVector& Point, const FVector& Direction, AActor* Follow)
{
	Role = Kind; Origin = Point; Forward = Direction.GetSafeNormal2D();
	if (Forward.IsNearlyZero()) { Forward = GetOwner()->GetActorForwardVector(); }
	Right = FVector::CrossProduct(FVector::UpVector, Forward); Source = Follow; bFollow = IsValid(Follow);
	if (Follow) { AddTickPrerequisiteActor(Follow); }
	if (Role == TEXT("W")) { return InitializeW(); }
	Cuts->SetStaticMesh(Cast<UStaticMesh>(Asset(TEXT("SM_TwistedCut"), UStaticMesh::StaticClass())));
	Fangs->SetStaticMesh(Cast<UStaticMesh>(Asset(TEXT("SM_HookedFang"), UStaticMesh::StaticClass())));
	auto* CutSurface = Cast<UMaterialInterface>(Asset(TEXT("M_BloodCut"), UMaterialInterface::StaticClass()));
	auto* FangSurface = Cast<UMaterialInterface>(Asset(TEXT("M_ObsidianVein"), UMaterialInterface::StaticClass()));
	if (!Cuts->GetStaticMesh() || !Fangs->GetStaticMesh() || !CutSurface || !FangSurface) { return false; }
	CutMaterial = Cuts->CreateDynamicMaterialInstance(0, CutSurface); FangMaterial = Fangs->CreateDynamicMaterialInstance(0, FangSurface);
	Life = Role == TEXT("S") ? 24.f : Role == TEXT("V") ? 3.7f : Role == TEXT("A") ? 2.3f : Role == TEXT("R") ? 1.25f : Role == TEXT("E") ? 1.15f : .8f;
	SetLifeSpan(Life + .12f); Tags.Add(FName(*FString::Printf(TEXT("CountessRebirth_%s"), *Role.ToString())));
	return CutMaterial && FangMaterial;
}
bool ACountessRebirthFX::InitializeW()
{
	ACharacter* Character = Cast<ACharacter>(GetOwner());
	USkeletalMeshComponent* Mesh = Character ? Character->GetMesh() : nullptr;
	UParticleSystem* TrailSource = LoadObject<UParticleSystem>(nullptr,
		TEXT("/Game/ParagonCountess/FX/Particles/p_CountessMeleeTrail.p_CountessMeleeTrail"));
	WSlashSource = LoadObject<UParticleSystem>(nullptr,
		TEXT("/Game/ParagonCountess/FX/Particles/Abilities/BladeSiphon/FX/P_Countess_BladeSiphon_Trails.P_Countess_BladeSiphon_Trails"));
	if (!Mesh || !TrailSource || !WSlashSource) { return false; }

	// Keep the authored trail material and lifetime on both real weapon sockets.
	// The old procedural crescents are not loaded for W.
	Cuts->SetVisibility(false); Fangs->SetVisibility(false);
	for (const TCHAR* Side : {TEXT("L"), TEXT("R")})
	{
		const FName Base(*FString::Printf(TEXT("FX_WeaponBase_%s"), Side));
		const FName Tip(*FString::Printf(TEXT("FX_WeaponTip_%s"), Side));
		if (!Mesh->DoesSocketExist(Base) || !Mesh->DoesSocketExist(Tip)) { return false; }
		UParticleSystemComponent* Trail = UGameplayStatics::SpawnEmitterAttached(TrailSource, Mesh, NAME_None,
			FVector::ZeroVector, FRotator::ZeroRotator, EAttachLocation::SnapToTarget, false, EPSCPoolMethod::None, false);
		if (!Trail) { return false; }
		// Match SpawnEffect: do not let distance LOD remove the authored emitters in the top-down camera.
		Trail->bOverrideLODMethod = true;
		Trail->LODMethod = PARTICLESYSTEMLODMETHOD_DirectSet;
		Trail->SetActorParameter(TEXT("BoneSocketActor"), Character);
		Trail->SetLODLevel(0);
		Trail->BeginTrails(Base, Tip, ETrailWidthMode_FromCentre, 1.0f);
		Trail->SetLODLevel(0);
		Trail->ComponentTags.Add(TEXT("CountessWSourceTrail"));
		Pulses.Add(Trail);
	}
	// Stop emission at the end of the cut; allow the source particles to finish.
	Life = 2.5f; SetLifeSpan(Life);
	Tags.Append({TEXT("CountessRebirth_W"), TEXT("CountessWSourceFX")});
	return true;
}
void ACountessRebirthFX::DrawW()
{
	if (LastBeat < 0 && Age >= .04f)
	{
		// Match ReleaseReforgeSkill's existing W damage pulse; no extra hit is added.
		const FVector Center = Origin + Forward * 190.f + FVector(0, 0, 8.f);
		if (UParticleSystemComponent* Slash = UGameplayStatics::SpawnEmitterAtLocation(GetWorld(), WSlashSource,
			Center, Forward.Rotation(), FVector(.50f), false, EPSCPoolMethod::None, false))
		{
			// Preserve the authored blade-current meshes, texture motion and erosion together.
			Slash->bOverrideLODMethod = true;
			Slash->LODMethod = PARTICLESYSTEMLODMETHOD_DirectSet;
			Slash->SetActorParameter(TEXT("BoneSocketActor"), GetOwner());
			Slash->SetLODLevel(0);
			Slash->ActivateSystem(true);
			Slash->SetLODLevel(0);
			Slash->ComponentTags.Add(TEXT("CountessWSourceSlash"));
			Pulses.Add(Slash);
		}
		LastBeat = 0;
		UE_LOG(LogTemp, Display, TEXT("COUNTESS_W_SOURCE slash age=%.3f center=%s particles=%d"), Age, *Center.ToString(), Pulses.Num());
	}
	if (LastBeat == 0 && Age >= .20f)
	{
		for (UParticleSystemComponent* Particle : Pulses)
		{
			if (IsValid(Particle) && Particle->ComponentTags.Contains(TEXT("CountessWSourceTrail")))
			{
				Particle->EndTrails();
				Particle->DeactivateSystem();
			}
		}
		LastBeat = 1;
	}
}
void ACountessRebirthFX::Cut(const FVector& Center, const FRotator& Rotation, const FVector& Size, float Alpha, float Seed)
{
	if (Alpha <= .002f) { return; }
	CutTransforms.Emplace(Rotation, Center, Size); CutData.Add(FVector4f(0.f, 1.f, Alpha, Seed));
}
void ACountessRebirthFX::Fang(const FVector& Base, const FRotator& Rotation, const FVector& Size, float Alpha)
{
	if (Alpha <= .002f || Size.Z < .001f) { return; }
	FangTransforms.Emplace(Rotation, Base, Size); FangData.Add(FVector4f(0.f, 1.f, Alpha, float(FangData.Num()) * .17f));
}
void ACountessRebirthFX::Pulse(const FVector& Where, float Scale)
{
	auto* Template = LoadObject<UParticleSystem>(nullptr,
		TEXT("/Game/TopDown/Characters/Countess/FX/P_CountessBloodSealBurst.P_CountessBloodSealBurst"));
	if (auto* Particle = UGameplayStatics::SpawnEmitterAtLocation(GetWorld(), Template, Where, Forward.Rotation(), FVector(Scale), true))
	{
		Particle->CustomTimeDilation = 1.5f; Pulses.Add(Particle);
		for (const TCHAR* Name : {TEXT("DarkeningElement"), TEXT("Refraction"), TEXT("Light"), TEXT("DarkSparkBack")})
		{
			Particle->SetEmitterEnable(Name, false);
		}
	}

	if (Role == TEXT("E") || Role == TEXT("R"))
	{
		auto* Ground = LoadObject<UParticleSystem>(nullptr, TEXT("/Game/TopDown/Characters/Countess/FX/P_CountessBloodSealGround.P_CountessBloodSealGround"));
		if (auto* Contact = UGameplayStatics::SpawnEmitterAtLocation(GetWorld(), Ground, Where, FRotator::ZeroRotator, FVector(Scale * .48f), true))
		{
			Contact->CustomTimeDilation = 1.4f; Pulses.Add(Contact);
			for (const TCHAR* Name : {TEXT("DarkeningElement"), TEXT("Refraction"), TEXT("Light"), TEXT("DarkSpark"), TEXT("DarkSparkBack")}) { Contact->SetEmitterEnable(Name, false); }
		}
	}
}
void ACountessRebirthFX::DrawStrike()
{
	const float Yaw = Forward.Rotation().Yaw;
	if (Role == TEXT("Q") || Role == TEXT("W") || Role == TEXT("D"))
	{
		const bool bD = Role == TEXT("D"), bW = Role == TEXT("W");
		const int32 Count = bD ? 3 : 2;
		for (int32 I = 0; I < Count; ++I)
		{
			const float T = Age - (bD ? .21f + I * .045f : I * .045f);
			const float P = FMath::Clamp(T / .18f, 0.f, 1.f), E = Envelope(T, .11f, .46f);
			const float Sign = I % 2 == 0 ? -1.f : 1.f;
			const FVector Center = Origin + Forward * (bD ? 240.f : bW ? 185.f : 0.f) + FVector(0, 0, 70.f + I * 21.f);
			Cut(Center, FRotator(bD ? 13.f : Sign * 35.f, Yaw - 75.f + P * 145.f + I * 17.f, Sign * (bD ? 8.f : 40.f)),
				FVector(bD ? 1.85f : bW ? 1.45f : 1.12f, 1.f, 1.f), E, I * .23f);
			Cut(Center - Forward * 17.f - FVector(0, 0, 5.f), FRotator(0.f, Yaw - 90.f + P * 155.f, Sign * 30.f),
				FVector(bD ? 1.65f : 1.15f, .5f, .6f), E * .4f, .7f);
		}
		const float BeatAt = bD ? .21f : .035f;
		if (Age > BeatAt && LastBeat < 0) { Pulse(Origin + Forward * (bD ? 260.f : bW ? 200.f : 0.f) + FVector(0, 0, 65.f), .43f); LastBeat = 0; }
	}
	else if (Role == TEXT("E") || Role == TEXT("R"))
	{
		const bool bR = Role == TEXT("R");
		for (int32 Zone = 0; Zone < (bR ? 3 : 1); ++Zone)
		{
			const float T = Age - (bR ? .08f + Zone * .12f : .12f);
			const float Growth = FMath::SmoothStep(0.f, .12f, T), Fade = 1.f - FMath::SmoothStep(.38f, .86f, T);
			const FVector Center = Origin + Forward * (bR ? 140.f + Zone * 220.f : 0.f);
			for (int32 I = 0; I < (bR ? 5 : 8); ++I)
			{
				const float Angle = I * 2.399963f + Zone * .7f;
				const FVector Radial = Forward * FMath::Cos(Angle) + Right * FMath::Sin(Angle);
				const float Height = (bR ? 1.6f + (I % 3) * .65f : 2.1f + I % 3 * .7f) * Growth;
				Fang(Center + Radial * (bR ? 55.f : 115.f), FRotator(bR ? -20.f : 20.f, Yaw + FMath::RadiansToDegrees(Angle), (I % 2 ? -1.f : 1.f) * 16.f),
					FVector(1.4f + I % 2 * .3f, 1.15f, Height), Fade * Growth);
				Cut(Center + Radial * 40.f + FVector(0, 0, 12.f + Growth * 30.f), FRotator(60.f, Yaw + I * 47.f, 0),
					FVector(.5f + Growth * .35f, .55f, 1.f), Envelope(T, .18f, .65f) * .65f, I * .1f);
			}
			if (T > 0.f && LastBeat < Zone) { Pulse(Center + FVector(0, 0, 25.f), bR ? .72f : 1.05f); LastBeat = Zone; }
		}
	}
	else if (Role == TEXT("B"))
	{
		const float E = Envelope(Age, .035f, .23f);
		Cut(Origin + Forward * 25.f, FRotator(5.f, Yaw + 30.f - Age * 360.f, 12.f), FVector(1.12f, .55f, 1.f), E);
		if (LastBeat < 0) { Pulse(Origin, .3f); LastBeat = 0; }
	}
	else
	{
		// Two severed, vertical crescents disappear rapidly; no continuous portal disk.
		const float E = Envelope(Age, .04f, .27f);
		for (int32 Side = -1; Side <= 1; Side += 2)
		{
			Cut(Origin + Right * Side * Age * 120.f, FRotator(60.f, Yaw + Side * 35.f + Age * Side * 120.f, 35.f), FVector(.85f, .6f, 1.2f), E);
		}
		if (LastBeat < 0) { Pulse(Origin + FVector(0, 0, 15.f), .44f); LastBeat = 0; }
	}
}
void ACountessRebirthFX::DrawField()
{
	const bool bV = Role == TEXT("V");
	if (auto* Field = Cast<ACountessInfernoVisual>(Source.Get())) { Origin = Field->GetFieldCenter(); }
	const float E = FMath::SmoothStep(0.f, .15f, Age) * (1.f - FMath::SmoothStep(Life - .25f, Life, Age));
	const float Radius = bV ? FMath::Lerp(100.f, 385.f, FMath::SmoothStep(.15f, .9f, Age)) : 135.f;
	const int32 Count = bV ? 4 : 2;
	for (int32 I = 0; I < Count; ++I)
	{
		const float Angle = Age * (bV ? 5.4f : 7.f) + I * PI * 2.f / Count;
		const FVector Radial = Forward * FMath::Cos(Angle) + Right * FMath::Sin(Angle);
		Cut(Origin + Radial * Radius * .35f + FVector(0, 0, bV ? 55.f + I * 32.f : 60.f),
			FRotator(bV ? I * 11.f - 18.f : 16.f, Forward.Rotation().Yaw + FMath::RadiansToDegrees(Angle), I % 2 ? -25.f : 20.f),
			FVector(Radius / 105.f, .55f + (bV ? .5f : 0.f), 1.f), E * (bV ? .68f : .8f), I * .17f);
	}
	if (bV && Age > 3.15f)
	{
		const float P = FMath::SmoothStep(3.15f, 3.45f, Age);
		for (int32 I = 0; I < 7; ++I)
		{
			const float A = I * PI * 2.f / 7.f;
			Fang(Origin + (Forward * FMath::Cos(A) + Right * FMath::Sin(A)) * 100.f * (1.f - P),
				FRotator(22.f, I * 51.4f, 0.f), FVector(.8f, .65f, P * 2.1f), E);
		}
	}
	const int32 Beat = bV ? FMath::FloorToInt((Age - .38f) / .23f) : FMath::FloorToInt((Age - .18f) / .34f);
	if (Beat > LastBeat && Beat >= 0 && Beat < (bV ? 12 : 6))
	{
		const float Angle = Beat * 2.399963f;
		Pulse(Origin + (Forward * FMath::Cos(Angle) + Right * FMath::Sin(Angle)) * Radius * .55f + FVector(0, 0, 60.f), bV ? .38f : .32f); LastBeat = Beat;
	}
}
void ACountessRebirthFX::DrawForm()
{
	Origin = GetOwner()->GetActorLocation(); Forward = GetOwner()->GetActorForwardVector(); Right = FVector::CrossProduct(FVector::UpVector, Forward);
	if (const auto* Character = Cast<ACharacter>(GetOwner()); Character && Character->GetMesh())
	{
		const auto* Mesh = Character->GetMesh();
		if (!Mesh->IsVisible() || Mesh->bHiddenInGame || Character->IsHidden()) { return; }
		const auto* Defaults = Character->GetClass()->GetDefaultObject<ACharacter>();
		if (Defaults && Defaults->GetMesh())
		{
			// V raises the actual mesh while its capsule stays grounded.
			const FVector MeshOffset = Mesh->GetRelativeLocation() - Defaults->GetMesh()->GetRelativeLocation();
			Origin += Character->GetActorTransform().TransformVectorNoScale(MeshOffset);
		}
	}
	const float E = FMath::SmoothStep(0.f, .18f, Age) * (1.f - FMath::SmoothStep(23.6f, 24.f, Age));
	for (int32 Side = -1; Side <= 1; Side += 2)
	{
		for (int32 I = 0; I < 3; ++I)
		{
			Fang(Origin - Forward * (14.f + I * 10.f) + Right * Side * (23.f + I * 7.f) + FVector(0, 0, 18.f),
				FRotator(20.f + I * 9.f, GetOwner()->GetActorRotation().Yaw + 90.f * Side, 18.f * Side),
				FVector(.25f, .4f, .65f + I * .14f), E * .9f);
		}
	}
	if (Age < .7f)
	{
		Cut(Origin - FVector(0, 0, 65.f), FRotator(0, Age * 240.f, 0), FVector(.65f + Age * 2.5f, 1.f, 1.f), Envelope(Age, .18f, .65f));
	}
	if (LastBeat < 0) { Pulse(Origin, .9f); LastBeat = 0; }
}
void ACountessRebirthFX::Upload()
{
	auto Write = [](UInstancedStaticMeshComponent* Part, const TArray<FTransform>& Transforms, const TArray<FVector4f>& Data)
	{
		if (Part->GetInstanceCount() != Transforms.Num()) { Part->ClearInstances(); Part->AddInstances(Transforms, false, true); }
		else if (!Transforms.IsEmpty()) { Part->BatchUpdateInstancesTransforms(0, Transforms, true, true, true); }
		for (int32 I = 0; I < Data.Num(); ++I) for (int32 C = 0; C < 4; ++C) { Part->SetCustomDataValue(I, C, Data[I][C], false); }
		Part->MarkRenderStateDirty();
	};
	Write(Cuts, CutTransforms, CutData); Write(Fangs, FangTransforms, FangData);
	CutMaterial->SetScalarParameterValue(TEXT("Age"), Age); FangMaterial->SetScalarParameterValue(TEXT("Age"), Age);
}
void ACountessRebirthFX::Tick(float DeltaSeconds)
{
	Super::Tick(DeltaSeconds);
	if (!IsValid(GetOwner()) || GetOwner()->IsActorBeingDestroyed() || (bFollow && !Source.IsValid())) { Destroy(); return; }
	Age += FMath::Max(0.f, DeltaSeconds);
	if (Role == TEXT("W")) { DrawW(); return; }
	CutTransforms.Reset(); CutData.Reset(); FangTransforms.Reset(); FangData.Reset();
	if (Role == TEXT("S")) { DrawForm(); }
	else if (Role == TEXT("A") || Role == TEXT("V")) { DrawField(); }
	else { DrawStrike(); }
	Upload();
	if (Age <= DeltaSeconds + .001f) { UE_LOG(LogTemp, Display, TEXT("COUNTESS_REBIRTH first role=%s cuts=%d fangs=%d origin=%s"), *Role.ToString(), CutTransforms.Num(), FangTransforms.Num(), *Origin.ToString()); }
}
void ACountessRebirthFX::EndPlay(const EEndPlayReason::Type Reason)
{
	for (UParticleSystemComponent* Particle : Pulses) { if (IsValid(Particle)) { Particle->DeactivateSystem(); Particle->DestroyComponent(); } }
	Super::EndPlay(Reason);
}
