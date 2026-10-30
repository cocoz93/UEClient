#include "SparrowFeatherTrail.h"

#include "Camera/PlayerCameraManager.h"
#include "Components/SceneComponent.h"
#include "Components/StaticMeshComponent.h"
#include "Components/CapsuleComponent.h"
#include "Engine/StaticMesh.h"
#include "GameFramework/Character.h"
#include "Kismet/GameplayStatics.h"
#include "Materials/MaterialInstanceDynamic.h"
#include "SparrowArrow.h"

namespace
{
	constexpr int32 FeatherCapacity = 36;
}

ASparrowFeatherTrail::ASparrowFeatherTrail()
{
	PrimaryActorTick.bCanEverTick = true;
	PrimaryActorTick.TickGroup = TG_PostPhysics;
	SetRootComponent(CreateDefaultSubobject<USceneComponent>(TEXT("Root")));
	SetActorEnableCollision(false);
	SetCanBeDamaged(false);
	Tags.Append({TEXT("SparrowSkillFX"), TEXT("SparrowFeatherTrail")});
}

bool ASparrowFeatherTrail::InitializeD(ASparrowArrow* Arrow, bool bAscended)
{
	bDRoute = true;
	SampleSpacing = 110.0f;
	FadeLifetime = .78f;
	if (ACharacter* Character = Cast<ACharacter>(GetOwner()))
	{
		// 빌보드 깃의 아래 모서리까지 고려한 단순 높이 하한이다. 바닥 탐색이나 이동 판정은 만들지 않는다.
		GroundLimit = Character->GetActorLocation().Z - Character->GetCapsuleComponent()->GetScaledCapsuleHalfHeight() + 36.0f;
	}
	Tags.Add(TEXT("SparrowDFeatherTrail"));
	return Initialize(Arrow, bAscended);
}

bool ASparrowFeatherTrail::Initialize(ASparrowArrow* Arrow, bool bAscended)
{
	if (!IsValid(Arrow) || !IsValid(GetOwner()) || GetOwner() != Arrow->GetOwner()) { return false; }
	UStaticMesh* Plane = LoadObject<UStaticMesh>(nullptr, TEXT("/Engine/BasicShapes/Plane.Plane"));
	UMaterialInterface* Source = LoadObject<UMaterialInterface>(nullptr, bDRoute ?
		TEXT("/Game/TopDown/Characters/Sparrow/Previews/FlameStudies20261026/M_DRouteFeather.M_DRouteFeather") :
		TEXT("/Game/TopDown/Characters/Sparrow/Materials/AscendedArsenal20261026/M_AscendedFeather.M_AscendedFeather"));
	if (!Plane || !Source) { return false; }
	SourceArrow = Arrow;
	LastPosition = Arrow->GetActorLocation();
	LastDirection = Arrow->GetFlightDirection().GetSafeNormal();
	if (LastPosition.ContainsNaN() || LastDirection.IsNearlyZero()) { return false; }
	bForm = bAscended;
	Samples.SetNum(FeatherCapacity);
	for (int32 Index = 0; Index < FeatherCapacity; ++Index)
	{
		UMaterialInstanceDynamic* Material = UMaterialInstanceDynamic::Create(Source, this);
		if (!Material) { return false; }
		Material->SetScalarParameterValue(TEXT("Skill"), bForm ? 1.0f : 0.0f);
		UStaticMeshComponent* Surface = NewObject<UStaticMeshComponent>(this, NAME_None, RF_Transient);
		Surface->SetMobility(EComponentMobility::Movable);
		Surface->SetupAttachment(RootComponent);
		Surface->SetCollisionEnabled(ECollisionEnabled::NoCollision);
		Surface->SetGenerateOverlapEvents(false);
		Surface->SetCanEverAffectNavigation(false);
		Surface->SetCastShadow(false);
		Surface->SetReceivesDecals(false);
		Surface->SetStaticMesh(Plane);
		Surface->SetMaterial(0, Material);
		Surface->SetVisibility(false);
		Surface->ComponentTags.Add(TEXT("SparrowFeatherTrailSurface"));
		if (bDRoute) { Surface->ComponentTags.Add(TEXT("SparrowDRouteFeather")); }
		AddInstanceComponent(Surface);
		Surface->RegisterComponent();
		Surfaces.Add(Surface);
		Materials.Add(Material);
	}
	AddTickPrerequisiteActor(Arrow);
	if (bDRoute) { Arrow->OnDestroyed.AddDynamic(this, &ASparrowFeatherTrail::OnTrackedArrowDestroyed); }
	bReady = true;
	bTracking = true;
	SetLifeSpan(8.0f);
	return true;
}

void ASparrowFeatherTrail::Emit(const FVector& Position, const FVector& Direction)
{
	FFeatherSample& Sample = Samples[Emitted % FeatherCapacity];
	Sample.Position = Position;
	Sample.Direction = Direction;
	Sample.BornAt = Age + (bDRoute ? .035f + (Emitted % 3) * .01f : 0.0f);
	Sample.Seed = Emitted;
	++Emitted;
}

void ASparrowFeatherTrail::AppendSegment(const FVector& Position)
{
	if (!bReady || Position.ContainsNaN()) { return; }
	const FVector Delta = Position - LastPosition;
	const float Distance = Delta.Size();
	if (Distance < KINDA_SMALL_NUMBER) { return; }
	// 워프나 외부 actor 재배치 구간을 실제 화살 궤적으로 늘여 그리지 않는다.
	if (Distance > 3000.0f) { LastPosition = Position; DistanceSinceSample = 0.0f; return; }
	const FVector Direction = Delta / Distance;
	float Next = SampleSpacing - DistanceSinceSample;
	while (Next <= Distance)
	{
		Emit(LastPosition + Direction * Next, Direction);
		Next += SampleSpacing;
	}
	DistanceSinceSample = FMath::Fmod(DistanceSinceSample + Distance, SampleSpacing);
	LastPosition = Position;
	LastDirection = Direction;
}

