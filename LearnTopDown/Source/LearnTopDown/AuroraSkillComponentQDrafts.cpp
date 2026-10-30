// Q 덧붙임 시안(Aurora.FX.QAdd 비트, 10-21 「뭐가 문제지, 검기 날리는 게 문제인가 — 검기를 더 못 하겠다면 다른 추가 이펙트를 붙이는 건 어때」).
// 검기 그림은 그대로 두고, 찍은 장면에서 비어 있던 자리 — 휘두르는 칼 · 맞는 순간 · 화면 — 에 더한다(헤더 QAddTrailSeconds 설명).
#include "AuroraSkillComponent.h"

#include "Camera/CameraComponent.h"
#include "Camera/PlayerCameraManager.h"
#include "Components/MeshComponent.h"
#include "Components/StaticMeshComponent.h"
#include "Engine/World.h"
#include "HAL/IConsoleManager.h"
#include "Kismet/GameplayStatics.h"
#include "Materials/MaterialInstanceDynamic.h"
#include "TimerManager.h"
#include "TopDownCombatCharacter.h"

namespace
{
	// 10-21 「Q는 칼 궤적만 추가」로 1이 기본
	TAutoConsoleVariable<int32> CVarAuroraSlashAdd(
		TEXT("Aurora.FX.QAdd"), 1,
		TEXT("Ice wave extras draft bitmask (QStyle 6): 1 a white sword trail along the blade while she swings (default), 2 a cut mark slashed across each enemy hit that shatters + glowing ice bits flung on, 4 each enemy hit flashes icy white and freezes for an instant, 8 the screen shakes a little as each wave leaves and harder on each hit. 0 = none."));

	// 10-21 「검기 이펙트 시안 여러 개 — 다 만들어서」: 고르기 전까지 0(지금 그림)
	TAutoConsoleVariable<int32> CVarAuroraSlashShape(
		TEXT("Aurora.FX.QShape"), 0,
		TEXT("Big ice wave body draft (with QBlade 16): 0 the current lying crescent (default), 1 stood up on edge with its lower tip grazing the floor, 2 a crescent of solid ice chunks, 3 a thin bright blade line leaving a long afterglow, 4 a spinning ice ring with saw teeth."));

	// 10-21 「누운 초승달 형태가 좋은데 이펙트 시안을 더」(헤더 QSkinAuraScale 설명) → 「푸른 빛무리는 추가」로 1이 기본
	TAutoConsoleVariable<int32> CVarAuroraSlashSkin(
		TEXT("Aurora.FX.QSkin"), 1,
		TEXT("Big ice wave effect draft bitmask (with QBlade 16, the lying crescent kept): 1 a deep blue glow wrapped round it (default), 2 aurora colours from tip to tip (teal, blue, violet), 4 frost grain flowing back through its body, 8 a long blue afterglow of thin blade lines trailing it, 16 glowing ice crystals along the edge instead of the comb of cones. 0 = none."));

	// 칼자국을 대상 몸 가운데에서 카메라 쪽으로 당기는 거리(몸에 반쯤 묻히지 않게)
	constexpr float QAddMarkToCamera = 60.0f;
}

int32 UAuroraSkillComponent::GetQAdd() const
{
	return CVarAuroraSlashAdd.GetValueOnGameThread();
}

int32 UAuroraSkillComponent::GetQShape() const
{
	return CVarAuroraSlashShape.GetValueOnGameThread();
}

int32 UAuroraSkillComponent::GetQSkin() const
{
	return CVarAuroraSlashSkin.GetValueOnGameThread();
}

void UAuroraSkillComponent::OnQAddCast()
{
	if (GetQAdd() & 1)
	{
		// 세 번 휘두르는 내내 칼날을 따라 그린다(E 4와 같은 궤적 · 소켓 — Aurora.FX.ETrail·ETrailSockets)
		BeginSwordTrail(QAddTrailSeconds);
	}
}

void UAuroraSkillComponent::OnQAddLaunch()
{
	if (GetQAdd() & 8)
	{
		ShakeCamera(QAddShakeLaunch);
	}
}

