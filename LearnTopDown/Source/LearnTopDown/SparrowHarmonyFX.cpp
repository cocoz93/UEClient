#include "SparrowHarmonyFX.h"
#include "SparrowArrow.h"
#include "SparrowAscendedShotFX.h"
#include "Camera/PlayerCameraManager.h"
#include "Components/InstancedStaticMeshComponent.h"
#include "Components/SkeletalMeshComponent.h"
#include "Engine/StaticMesh.h"
#include "Engine/World.h"
#include "GameFramework/Character.h"
#include "HAL/IConsoleManager.h"
#include "Kismet/GameplayStatics.h"
#include "Materials/MaterialInstanceDynamic.h"
#include "Particles/ParticleSystemComponent.h"

namespace
{
	TAutoConsoleVariable<int32> CVarHarmony(TEXT("Sparrow.Harmony"), 1, TEXT("Sparrow visual rework; gameplay values are unchanged."));
	constexpr const TCHAR* Root = TEXT("/Game/TopDown/Characters/Sparrow/FX/Harmony20261028");
	float Smooth(float A, float B, float T) { return FMath::SmoothStep(A, B, T); }
	UObject* Asset(const TCHAR* Name, UClass* Type)
	{
		return StaticLoadObject(Type, nullptr, *FString::Printf(TEXT("%s/%s.%s"), Root, Name, Name));
	}
	void Configure(UInstancedStaticMeshComponent* Part)
	{
		Part->SetCollisionEnabled(ECollisionEnabled::NoCollision); Part->SetGenerateOverlapEvents(false);
		Part->SetCanEverAffectNavigation(false); Part->SetCastShadow(false); Part->SetReceivesDecals(false);
		Part->NumCustomDataFloats = 4; Part->ComponentTags.Add(TEXT("SparrowSkillFX"));
	}
}

ASparrowHarmonyFX::ASparrowHarmonyFX()
{
	PrimaryActorTick.bCanEverTick = true; PrimaryActorTick.TickGroup = TG_PostPhysics;
	SetRootComponent(CreateDefaultSubobject<USceneComponent>(TEXT("Root")));
	Ribbons = CreateDefaultSubobject<UInstancedStaticMeshComponent>(TEXT("WovenCurrents"));
	Motes = CreateDefaultSubobject<UInstancedStaticMeshComponent>(TEXT("BoundLight"));
	ArrowHeads = CreateDefaultSubobject<UInstancedStaticMeshComponent>(TEXT("CarvedArrows"));
	for (auto* Part : {Ribbons.Get(), Motes.Get(), ArrowHeads.Get()}) { Part->SetupAttachment(RootComponent); Configure(Part); }
	SetActorEnableCollision(false); SetCanBeDamaged(false); Tags.Add(TEXT("SparrowHarmonyFX"));
}