void ASparrowFeatherTrail::StopTracking(const FVector& FinalLocation)
{
	if (!bReady || !bTracking) { return; }
	AppendSegment(FinalLocation);
	if (DistanceSinceSample >= 22.0f) { Emit(LastPosition, LastDirection); }
	if (SourceArrow.IsValid())
	{
		RemoveTickPrerequisiteActor(SourceArrow.Get());
		if (bDRoute) { SourceArrow->OnDestroyed.RemoveDynamic(this, &ASparrowFeatherTrail::OnTrackedArrowDestroyed); }
	}
	SourceArrow.Reset();
	bTracking = false;
	SetLifeSpan(FadeLifetime + (bDRoute ? .10f : .04f));
}

void ASparrowFeatherTrail::OnTrackedArrowDestroyed(AActor* DestroyedActor)
{
	if (DestroyedActor) { StopTracking(DestroyedActor->GetActorLocation()); }
}

void ASparrowFeatherTrail::Tick(float DeltaSeconds)
{
	Super::Tick(DeltaSeconds);
	if (!bReady || !IsValid(GetOwner()) || GetOwner()->IsActorBeingDestroyed()) { Destroy(); return; }
	Age += FMath::Max(DeltaSeconds, 0.0f);
	if (bTracking)
	{
		if (SourceArrow.IsValid() && !SourceArrow->IsActorBeingDestroyed()) { AppendSegment(SourceArrow->GetActorLocation()); }
		else { StopTracking(LastPosition); }
	}
	APlayerCameraManager* Camera = UGameplayStatics::GetPlayerCameraManager(this, 0);
	bool bAnyVisible = false;
	for (int32 Index = 0; Index < Samples.Num(); ++Index)
	{
		const FFeatherSample& Sample = Samples[Index];
		const float LocalAge = Age - Sample.BornAt;
		if (bDRoute && LocalAge < 0.0f && Sample.BornAt >= 0.0f) { bAnyVisible = true; }
		const bool bVisible = LocalAge >= 0.0f && LocalAge < FadeLifetime;
		Surfaces[Index]->SetVisibility(bVisible);
		if (!bVisible) { continue; }
		bAnyVisible = true;
		const float Side = Sample.Seed % 2 == 0 ? -1.0f : 1.0f;
		const FVector Right = FVector::CrossProduct(FVector::UpVector, Sample.Direction).GetSafeNormal();
		const float Drift = LocalAge * LocalAge * 44.0f;
		FVector Position = Sample.Position + Right * Side * (5.0f + Drift) + FVector::UpVector * (LocalAge * 12.0f);
		if (bDRoute)
		{
			const float FallTime = FMath::Max(0.0f, LocalAge * 1.85f - .04f);
			const float Sway = FMath::Sin(LocalAge * 4.1f + Sample.Seed * .7f) * 5.0f;
			Position = Sample.Position + Right * (Side * (14.0f + LocalAge * 12.0f) + Sway);
			Position -= Sample.Direction * (LocalAge * 11.0f);
			Position.Z = FMath::Max(GroundLimit, Sample.Position.Z - (22.0f * FallTime + 11.0f * FallTime * FallTime));
		}
		const FVector Normal = Camera ? Camera->GetCameraLocation() - Position : FVector::UpVector;
		const FQuat Facing = FRotationMatrix::MakeFromXZ(Sample.Direction, Normal).ToQuat();
		const float Turn = bDRoute ? Side * (.40f + .30f * FMath::SmoothStep(.24f, FadeLifetime, LocalAge)) + .10f * FMath::Sin(LocalAge * 4.4f + Sample.Seed) :
			Side * (.15f + LocalAge * .38f) + .035f * FMath::Sin(LocalAge * 11.0f + Sample.Seed);
		Surfaces[Index]->SetWorldLocationAndRotation(Position, Facing * FQuat(FVector::UpVector, Turn));
		const float Size = (Sample.Seed % 3 == 0 ? 1.10f : .88f) * (bForm ? 1.10f : 1.0f);
		Surfaces[Index]->SetWorldScale3D((bDRoute ? FVector(.98f * (2.0f / 3.0f), .70f * (2.0f / 3.0f), 1.0f) : FVector(.82f, .52f, 1.0f)) * Size);
		Materials[Index]->SetScalarParameterValue(TEXT("Age"), bDRoute ? LocalAge * 1.85f : LocalAge);
		Materials[Index]->SetScalarParameterValue(TEXT("Index"), Sample.Seed);
		const float Fade = 1.0f - FMath::SmoothStep(bDRoute ? .32f : .22f, FadeLifetime, LocalAge);
		Materials[Index]->SetScalarParameterValue(bDRoute ? TEXT("Strength") : TEXT("Envelope"), Fade);
	}
	if (!bTracking && !bAnyVisible) { Destroy(); }
}

void ASparrowFeatherTrail::EndPlay(const EEndPlayReason::Type EndPlayReason)
{
	if (SourceArrow.IsValid())
	{
		RemoveTickPrerequisiteActor(SourceArrow.Get());
		if (bDRoute) { SourceArrow->OnDestroyed.RemoveDynamic(this, &ASparrowFeatherTrail::OnTrackedArrowDestroyed); }
	}
	SourceArrow.Reset();
	bTracking = false;
	Super::EndPlay(EndPlayReason);
}