void UAuroraSkillComponent::OnQAddHit(AActor* Target, const FVector& Direction, float Roll)
{
	const int32 Add = GetQAdd();
	UWorld* World = GetWorld();
	if (!Add || !IsValid(Target) || !World)
	{
		return;
	}
	const double Now = World->GetTimeSeconds();
	const FVector Center = Target->GetActorLocation();
	if (Add & 2)
	{
		// 칼자국: 카메라를 보고 화면 가로에서 검기가 기운 쪽으로 — 「/」 검기는 왼쪽 아래 → 오른쪽 위로 그어진다(Q2 칼자국과 같은 판·재질)
		UMaterialInterface* Material = CutMarkMaterial.LoadSynchronous();
		const APlayerCameraManager* Camera = UGameplayStatics::GetPlayerCameraManager(World, 0);
		if (PlaneMesh && Material && Camera)
		{
			const FRotationMatrix View(Camera->GetCameraRotation());
			const FVector Facing = -View.GetUnitAxis(EAxis::X);
			const float Tilt = FMath::DegreesToRadians(QAddMarkTilt) * Roll;
			const FVector Stroke = View.GetUnitAxis(EAxis::Y) * FMath::Cos(Tilt) + View.GetUnitAxis(EAxis::Z) * FMath::Sin(Tilt);
			// 판 앞면(Z)이 카메라를, 그림 위쪽(-Y)이 칼이 나가는 쪽을 본다.
			const FQuat Rotation = FRotationMatrix::MakeFromZY(Facing, -Stroke).ToQuat();
			if (UStaticMeshComponent* Mesh = SpawnTimedMesh(PlaneMesh, FTransform(Rotation, Center + Facing * QAddMarkToCamera,
				FVector(2.0f * QAddMarkHalfWidth / 100.0f, QAddMarkLength / 100.0f, 1.0f)), QAddMarkHold + CutMarkFadeSeconds + 0.2f))
			{
				UMaterialInstanceDynamic* Dynamic = UMaterialInstanceDynamic::Create(Material, Mesh);
				Dynamic->SetScalarParameterValue(TEXT("Reveal"), 0.0f);
				Mesh->SetMaterial(0, Dynamic);
				Mesh->SetCastShadow(false);
				Mesh->SetReceivesDecals(false);
				// 깨지는 때를 앞으로 잡아 두면 BladeTick이 그때까지 그대로 두었다가 번쩍이며 지운다
				CutMarks.Add({Mesh, Dynamic, Now, Now + QAddMarkHold});
				if (!World->GetTimerManager().IsTimerActive(BladeTimer))
				{
					World->GetTimerManager().SetTimer(BladeTimer, this, &UAuroraSkillComponent::BladeTick, 1.0f / 60.0f, true);
				}
			}
		}
		// 빛나는 얼음 조각이 검기가 나는 쪽으로 튀었다 떨어진다(QBig 4 산산조각과 같은 조각)
		UMaterialInterface* Glow = GlowIceMaterial.LoadSynchronous();
		const float FloorZ = FindFloorZ(Center, GetFeetLocation().Z);
		for (int32 Bit = 0; Bit < QAddShardCount; ++Bit)
		{
			FAuroraShard Shard;
			Shard.FloorZ = FloorZ + 3.0f;
			Shard.Start = Center + FMath::VRand() * 15.0f;
			Shard.Velocity = Direction * FMath::FRandRange(250.0f, 550.0f) + FMath::VRand() * 150.0f +
				FVector(0.0f, 0.0f, FMath::FRandRange(150.0f, 300.0f));
			Shard.Born = Now;
			Shard.Life = FMath::FRandRange(0.5f, 0.9f);
			const float Width = FMath::FRandRange(8.0f, 14.0f);
			Shard.Size = FVector(Width, Width * FMath::FRandRange(0.4f, 0.7f), FMath::FRandRange(25.0f, 45.0f));
			AddShard(Shard, Now, Glow);
		}
	}
	if (Add & 8)
	{
		ShakeCamera(QAddShakeHit);
	}
	if (Add & 4)
	{
		FlashHitTarget(Target);
	}
	UE_LOG(LogTemp, Display, TEXT("AURORA_QADD hit=%s add=%d roll=%.0f"), *Target->GetName(), Add, Roll);
}