bool ASparrowHarmonyFX::Enabled() { return CVarHarmony.GetValueOnGameThread() != 0; }
ASparrowHarmonyFX* ASparrowHarmonyFX::Create(AActor* Owner, FName Kind, const FVector& Point,
	const FVector& Direction, float Charge, AActor* Source)
{
	if (!Enabled() || !IsValid(Owner) || !Owner->GetWorld()) { return nullptr; }
	FActorSpawnParameters Params; Params.Owner = Owner; Params.SpawnCollisionHandlingOverride = ESpawnActorCollisionHandlingMethod::AlwaysSpawn;
	auto* FX = Owner->GetWorld()->SpawnActor<ASparrowHarmonyFX>(Point, FRotator::ZeroRotator, Params);
	if (FX && !FX->Initialize(Kind, Point, Direction, Charge, Source)) { FX->Destroy(); return nullptr; }
	return FX;
}
bool ASparrowHarmonyFX::Initialize(FName Kind, const FVector& Point, const FVector& Direction, float Charge, AActor* Source)
{
	Role = Kind; Origin = Point; Forward = Direction.GetSafeNormal(); ChargeSeconds = FMath::Max(.05f, Charge);
	Follow = Source; bHasFollow = IsValid(Source);
	if (Source) { AddTickPrerequisiteActor(Source); }
	UStaticMesh* Plane = LoadObject<UStaticMesh>(nullptr, TEXT("/Engine/BasicShapes/Plane.Plane"));
	UStaticMesh* Shape = Cast<UStaticMesh>(Asset(TEXT("SM_CarvedArrow"), UStaticMesh::StaticClass()));
	Ribbons->SetStaticMesh(Plane); Motes->SetStaticMesh(Plane); ArrowHeads->SetStaticMesh(Shape);
	UMaterialInterface* Flow = Cast<UMaterialInterface>(Asset(TEXT("M_WovenCurrent"), UMaterialInterface::StaticClass()));
	UMaterialInterface* Dot = Cast<UMaterialInterface>(Asset(TEXT("M_BoundLight"), UMaterialInterface::StaticClass()));
	UMaterialInterface* Metal = Cast<UMaterialInterface>(Asset(TEXT("M_ArrowRelief"), UMaterialInterface::StaticClass()));
	if (!Plane || !Shape || !Flow || !Dot || !Metal) { return false; }
	RibbonMaterial = Ribbons->CreateDynamicMaterialInstance(0, Flow);
	MoteMaterial = Motes->CreateDynamicMaterialInstance(0, Dot);
	ArrowMaterial = ArrowHeads->CreateDynamicMaterialInstance(0, Metal);
	Tags.Add(FName(*FString::Printf(TEXT("SparrowHarmony_%s"), *Role.ToString())));
	SetLifeSpan(Role == TEXT("Q") ? 4.3f : Role == TEXT("A") ? 13.f : Role == TEXT("B") ? .22f : ChargeSeconds + .65f);
	return RibbonMaterial && MoteMaterial && ArrowMaterial;
}
void ASparrowHarmonyFX::NotifyShot() { if (ShotAt < 0.f) { ShotAt = Age; } }
void ASparrowHarmonyFX::TrackArrow(ASparrowArrow* InArrow)
{
	if (!IsValid(InArrow)) { return; }
	NotifyShot(); Arrows.Add(InArrow); LastArrowPoints.Add(InArrow->GetActorLocation()); ArrowEnded.Add(false);
}
FVector ASparrowHarmonyFX::Anchor() const
{
	const auto* Character = Cast<ACharacter>(GetOwner());
	return Character && Character->GetMesh() ? Character->GetMesh()->GetSocketLocation(TEXT("arrow_anchor")) : Origin;
}
void ASparrowHarmonyFX::Strip(const FVector& A, const FVector& B, float Width, float Alpha, float Path)
{
	const FVector Delta = B - A; const float Length = Delta.Size();
	if (Alpha <= .001f || Length < .01f) { return; }
	Width *= Role == TEXT("S") ? 2.5f : Role == TEXT("D") ? 2.f : Role == TEXT("A") ? 1.8f : Role == TEXT("B") ? 2.5f : 1.6f;
	RibbonTransforms.Emplace(FRotationMatrix::MakeFromXZ(Delta / Length, CameraNormal).Rotator(),
		(A + B) * .5f, FVector(Length * 1.04f / 100.f, Width / 100.f, 1.f));
	RibbonData.Add(FVector4f(Path, Length / 160.f, Alpha, float(RibbonData.Num() % 3) * .17f));
}
void ASparrowHarmonyFX::Dot(const FVector& Point, float Size, float Alpha)
{
	if (Alpha <= .001f || Size <= .01f) { return; }
	MoteTransforms.Emplace(FRotationMatrix::MakeFromZ(CameraNormal).Rotator(), Point, FVector(Size / 100.f));
	MoteData.Add(FVector4f(0.f, 0.f, Alpha, 0.f));
}
void ASparrowHarmonyFX::Arrow(const FVector& Tip, const FVector& Direction, float Size, float Alpha)
{
	if (Size < .001f || Alpha < .001f) { return; }
	const FVector Up = FMath::Abs(Direction.Z) > .98f ? FVector::RightVector : FVector::UpVector;
	ArrowTransforms.Emplace(FRotationMatrix::MakeFromXZ(Direction, Up).Rotator(),
		Tip - Direction * 160.f * Size, FVector(Size));
}
void ASparrowHarmonyFX::Pulse(const FVector& Point, float Scale)
{
	if (auto* Template = ASparrowAscendedShotFX::GetHarmonyContactTemplate())
	{
		if (auto* Particle = UGameplayStatics::SpawnEmitterAtLocation(GetWorld(), Template, Point,
			FRotator::ZeroRotator, FVector(Scale), true, EPSCPoolMethod::None, true))
		{
			Particle->CustomTimeDilation = 1.65f; Pulses.Add(Particle);
		}
	}
}
void ASparrowHarmonyFX::Rain()
{
	const FVector Across(0, 1, 0); const FVector Along(1, 0, 0);
	const float Flight = (Age - .68f) / .14f;
	for (int32 Index = 0; Index < 13; ++Index)
	{
		const float Angle = Index * 2.399963f;
		const float Radius = Index == 0 ? 0.f : FMath::Sqrt(float(Index) / 13.f) * 510.f;
		const FVector Ground = Origin + Across * FMath::Cos(Angle) * Radius + Along * FMath::Sin(Angle) * Radius;
		if (Flight >= 0.f && Flight < 1.2f)
		{
			const float Height = 1700.f * FMath::Square(1.f - FMath::Clamp(Flight, 0.f, 1.f));
			const FVector Tip = Ground + FVector::UpVector * Height;
			Arrow(Tip, -FVector::UpVector, Index == 0 ? 1.7f : 1.1f);
			Strip(Tip + FVector::UpVector * 30.f, Tip + FVector::UpVector * 1350.f, Index == 0 ? 22.f : 12.f,
				(1.f - Smooth(.94f, 1.18f, Flight)) * .8f, .2f);
		}
		if (Age > .82f && LastPulse < 0) { Pulse(Ground + FVector::UpVector * 5.f, Index == 0 ? 1.7f : .62f); }
		const float Local = Age - .82f;
		if (Local >= 0.f)
		{
			const float Fade = 1.f - Smooth(.12f, .75f, Local);
			for (int32 Spark = 0; Spark < 3; ++Spark)
			{
				const FVector D(FMath::Cos(Angle + Spark * 2.1f), FMath::Sin(Angle + Spark * 2.1f), .35f + Spark * .12f);
				Dot(Ground + D * Local * 240.f, 6.f * Fade, Fade * .8f);
			}
		}
	}
	if (Age >= .82f && LastPulse < 0) { LastPulse = 0; }
	// The first hit is the large visual beat; the sustained damage retains subtle contact beats.
	const int32 Beat = FMath::FloorToInt((Age - .82f) / .37f);
	if (Beat > LastPulse && Beat < 8 && Beat >= 1) { Pulse(Origin, .28f); LastPulse = Beat; }
}
void ASparrowHarmonyFX::Orbit()
{
	if (!Follow.IsValid() || Follow->IsActorBeingDestroyed()) { Destroy(); return; }
	Forward = Follow->GetActorForwardVector();
	const FVector Right = FVector::CrossProduct(FVector::UpVector, Forward).GetSafeNormal();
	const FVector Center = Follow->GetActorLocation() + Right * APairHalfSpacing;
	const FVector Up = FVector::UpVector;
	Arrow(Center + Forward * 55.f, Forward, .43f);
	for (int32 Side = 0; Side < 2; ++Side)
	{
		const float Phase = Age * 7.2f + Side * PI;
		const auto Point = [&](float T)
		{
			const float A = Phase - T * 1.65f;
			return Center - Forward * (14.f + T * 25.f) + Right * (FMath::Cos(A) * 79.f) + Up * (FMath::Sin(A) * 43.f);
		};
		for (int32 Step = 0; Step < 20; ++Step)
		{
			const float T = float(Step) / 20.f;
			Strip(Point(T), Point(T + .05f), 9.f * FMath::Pow(1.f - T, .65f) + .6f,
				FMath::Pow(1.f - T, 1.25f) * .95f, T * .7f);
		}
		Dot(Point(0.f), 9.f, .8f);
	}
}
void ASparrowHarmonyFX::Volley()
{
	const FVector Center = Anchor() + Forward * 68.f;
	const FVector Right = FVector::CrossProduct(FVector::UpVector, Forward).GetSafeNormal();
	const float P = Smooth(0.f, ChargeSeconds, Age), Since = ShotAt < 0.f ? -1.f : Age - ShotAt;
	const float Fade = Since < 0.f ? 1.f : 1.f - Smooth(.015f, .17f, Since);
	for (int32 Side = 0; Side < 2; ++Side)
	{
		const float Sign = Side == 0 ? -1.f : 1.f;
		for (int32 Layer = 0; Layer < 3; ++Layer)
		{
			auto Point = [&](float T)
			{
				const float Radius = FMath::Lerp(145.f, 45.f, P);
				return Center + Right * Sign * (Radius * (1.f - T)) + FVector::UpVector * (FMath::Sin(T * PI) * (45.f + Layer * 11.f))
					- Forward * (FMath::Sin(T * PI) * 55.f + Layer * 8.f);
			};
			for (int32 Step = 0; Step < 16; ++Step)
			{
				float T = Step / 16.f;
				Strip(Point(T), Point(T + 1.f / 16.f), (7.f + Layer * 2.f) * FMath::Sin(T * PI),
					Fade * P * (1.f - Layer * .24f), T);
			}
		}
	}
	Dot(Center, 15.f + P * 18.f, Fade * P * .65f);
	if (Since >= 0.f)
	{
		if (LastPulse < 0) { Pulse(Center, .5f); LastPulse = 0; }
		for (int32 Lane = -2; Lane <= 2; ++Lane)
		{
			const FVector Start = Center + Right * Lane * 17.f;
			Strip(Start + Forward * Since * 600.f, Start + Forward * (Since * 600.f + 190.f),
				(14.f - FMath::Abs(Lane) * 2.f) * Fade, Fade * .6f, float(Lane) * .2f);
		}
	}
}
void ASparrowHarmonyFX::Bow()
{
	auto* Character = Cast<ACharacter>(GetOwner()); if (!Character || !Character->GetMesh()) { return; }
	const FVector Center = Anchor();
	const float P = Smooth(0.f, ChargeSeconds, Age), Since = ShotAt < 0.f ? -1.f : Age - ShotAt;
	const float Fade = Since < 0.f ? 1.f : 1.f - Smooth(.015f, .15f, Since);
	for (FName Socket : {FName(TEXT("bow_string_top")), FName(TEXT("bow_string_bott"))})
	{
		FVector Start = Character->GetMesh()->GetSocketLocation(Socket);
		const auto Point = [&](float T) { return FMath::Lerp(Start, Center, T) - Forward * FMath::Sin(T * PI) * 27.f; };
		for (int32 Step = 0; Step < 16; ++Step)
		{
			const float T = Step / 16.f;
			Strip(Point(T), Point(T + 1.f / 16.f), 7.f * FMath::Sin(T * PI) + 1.f, P * Fade * .9f, T * .7f - Age * .6f);
		}
	}
	if (Since >= 0.f && LastPulse < 0) { Pulse(Center, .35f); LastPulse = 0; }
}
void ASparrowHarmonyFX::Gather()
{
	const FVector Center = Anchor() + Forward * 90.f;
	const FVector Right = FVector::CrossProduct(FVector::UpVector, Forward).GetSafeNormal();
	if (ShotAt < 0.f)
	{
		for (int32 Index = 0; Index < 32; ++Index)
		{
			const float P = FMath::Clamp((Age / ChargeSeconds - Index * .008f) / .84f, 0.f, 1.f);
			const float Ease = P * P, Angle = Index * 2.399963f + P * 1.6f;
			const FVector Radial = Right * FMath::Cos(Angle) + FVector::UpVector * FMath::Sin(Angle);
			const FVector Point = Center + Radial * (1.f - Ease) * (110.f + Index % 5 * 11.f) - Forward * (1.f - Ease) * 75.f;
			const float Alpha = Smooth(0.f, .12f, P) * (1.f - Smooth(.80f, 1.f, P));
			Dot(Point, (4.f + Index % 3 * 2.f) * (1.f - P * .5f), Alpha);
			Strip(Point - (Forward + Radial * .6f) * 17.f, Point, 3.f, Alpha * .55f, Index * .13f);
		}
		const float P = Age / ChargeSeconds;
		Dot(Center, 22.f + P * 14.f, .55f);
		const float Reveal = Smooth(.77f, .97f, P);
		Arrow(Center + Forward * 135.f, Forward, Reveal);
	}
	else
	{
		if (LastPulse < 0) { Pulse(Anchor() + Forward * 40.f, .55f); LastPulse = 0; }
		for (int32 Index = 0; Index < Arrows.Num(); ++Index)
		{
			if (Arrows[Index].IsValid() && !Arrows[Index]->IsActorBeingDestroyed())
			{
				const FVector Point = Arrows[Index]->GetActorLocation();
				const FVector FlightDirection = Arrows[Index]->GetActorForwardVector();
				Arrow(Point, FlightDirection, 1.f);
				Strip(Point - FlightDirection * 300.f, Point - FlightDirection * 150.f, 13.f, .7f, Age);
				LastArrowPoints[Index] = Point;
			}
			else if (!ArrowEnded[Index]) { Pulse(LastArrowPoints[Index], .6f); ArrowEnded[Index] = true; }
		}
	}
}
void ASparrowHarmonyFX::Blink()
{
	const float P = Age / .18f, Fade = FMath::Square(1.f - FMath::Clamp(P, 0.f, 1.f));
	if (LastPulse < 0) { Pulse(Origin, .95f); LastPulse = 0; }
	const FVector Right = FVector::CrossProduct(FVector::UpVector, Forward).GetSafeNormal();
	for (int32 Index = 0; Index < 10; ++Index)
	{
		const float Angle = Index * 2.399963f;
		const FVector D = Right * FMath::Cos(Angle) + FVector::UpVector * FMath::Sin(Angle);
		const FVector Point = Origin + D * (15.f + P * 80.f);
		Strip(Point, Point + D * 27.f * Fade, 4.f * Fade, Fade, .4f);
		Dot(Point, 7.f * Fade, Fade);
	}
	Strip(Origin - FVector::UpVector * 45.f, Origin + FVector::UpVector * 110.f, 15.f * Fade, Fade, .2f);
}
void ASparrowHarmonyFX::Upload()
{
	auto Write = [](UInstancedStaticMeshComponent* Part, const TArray<FTransform>& Transforms, const TArray<FVector4f>* Data)
	{
		if (Part->GetInstanceCount() != Transforms.Num()) { Part->ClearInstances(); Part->AddInstances(Transforms, false, true); }
		else if (!Transforms.IsEmpty()) { Part->BatchUpdateInstancesTransforms(0, Transforms, true, true, true); }
		if (Data) for (int32 I = 0; I < Data->Num(); ++I) for (int32 C = 0; C < 4; ++C) { Part->SetCustomDataValue(I, C, (*Data)[I][C], false); }
		Part->MarkRenderStateDirty();
	};
	Write(Ribbons, RibbonTransforms, &RibbonData); Write(Motes, MoteTransforms, &MoteData); Write(ArrowHeads, ArrowTransforms, nullptr);
	RibbonMaterial->SetScalarParameterValue(TEXT("Age"), Age); MoteMaterial->SetScalarParameterValue(TEXT("Age"), Age);
	ArrowMaterial->SetScalarParameterValue(TEXT("Envelope"), 1.f);
}
void ASparrowHarmonyFX::Tick(float DeltaSeconds)
{
	Super::Tick(DeltaSeconds);
	if (!IsValid(GetOwner()) || GetOwner()->IsActorBeingDestroyed()) { Destroy(); return; }
	Age += FMath::Max(DeltaSeconds, 0.f);
	RibbonTransforms.Reset(); MoteTransforms.Reset(); ArrowTransforms.Reset(); RibbonData.Reset(); MoteData.Reset();
	if (auto* Camera = UGameplayStatics::GetPlayerCameraManager(this, 0)) { CameraNormal = (Camera->GetCameraLocation() - Anchor()).GetSafeNormal(); }
	if (Role == TEXT("Q")) { Rain(); }
	else if (Role == TEXT("A")) { Orbit(); }
	else if (Role == TEXT("S")) { Volley(); }
	else if (Role == TEXT("D")) { Bow(); }
	else if (Role == TEXT("F")) { Gather(); }
	else if (Role == TEXT("B")) { Blink(); }
	if (bHasFollow && Role != TEXT("A") && ShotAt < 0.f && !Follow.IsValid()) { Destroy(); return; }
	Upload();
}
void ASparrowHarmonyFX::EndPlay(const EEndPlayReason::Type Reason)
{
	for (UParticleSystemComponent* Particle : Pulses) { if (IsValid(Particle)) { Particle->DeactivateSystem(); Particle->DestroyComponent(); } }
	Super::EndPlay(Reason);
}
