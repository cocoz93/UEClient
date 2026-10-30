#include "SparrowSharpImpact.h"

#include "Camera/PlayerCameraManager.h"
#include "Components/StaticMeshComponent.h"
#include "Engine/StaticMesh.h"
#include "Engine/World.h"
#include "Particles/ParticleSystem.h"
#include "Particles/ParticleEmitter.h"
#include "Particles/ParticleLODLevel.h"
#include "Particles/ParticleModuleRequired.h"
#include "Particles/ParticleSystemComponent.h"
#include "Kismet/GameplayStatics.h"
#include "Materials/MaterialInstanceDynamic.h"

namespace
{
	UParticleSystem* WFinisherFlames()
	{
		static TWeakObjectPtr<UParticleSystem> Cached;
		if (Cached.IsValid()) { return Cached.Get(); }
		UParticleSystem* Source = LoadObject<UParticleSystem>(nullptr,
			TEXT("/Game/ParagonSparrow/FX/Particles/Sparrow/Abilities/Ultimate/FX/P_Sparrow_UltHit.P_Sparrow_UltHit"));
		if (!Source) { return nullptr; }
		UParticleSystem* Copy = DuplicateObject<UParticleSystem>(Source, GetTransientPackage(),
			MakeUniqueObjectName(GetTransientPackage(), UParticleSystem::StaticClass(), TEXT("WFinisherFlames")));
		Copy->SetFlags(RF_Transient);
		Copy->ClearFlags(RF_Public | RF_Standalone);
		Copy->Emitters.RemoveAll([](UParticleEmitter* Emitter)
		{
			return !Emitter || (Emitter->GetEmitterName() != TEXT("Main Flames") &&
				Emitter->GetEmitterName() != TEXT("Sparks") && Emitter->GetEmitterName() != TEXT("SparkTrailHeads"));
		});
		for (UParticleEmitter* Emitter : Copy->Emitters) { Emitter->UpdateModuleLists(); }
		Cached = Copy;
		return Copy;
	}
}

ASparrowSharpImpact::ASparrowSharpImpact()
{
	PrimaryActorTick.bCanEverTick = true;
	PrimaryActorTick.bStartWithTickEnabled = false;
	SetActorEnableCollision(false);
	SetCanBeDamaged(false);
	Surface = CreateDefaultSubobject<UStaticMeshComponent>(TEXT("ContactGlow"));
	SetRootComponent(Surface);
	Surface->SetCollisionEnabled(ECollisionEnabled::NoCollision);
	Surface->SetGenerateOverlapEvents(false);
	Surface->SetCanEverAffectNavigation(false);
	Surface->SetCastShadow(false);
	Surface->SetReceivesDecals(false);
	Tags.Append({TEXT("SparrowSkillFX"), TEXT("SparrowSharpImpact")});
}