void UAuroraSkillComponent::ShakeCamera(float Strength)
{
	UWorld* World = GetWorld();
	UCameraComponent* Camera = Character.IsValid() ? Character->FindComponentByClass<UCameraComponent>() : nullptr;
	if (!World || !Camera)
	{
		return;
	}
	// 흔드는 중에 또 흔들면 원래 자리는 처음 것을 지키고, 남은 세기보다 세면 새로 시작한다
	if (!ShakeCameraComponent.IsValid())
	{
		ShakeCameraComponent = Camera;
		ShakeRelative = Camera->GetRelativeLocation();
		ShakeStrength = 0.0f;
	}
	const double Now = World->GetTimeSeconds();
	const float Left = ShakeStrength * FMath::Max(1.0f - static_cast<float>(Now - ShakeStarted) / QAddShakeSeconds, 0.0f);
	if (Strength >= Left)
	{
		ShakeStrength = Strength;
		ShakeStarted = Now;
	}
	if (!World->GetTimerManager().IsTimerActive(ShakeTimer))
	{
		World->GetTimerManager().SetTimer(ShakeTimer, this, &UAuroraSkillComponent::ShakeTick, 1.0f / 60.0f, true);
	}
	ShakeTick();
}

void UAuroraSkillComponent::ShakeTick()
{
	UWorld* World = GetWorld();
	USceneComponent* Camera = ShakeCameraComponent.Get();
	const float Alpha = World ? 1.0f - static_cast<float>(World->GetTimeSeconds() - ShakeStarted) / QAddShakeSeconds : 0.0f;
	if (!Camera || Alpha <= 0.0f)
	{
		if (Camera)
		{
			Camera->SetRelativeLocation(ShakeRelative);
		}
		if (World)
		{
			World->GetTimerManager().ClearTimer(ShakeTimer);
		}
		ShakeCameraComponent.Reset();
		return;
	}
	// 카메라는 붐 끝에 돌리지 않고 붙어 있어 붙은 자리의 Y·Z가 화면 가로·세로다
	const float Amount = ShakeStrength * Alpha;
	Camera->SetRelativeLocation(ShakeRelative + FVector(0.0f, FMath::FRandRange(-1.0f, 1.0f) * Amount, FMath::FRandRange(-1.0f, 1.0f) * Amount));
}

void UAuroraSkillComponent::FlashHitTarget(AActor* Target)
{
	UWorld* World = GetWorld();
	if (!IsValid(Target) || !World)
	{
		return;
	}
	// 덧씌움(오버레이)은 몸을 한 번 더 그 재질로 그린다 — 분신 재질은 캐릭터 메시용 표시가 있어 허수아비 몸에도 그대로 나온다.
	// 이미 덧씌움이 있는 부품(다른 효과)은 건드리지 않는다.
	TArray<TWeakObjectPtr<UMeshComponent>> Flashed;
	if (UMaterialInterface* Ice = CloneIceMaterial.LoadSynchronous())
	{
		TArray<UMeshComponent*> Meshes;
		Target->GetComponents<UMeshComponent>(Meshes);
		for (UMeshComponent* Mesh : Meshes)
		{
			if (Mesh->IsVisible() && !Mesh->GetOverlayMaterial())
			{
				Mesh->SetOverlayMaterial(Ice);
				Flashed.Add(Mesh);
			}
		}
	}
	// 대상만 멈춘다(캐릭터는 다음 칼을 그대로 휘두른다). 다른 멈칫(W·V)이 잡은 대상이면 그쪽에 맡긴다.
	const bool bStop = Target->CustomTimeDilation == 1.0f;
	if (bStop)
	{
		Target->CustomTimeDilation = HitStopDilation;
	}
	TWeakObjectPtr<AActor> Weak = Target;
	World->GetTimerManager().SetTimer(AddReleaseTimer(), FTimerDelegate::CreateWeakLambda(this, [Flashed]()
	{
		for (const TWeakObjectPtr<UMeshComponent>& Mesh : Flashed)
		{
			if (Mesh.IsValid())
			{
				Mesh->SetOverlayMaterial(nullptr);
			}
		}
	}), QAddFlashSeconds, false);
	if (bStop)
	{
		World->GetTimerManager().SetTimer(AddReleaseTimer(), FTimerDelegate::CreateWeakLambda(this, [Weak]()
		{
			if (AActor* Actor = Weak.Get())
			{
				Actor->CustomTimeDilation = 1.0f;
			}
		}), QAddHitStopSeconds, false);
	}
	UE_LOG(LogTemp, Display, TEXT("AURORA_QADD flash=%s meshes=%d stopped=%d"), *Target->GetName(), Flashed.Num(), bStop);
}

void UAuroraSkillComponent::EndQAdd()
{
	if (UWorld* World = GetWorld())
	{
		World->GetTimerManager().ClearTimer(ShakeTimer);
	}
	if (USceneComponent* Camera = ShakeCameraComponent.Get())
	{
		Camera->SetRelativeLocation(ShakeRelative);
	}
	ShakeCameraComponent.Reset();
}
