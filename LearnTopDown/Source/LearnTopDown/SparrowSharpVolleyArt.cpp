#include "SparrowSharpVolley.h"

#include "Camera/PlayerCameraManager.h"
#include "Components/StaticMeshComponent.h"
#include "Engine/StaticMesh.h"
#include "Kismet/GameplayStatics.h"
#include "Materials/MaterialInstanceDynamic.h"

bool ASparrowSharpVolley::InitializeArtPresentation(UStaticMesh* Plane)
{
	UMaterialInterface* Source = LoadObject<UMaterialInterface>(nullptr, *FString::Printf(
		TEXT("/Game/TopDown/Characters/Sparrow/Materials/%s/M_SharpT%dBody.M_SharpT%dBody"),
		bAscended && (DetailPreviewStyle == 6 || DetailPreviewStyle == 10) ? TEXT("AscendedArsenal20261026") : TEXT("SharpArt20261026"),
		DetailPreviewStyle, DetailPreviewStyle));
	if (!Plane || !Source) { return false; }
	const int32 Design = DetailPreviewStyle - 6;
	const int32 Count = Design == 4 ? 14 : Design == 5 ? 12 : Design == 0 ? (bAscended ? 4 : 2) : 3;
	for (int32 Index = 0; Index < Count; ++Index)
	{
		UMaterialInstanceDynamic* Material = UMaterialInstanceDynamic::Create(Source, this);
		Material->SetScalarParameterValue(TEXT("Index"), static_cast<float>(Index));
		Material->SetScalarParameterValue(TEXT("ShotAge"), 100.0f);
		UStaticMeshComponent* Part = NewObject<UStaticMeshComponent>(this, NAME_None, RF_Transient);
		Part->SetMobility(EComponentMobility::Movable);
		Part->SetupAttachment(RootComponent);
		Part->SetCollisionEnabled(ECollisionEnabled::NoCollision);
		Part->SetGenerateOverlapEvents(false);
		Part->SetCanEverAffectNavigation(false);
		Part->SetCastShadow(false);
		Part->SetReceivesDecals(false);
		Part->SetStaticMesh(Plane);
		Part->SetMaterial(0, Material);
		Part->SetVisibility(false);
		Part->ComponentTags.Add(TEXT("SparrowSharpArt"));
		AddInstanceComponent(Part);
		Part->RegisterComponent();
		ArtSurfaces.Add(Part);
		ArtMaterials.Add(Material);
	}
	return true;
}

void ASparrowSharpVolley::UpdateArtPresentation(float Age, float Since, const FVector& Origin)
{
	const int32 Design = DetailPreviewStyle - 6;
	const FVector Right = FVector::CrossProduct(FVector::UpVector, Direction).GetSafeNormal();
	FVector Normal = FVector::UpVector;
	if (APlayerCameraManager* Camera = UGameplayStatics::GetPlayerCameraManager(this, 0))
	{
		Normal = Camera->GetCameraLocation() - Origin;
	}
	const FQuat Facing = FRotationMatrix::MakeFromXZ(Direction, Normal).ToQuat();
	const FVector ScreenAcross = Facing.GetAxisY();
	const float Open = FMath::SmoothStep(0.0f, .10f, Age);
	const float Compress = FMath::SmoothStep(.20f, .36f, Age);
	const bool bFired = LastReleaseAge >= 0.0f;
	const float Burst = bFired ? FMath::Clamp(Since / .17f, 0.0f, 1.0f) : 0.0f;
	for (int32 Index = 0; Index < ArtSurfaces.Num(); ++Index)
	{
		FVector Position = Origin;
		FVector Scale(2.7f, 2.5f, 1.0f);
		FQuat Rotation = Facing;
		const float Phase = Index * 2.399963f;
		if (Design == 0)
		{
			Position += Direction * 20.0f;
			Rotation = FRotationMatrix::MakeFromXZ(Right, Direction).ToQuat();
			Scale = FVector(3.05f, 3.05f, 1.0f);
			Position += Direction * (Index * 8.0f);
			if (bAscended && Index >= 2)
			{
				Position += Right * (Index == 2 ? -24.0f : 19.0f) + FVector::UpVector * (Index == 2 ? 12.0f : -9.0f);
				Scale *= Index == 2 ? .78f : 1.12f;
			}
		}
		else if (Design == 1)
		{
			// B: 짧은 빛결만 활 가까이 감긴다. 화면 뒤까지 늘어지는 긴 매듭은 만들지 않는다.
			Position += Direction * (-18.0f + Index * 8.0f) + Right * ((Index - 1) * 19.0f);
			Rotation = Facing * FQuat(FVector::ForwardVector, FMath::DegreesToRadians((Index - 1) * 24.0f));
			Scale = FVector(2.55f, 1.95f, 1.0f);
		}
		else if (Design == 2)
		{
			Position += Direction * (Index * 32.0f + 8.0f);
			Rotation = Facing * FQuat(FVector::ForwardVector, FMath::DegreesToRadians((Index - 1) * 20.0f));
			Scale = FVector(1.6f - Compress * .5f, (2.1f + Index * .25f) * Open, 1.0f);
		}
		else if (Design == 3)
		{
			Position += Direction * (44.0f - Compress * 16.0f);
			Rotation = Facing * FQuat(FVector::ForwardVector, Index * PI / 3.0f + Age * 1.6f);
			Scale = FVector(2.65f - Compress * .55f, (2.0f - Compress * .55f) * Open, 1.0f);
		}
		else if (Design == 4)
		{
			const float Radius = (62.0f + (Index % 4) * 14.0f) * Open * (1.0f - Compress * .58f + Burst * 1.25f);
			Position += Right * FMath::Cos(Phase) * Radius + FVector::UpVector * FMath::Sin(Phase) * Radius;
			Position += Direction * (-25.0f + (Index % 5) * 14.0f + Burst * 35.0f);
			Rotation = Facing * FQuat(FVector::UpVector, Phase + Age * (Index % 2 == 0 ? 1.4f : -1.1f));
			Scale = FVector(.40f + (Index % 3) * .12f, .8f + (Index % 4) * .16f, 1.0f);
		}
		else
		{
			// F: 연결선 없이 작은 광편이 모이고 순차 점화된다. 발사 때만 별빛으로 열린다.
			const float Radius = (72.0f + (Index % 3) * 16.0f) * (1.0f - Compress * .63f + Burst * .8f);
			Position += ScreenAcross * FMath::Sin(Phase) * Radius;
			Position += Direction * (24.0f + FMath::Cos(Phase) * Radius * .65f);
			Position += Right * ((Index % 3 - 1) * 12.0f);
			Scale = FVector(.55f + (Index % 3) * .1f, .55f + (Index % 3) * .1f, 1.0f);
		}
		ArtSurfaces[Index]->SetWorldLocationAndRotation(Position, Rotation);
		ArtSurfaces[Index]->SetWorldScale3D(Scale);
		ArtSurfaces[Index]->SetVisibility(Age > .005f && (!bFired || Since < .28f));
		ArtMaterials[Index]->SetScalarParameterValue(TEXT("Age"), Age);
		ArtMaterials[Index]->SetScalarParameterValue(TEXT("ShotAge"), Since);
	}
}