void ASparrowSharpImpact::Initialize(int32 DetailPreviewStyle, const FVector& ShotDirection, bool bAscended, bool bCrystal)
{
	UStaticMesh* Plane = LoadObject<UStaticMesh>(nullptr, TEXT("/Engine/BasicShapes/Plane.Plane"));
	UMaterialInterface* Source = LoadObject<UMaterialInterface>(nullptr,
		TEXT("/Game/TopDown/Characters/Sparrow/Materials/M_SparrowSharpImpact.M_SparrowSharpImpact"));
	if (DetailPreviewStyle >= 1 && DetailPreviewStyle <= 11)
	{
		const TCHAR* Folder = bAscended && (DetailPreviewStyle == 6 || DetailPreviewStyle == 10) ?
			TEXT("AscendedArsenal20261026") : DetailPreviewStyle >= 6 ? TEXT("SharpArt20261026") : TEXT("SharpDetails20261026");
		Source = LoadObject<UMaterialInterface>(nullptr, *FString::Printf(
			TEXT("/Game/TopDown/Characters/Sparrow/Materials/%s/M_SharpT%dImpact.M_SharpT%dImpact"),
			Folder, DetailPreviewStyle, DetailPreviewStyle));
	}
	if (bCrystal)
	{
		const TCHAR* Folder = bAscended ? TEXT("AscendedArsenal20261026") : TEXT("Arsenal20261026");
		Source = LoadObject<UMaterialInterface>(nullptr, *FString::Printf(
			TEXT("/Game/TopDown/Characters/Sparrow/Materials/%s/M_GatherCrystalImpact.M_GatherCrystalImpact"), Folder));
		Tags.Add(TEXT("SparrowCrystalImpact"));
	}
	if (DetailPreviewStyle >= 12 && DetailPreviewStyle <= 14)
	{
		const TCHAR* Name = DetailPreviewStyle == 12 ? TEXT("M_WFinisherImpact") :
			DetailPreviewStyle == 13 ? TEXT("M_StudyS9Impact") : TEXT("M_StudyS10Impact");
		Source = LoadObject<UMaterialInterface>(nullptr, *FString::Printf(
			TEXT("/Game/TopDown/Characters/Sparrow/Materials/ImpactRevision20261027/%s.%s"), Name, Name));
		Tags.Add(DetailPreviewStyle == 12 ? TEXT("SparrowWFinalImpact") : TEXT("SparrowStudyFinalImpact"));
	}
	if (DetailPreviewStyle == 15 || DetailPreviewStyle == 16)
	{
		Source = LoadObject<UMaterialInterface>(nullptr,
			TEXT("/Game/TopDown/Characters/Sparrow/Materials/Renaissance20261027/M_RenImpact.M_RenImpact"));
		Tags.Add(TEXT("SparrowRenaissanceImpact"));
	}
	if (!GetWorld() || !IsValid(GetOwner()) || !Plane || !Source) { Destroy(); return; }
	Surface->SetStaticMesh(Plane);
	Material = UMaterialInstanceDynamic::Create(Source, this);
	if (DetailPreviewStyle == 15 || DetailPreviewStyle == 16)
	{
		Material->SetScalarParameterValue(TEXT("Index"), DetailPreviewStyle - 15.0f);
	}
	Surface->SetMaterial(0, Material);
	Surface->SetWorldScale3D(FVector(.95f, .95f, 1.0f));
	if (DetailPreviewStyle >= 6) { Surface->SetWorldScale3D(FVector(2.35f, 2.35f, 1.0f)); }
	bDirectional = DetailPreviewStyle == 5 || bCrystal || DetailPreviewStyle >= 12;
	if (bDirectional)
	{
		Direction = ShotDirection.GetSafeNormal();
		if (Direction.IsNearlyZero()) { Direction = FVector::ForwardVector; }
		SetActorLocation(GetActorLocation() + Direction * (bCrystal ? 12.0f : 36.0f));
		Surface->SetWorldScale3D(FVector(bCrystal ? 2.2f : 2.0f, 1.7f, 1.0f));
	}
	if (DetailPreviewStyle >= 12)
	{
		Surface->SetWorldScale3D(FVector(DetailPreviewStyle == 12 ? 3.8f : 2.3f,
			DetailPreviewStyle == 12 ? 3.6f : 1.9f, 1.0f));
		Material->SetScalarParameterValue(TEXT("Ascended"), bAscended ? 1.0f : 0.0f);
	}
	if (DetailPreviewStyle == 12)
	{
		// 단일 평면의 별무늬 대신 원본의 입체 불꽃·불티를 짧은 접촉 사건으로 묶는다.
		UParticleSystem* Flames = WFinisherFlames();
		if (Flames)
		{
			ContactFlames = NewObject<UParticleSystemComponent>(this, NAME_None, RF_Transient);
			ContactFlames->SetupAttachment(Surface);
			ContactFlames->SetAbsolute(false, true, true);
			ContactFlames->SetCollisionEnabled(ECollisionEnabled::NoCollision);
			ContactFlames->SetGenerateOverlapEvents(false);
			ContactFlames->SetCanEverAffectNavigation(false);
			ContactFlames->bAutoActivate = false;
			ContactFlames->SetTemplate(Flames);
			AddInstanceComponent(ContactFlames);
			ContactFlames->RegisterComponent();
			ContactFlames->SetWorldRotation(ShotDirection.Rotation());
			ContactFlames->SetWorldScale3D(FVector(1.45f));
			ContactFlames->SetFloatParameter(TEXT("Lifetime"), .3f);
			ContactFlames->ActivateSystem(true);
		}
	}
	StartedAt = GetWorld()->GetTimeSeconds();
	SetLifeSpan(DetailPreviewStyle == 12 ? .44f : DetailPreviewStyle >= 13 ? .26f : .20f);
	SetActorTickEnabled(true);
	Tick(0.0f);
}

void ASparrowSharpImpact::InitializeReference(const FVector& ShotDirection, bool bRefined, bool bPlume)
{
	UStaticMesh* Plane = LoadObject<UStaticMesh>(nullptr, TEXT("/Engine/BasicShapes/Plane.Plane"));
	UMaterialInterface* Source = LoadObject<UMaterialInterface>(nullptr, *FString::Printf(
		TEXT("/Game/TopDown/Characters/Sparrow/Materials/SharpReference20261027/%s/M_SharpReferenceImpact.M_SharpReferenceImpact"),
		bPlume ? TEXT("Plume") : bRefined ? TEXT("Refined") : TEXT("Base")));
	if (!GetWorld() || !IsValid(GetOwner()) || !Plane || !Source) { Destroy(); return; }
	Direction = ShotDirection.GetSafeNormal();
	bDirectional = false;
	Surface->SetStaticMesh(Plane);
	Material = UMaterialInstanceDynamic::Create(Source, this);
	Surface->SetMaterial(0, Material);
	Surface->SetWorldScale3D(FVector(.95f, .95f, 1.0f));
	Tags.Add(TEXT("SparrowSharpReferenceImpact"));
	if (bRefined) { Tags.Add(TEXT("SparrowSharpReferenceRefined")); }
	if (bPlume) { Tags.Add(TEXT("SparrowSharpReferencePlume")); }
	StartedAt = GetWorld()->GetTimeSeconds();
	SetLifeSpan(bRefined ? .24f : .20f);
	SetActorTickEnabled(true);
	Tick(0.0f);
}

void ASparrowSharpImpact::Tick(float DeltaSeconds)
{
	Super::Tick(DeltaSeconds);
	if (!Material || !IsValid(GetOwner()) || GetOwner()->IsActorBeingDestroyed()) { Destroy(); return; }
	const float Age = static_cast<float>(GetWorld()->GetTimeSeconds() - StartedAt);
	Material->SetScalarParameterValue(TEXT("Age"), Age);
	if (APlayerCameraManager* Camera = UGameplayStatics::GetPlayerCameraManager(this, 0))
	{
		const FVector Normal = Camera->GetCameraLocation() - GetActorLocation();
		Surface->SetWorldRotation(bDirectional ? FRotationMatrix::MakeFromXZ(Direction, Normal).Rotator() :
			FRotationMatrix::MakeFromZ(Normal).Rotator());
	}
}
