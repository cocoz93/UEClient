// R 얼음 난무(10-20 밤 R 제로베이스 러프 시안 1 → 10-21 「R은 일단 1로」). Aurora.FX.RDraft 1(기본)이면 그 전 R(냉기 장판 회오리) 대신 쓴다.
// 대상을 꿰뚫는 지름 셋을 60도씩 돌려 베며 지나가 바닥에 눈꽃(지름마다 팔 둘, M_Aurora_FlakeArm)을 남기고, 돌아와 가리키면 눈꽃이
// 번쩍이며 깨진다(빛 · 팔 끝 얼음 조각 · 고리). 첫 판(10-21 1시)은 같은 굵기 막대 15개를 판으로 띄워 「눈 모양 너무 퀄리티 낮아 보인다」.
// 순간이동 시안 Aurora.FX.RBlink(「막 순간이동하면서 때리는데 왜 이렇게 어색해 보이지 — 좋은 방법, 시안 더」): 1 카메라 제자리 ·
// 2 사라졌다 나타남 · 4 얼음 잔상 · 8 미끄러지듯. 러프 시안 2 빙하 낙하 · 3 칼날 폭풍 · 5 거대 얼음검은 지웠고 4 얼음 분신은 F로 옮겼다.
#include "AuroraSkillComponent.h"

#include "Animation/AnimSequence.h"
#include "Components/CapsuleComponent.h"
#include "Components/DecalComponent.h"
#include "Components/PointLightComponent.h"
#include "Components/SkeletalMeshComponent.h"
#include "Components/StaticMeshComponent.h"
#include "Engine/SkinnedAsset.h"
#include "Engine/World.h"
#include "GameFramework/SpringArmComponent.h"
#include "HAL/IConsoleManager.h"
#include "Kismet/GameplayStatics.h"
#include "Materials/MaterialInstanceDynamic.h"
#include "Particles/ParticleSystem.h"
#include "TimerManager.h"
#include "TopDownCombatCharacter.h"

namespace
{
	TAutoConsoleVariable<int32> CVarAuroraRDraft(
		TEXT("Aurora.FX.RDraft"), 1,
		TEXT("R: 0 the old frost field channel, 1 ice flurry - blink through the target three times leaving a snowflake of cuts on the floor that shatters (default)."));
	// 10-21 「R은 15로 가자」로 15(넷 다)가 기본
	TAutoConsoleVariable<int32> CVarAuroraRBlink(
		TEXT("Aurora.FX.RBlink"), 15,
		TEXT("Ice flurry blink draft bitmask: 1 the camera holds still where she started instead of jumping with her, 2 she vanishes while she crosses and reappears striking, 4 an ice afterimage is left where she leaves, 8 she glides across fast instead of teleporting. 15 = all (default), 0 = none."));

	// 지름 Arm(0~2)을 60도씩: 한쪽 끝으로 옮겨 섰다가(안 그음) 맞은편 끝으로 베며 지나감(그음), BlinkStep초마다 → 처음 자리로 돌아와
	// BlinkShatterDelay초 뒤 깨진다
	constexpr int32 BlinkCuts = 6;
	constexpr float BlinkFirst = 0.15f;
	constexpr float BlinkStep = 0.13f;
	// 10-25 「R은 눈 모양 1/2 정도로 줄이고, 분신들이 공격하는 것도 그에 맞춰」: 200 → 100(옮겨 서는 자리 = 눈꽃 지름 끝이라 같이 줄어든다).
	// 맞는 반경(칼선 120 · 깨짐 220)은 그대로
	// 93차 「분신과의 거리를 약간만 더 멀게 — 지금 좁은 원을 그리듯 생기는데 더 컸으면」: 서는 자리만 100 → 140.
	// 바닥 눈꽃·깨지는 조각 자리는 그 전 크기(BlinkArmRadius) 그대로 둔다(10-25 「눈 모양 1/2」)
	constexpr float BlinkRadius = 140.0f;
	constexpr float BlinkArmRadius = 100.0f;
	constexpr float BlinkSearch = 500.0f;
	constexpr float BlinkCutDamage = 8.0f;
	constexpr float BlinkShatterDelay = 0.12f;
	constexpr float BlinkShatterDamage = 30.0f;
	constexpr float BlinkCutRate = 1.4f;
	// 칼 빛: 지나간 줄 위에 잠깐 남는 판(Q2 칼자국 재질, 바닥 위 BlinkStreakHeight) — BlinkStreakSeconds 뒤 사라짐
	constexpr float BlinkStreakWidth = 40.0f;
	constexpr float BlinkStreakHeight = 30.0f;
	constexpr float BlinkStreakSeconds = 0.1f;
	// 바닥 눈꽃 팔: 크기 = 반경 × BlinkArmScale(그림 팔 끝 0.46 + 마름모) · 베며 지나가는 쪽으로 BlinkArmSweep초에 드러남 ·
	// 깨질 때 밝기·선 빛을 BlinkFlash*로 올렸다가 BlinkFadeSeconds에 걷음(재질 기본 선 0.95 · 퍼진 빛 0.4)
	constexpr float BlinkArmScale = 1.1f;
	constexpr float BlinkArmSweep = 0.08f;
	constexpr float BlinkArmSeconds = 3.0f;
	constexpr float BlinkFlashBrightness = 3.5f;
	constexpr float BlinkFlashGlow = 6.0f;
	constexpr float BlinkFadeSeconds = 0.35f;
	constexpr float BlinkArmLine = 0.95f;
	constexpr float BlinkArmHalo = 0.4f;
	// 깨질 때 가운데 빛(칸델라 → 0, BlinkLightSeconds) · 닿는 거리
	constexpr float BlinkLightCandelas = 150.0f;
	constexpr float BlinkLightSeconds = 0.45f;
	constexpr float BlinkLightReach = 520.0f;
	// 순간이동 시안: 2 숨는 시간 · 4 잔상이 흐려져 사라지는 시간 · 8 미끄러져 가는 시간
	constexpr float BlinkHideSeconds = 0.07f;
	// 잔상 = 칼을 휘두르는 얼음 분신(10-25 「R은 얼음 분신들의 애니메이션이 좀 어정쩡한데, 검을 휘두르는 형태로」 — 전엔 떠나는 순간
	// 자세 하나로 굳어 0.3초 흐려졌다): 칼이 가장 빠른 순간 BlinkAfterimageLead초 앞부터 휘두르고, 앞 BlinkAfterimageHold 몫은
	// 또렷하게 · 나머지 동안 흐려진다
	constexpr float BlinkAfterimageSeconds = 0.45f;
	constexpr float BlinkAfterimageLead = 0.12f;
	constexpr float BlinkAfterimageHold = 0.4f;

	// 이어서 「다른 휘두르는 애니메이션 없어? 지금도 어정쩡해 보이는데」 — 잔상 동작 시안 → 「일단 평타 A, D로 가자」로 6(빠른 공격 A·D)이 기본. 1~7은 처음부터 끝까지 한 번
	// 휘두르고(BlinkSwingRate배, 수명 = 동작 길이 ÷ 배속, BlinkSwingMaxSeconds까지) 짝을 Cut마다 번갈아. 몸(순간이동하는 오로라)은 그대로.
	TAutoConsoleVariable<int32> CVarAuroraRSwing(
		TEXT("Aurora.FX.RSwing"), 6,
		TEXT("Ice flurry afterimage swing draft: 0 the Q2 cuts from just before the fastest moment, 1 the same Q2 cuts from the start, 2 basic attacks A/B, 3 basic attack C, 4 slow attacks A/B, 5 slow attacks C/D, 6 fast attacks A/D (default), 7 the airborne slash."));
	struct FBlinkSwing
	{
		const TCHAR* First;
		const TCHAR* Second;
	};
	const FBlinkSwing BlinkSwings[] = {
		{TEXT("Primary_Attack_Fast_C"), TEXT("Primary_Attack_Fast_B")},
		{TEXT("Primary_Attack_A"), TEXT("Primary_Attack_B")},
		{TEXT("Primary_Attack_C"), TEXT("Primary_Attack_C")},
		{TEXT("Primary_Attack_Slow_A"), TEXT("Primary_Attack_Slow_B")},
		{TEXT("Primary_Attack_Slow_C"), TEXT("Primary_Attack_Slow_D")},
		{TEXT("Primary_Attack_Fast_A"), TEXT("Primary_Attack_Fast_D")},
		{TEXT("Melee_Attack_Air"), TEXT("Melee_Attack_Air")}};
	constexpr float BlinkSwingRate = 1.3f;
	constexpr float BlinkSwingMaxSeconds = 0.8f;

	UAnimSequence* LoadBlinkSwing(const TCHAR* Name)
	{
		return TSoftObjectPtr<UAnimSequence>(FSoftObjectPath(FString::Printf(
			TEXT("/Game/ParagonAurora/Characters/Heroes/Aurora/Animations/%s.%s"), Name, Name))).LoadSynchronous();
	}
	constexpr float BlinkGlideSeconds = 0.07f;
	constexpr int32 BlinkFadeSteps = 6;
}

int32 UAuroraSkillComponent::GetRDraft() const
{
	return CVarAuroraRDraft.GetValueOnGameThread();
}

bool UAuroraSkillComponent::BeginRDraft(int32 Draft, const FVector& Aim)
{
	USkeletalMeshComponent* Mesh = Character.IsValid() ? Character->GetMesh() : nullptr;
	UWorld* World = GetWorld();
	if (!Mesh || !Mesh->GetAnimInstance() || !World || Draft != 1)
	{
		return RejectInput(TEXT("Unavailable"));
	}
	EndRDraft();
	// 이어서 「A를 사용하면 분신들도 얼음 방어막 달고 있던데」: 보호막은 몸통 밑(루트)에 붙어 있어 순간이동 동안 몸만 숨고 보호막은 서는 자리마다
	// 따라다녔다 → 난무 동안 숨기고 돌아오면(깨질 때·끝날 때) 다시 보인다(ShowBlinkArmor)
	ShowBlinkArmor(false);
	PrepareCast(EAuroraSkill::FrostField, Aim);
	StartCooldown(EAuroraSkill::FrostField);
	BlinkStyle = CVarAuroraRBlink.GetValueOnGameThread();
	const uint32 Generation = CastGeneration;
	FTimerManager& Timers = World->GetTimerManager();
	// 겨눈 자리에서 가장 가까운 대상 둘레를 돈다(없으면 겨눈 자리)
	TArray<AActor*> Targets;
	GatherTargets(Aim, BlinkSearch, Targets);
	AActor* Nearest = nullptr;
	for (AActor* Target : Targets)
	{
		if (!Nearest || FVector::DistSquared2D(Target->GetActorLocation(), Aim) < FVector::DistSquared2D(Nearest->GetActorLocation(), Aim))
		{
			Nearest = Target;
		}
	}
	BlinkTarget = Nearest;
	BlinkHome = Character->GetActorLocation();
	BlinkLast = BlinkHome;
	const FVector Around = Nearest ? Nearest->GetActorLocation() : Aim;
	BlinkCenter = FVector(Around.X, Around.Y, GetFeetLocation().Z);
	// 87차 R-2 「감옥 먼저」: 대상 둘레 고드름 고리 → 마지막 칼 직후 감옥째 터짐(AuroraSkillComponentPolish.cpp)
	BeginRPrison(BlinkCenter, BlinkFirst + BlinkStep * BlinkCuts + 0.1f, Nearest);
	if (BlinkStyle & 1)
	{
		// 시안 1: 카메라 붐을 지금 자리에 세워 둔다(몸을 따라 화면이 튀지 않게) — 깨질 때·끝날 때 되돌린다
		if (USpringArmComponent* Boom = Character->FindComponentByClass<USpringArmComponent>())
		{
			BlinkBoom = Boom;
			BlinkBoomRelative = Boom->GetRelativeLocation();
			const FVector Held = Boom->GetComponentLocation();
			Boom->SetUsingAbsoluteLocation(true);
			Boom->SetWorldLocation(Held);
		}
	}
	PlayFullBody(ChargeLungeAnimation, 1.6f);
	for (int32 Cut = 0; Cut <= BlinkCuts; ++Cut)
	{
		Timers.SetTimer(Cut == 0 ? ActionTimer : AddReleaseTimer(), FTimerDelegate::CreateUObject(this, &UAuroraSkillComponent::BlinkCut,
			Generation, Cut), BlinkFirst + BlinkStep * Cut, false);
	}
	const float Ends = BlinkFirst + BlinkStep * BlinkCuts + 0.45f;
	Timers.SetTimer(RecoveryTimer, this, &UAuroraSkillComponent::FinishCast, Ends, false);
	// 도중에 끊겨도 카메라는 돌려 놓는다
	Timers.SetTimer(AddReleaseTimer(), FTimerDelegate::CreateWeakLambda(this, [this]()
	{
		RestoreBlinkCamera();
	}), Ends, false);
	UE_LOG(LogTemp, Display, TEXT("AURORA_RDRAFT start=%d blink=%d aim=%s"), Draft, BlinkStyle, *Aim.ToCompactString());
	return true;
}

void UAuroraSkillComponent::BlinkCut(uint32 Generation, int32 Cut)
{
	if (!bCasting || Generation != CastGeneration || !Character.IsValid() || !GetWorld())
	{
		return;
	}
	UWorld* World = GetWorld();
	const double Now = World->GetTimeSeconds();
	if (const AActor* Target = BlinkTarget.Get())
	{
		BlinkCenter = FVector(Target->GetActorLocation().X, Target->GetActorLocation().Y, BlinkCenter.Z);
	}
	const float Z = Character->GetActorLocation().Z;
	FVector Away = (BlinkHome - BlinkCenter).GetSafeNormal2D();
	if (Away.IsNearlyZero())
	{
		Away = -Character->GetActorForwardVector().GetSafeNormal2D();
	}
	// 지름 Arm(0~2)의 한쪽 끝(짝수 번째, 안 그음) → 맞은편 끝(홀수 번째, 그음). 마지막에 처음 자리로(안 그음).
	const bool bHome = Cut >= BlinkCuts;
	const FVector Along = Away.RotateAngleAxis(60.0f * (Cut / 2), FVector::UpVector);
	const FVector Spot = bHome ? BlinkHome :
		FVector(BlinkCenter.X, BlinkCenter.Y, Z) + Along * BlinkRadius * (Cut % 2 == 0 ? 1.0f : -1.0f);
	const bool bDraw = !bHome && Cut % 2 == 1;
	// 떠나는 자리: 번쩍 + 시안 4 얼음 잔상
	if (LanceFlash)
	{
		UGameplayStatics::SpawnEmitterAtLocation(World, LanceFlash, Character->GetActorLocation());
	}
	if (BlinkStyle & 4)
	{
		// 떠나는 자리에서 휘두르던 칼(Cut - 1번째 — 짝수 번째가 첫 칼)을 잔상이 마저 휘두른다
		LeaveBlinkAfterimage(Cut % 2 == 1);
	}
	if (bDraw)
	{
		const FVector Stroke = (Spot - BlinkLast) * FVector(1.0f, 1.0f, 0.0f);
		// 칼 빛: Q2 칼자국 판을 지나간 줄 위에 눕혀(그림 위쪽(-Y)이 나간 쪽) BlinkStreakSeconds 뒤 사라지게
		UMaterialInterface* Streak = CutMarkMaterial.LoadSynchronous();
		if (PlaneMesh && Streak && Stroke.Size() > 10.0f)
		{
			const FVector Middle = (BlinkLast + Spot) * 0.5f;
			const FQuat Rotation = FRotationMatrix::MakeFromZY(FVector::UpVector, -Stroke.GetSafeNormal()).ToQuat();
			if (UStaticMeshComponent* Mark = SpawnTimedMesh(PlaneMesh, FTransform(Rotation, FVector(Middle.X, Middle.Y, BlinkCenter.Z + BlinkStreakHeight),
				FVector(BlinkStreakWidth / 100.0f, Stroke.Size() / 100.0f, 1.0f)), 1.0f))
			{
				UMaterialInstanceDynamic* Dynamic = UMaterialInstanceDynamic::Create(Streak, Mark);
				Dynamic->SetScalarParameterValue(TEXT("Reveal"), 0.0f);
				Mark->SetMaterial(0, Dynamic);
				Mark->SetCastShadow(false);
				Mark->SetReceivesDecals(false);
				CutMarks.Add({Mark, Dynamic, Now, Now + BlinkStreakSeconds});
				if (!World->GetTimerManager().IsTimerActive(BladeTimer))
				{
					World->GetTimerManager().SetTimer(BladeTimer, this, &UAuroraSkillComponent::BladeTick, 1.0f / 60.0f, true);
				}
			}
		}
		// 바닥 눈꽃 팔(지름 하나): 베며 지나가는 쪽으로 드러난다
		if (UDecalComponent* Arm = SweepFloorDecal(FlakeArmMaterial.LoadSynchronous(), BlinkCenter, Stroke.GetSafeNormal(),
			BlinkArmRadius * BlinkArmScale, BlinkArmSeconds, BlinkArmSweep))
		{
			Arm->SetSortOrder(1);
			BlinkArms.Add(Arm);
			BlinkArmDirections.Add(Stroke.GetSafeNormal());
		}
		ApplyAreaDamage(BlinkCenter, 120.0f, BlinkCutDamage, TEXT("SLOW"), 1.0f);
	}
	// 옮겨 간다: 시안 8은 BlinkGlideSeconds에 미끄러지듯(RDraftTick), 아니면 곧바로
	if (BlinkStyle & 8)
	{
		GlideFrom = Character->GetActorLocation();
		GlideTo = Spot;
		GlideStarted = Now;
		World->GetTimerManager().SetTimer(RDraftTimer, this, &UAuroraSkillComponent::RDraftTick, 1.0f / 60.0f, true);
	}
	else
	{
		Character->SetActorLocation(Spot, false, nullptr, ETeleportType::TeleportPhysics);
	}
	Character->SetActorRotation(FRotator(0.0f, (BlinkCenter - Spot).Rotation().Yaw, 0.0f));
	if (BlinkStyle & 2)
	{
		// 시안 2: 지나가는 동안(칼 빛이 그어지는 동안) 몸을 숨겼다가 베는 자세로 나타난다
		USkeletalMeshComponent* Body = Character->GetMesh();
		Body->SetVisibility(false, true);
		const TWeakObjectPtr<USkeletalMeshComponent> WeakBody = Body;
		World->GetTimerManager().SetTimer(AddReleaseTimer(), FTimerDelegate::CreateWeakLambda(this, [WeakBody]()
		{
			if (USkeletalMeshComponent* Shown = WeakBody.Get())
			{
				Shown->SetVisibility(true, true);
			}
		}), BlinkHideSeconds, false);
	}
	BlinkLast = Spot;
	if (!bHome)
	{
		// 옮겨 설 때마다 Q2의 두 칼(「\」·「/」)을 번갈아 칼이 가장 빠른 순간 앞부터
		const bool bFirst = Cut % 2 == 0;
		PlayFullBody(bFirst ? CrossFirstAnimation : CrossSecondAnimation, BlinkCutRate,
			FMath::Max(0.0f, (bFirst ? FrostCrossFirstCut : FrostCrossSecondCut) - 0.1f));
		UE_LOG(LogTemp, Display, TEXT("AURORA_RDRAFT blink=%d at=%s"), Cut, *Spot.ToCompactString());
		return;
	}
	// 돌아와 칼로 가리키면 눈꽃이 깨진다
	PlayFullBody(Skills[EAuroraSkill::FrostField].Animation, 1.3f, 0.15f);
	World->GetTimerManager().SetTimer(AddReleaseTimer(), FTimerDelegate::CreateUObject(this, &UAuroraSkillComponent::ShatterBlinkFlake,
		BlinkTarget, BlinkCenter), BlinkShatterDelay, false);
}

void UAuroraSkillComponent::ShatterBlinkFlake(TWeakObjectPtr<AActor> Target, FVector Center)
{
	UWorld* World = GetWorld();
	if (!World || !Character.IsValid())
	{
		return;
	}
	const double Now = World->GetTimeSeconds();
	for (FAuroraCutMark& Mark : CutMarks)
	{
		if (Mark.ShatterAt == 0.0)
		{
			Mark.ShatterAt = Now;
		}
	}
	// 눈꽃 팔: 번쩍(밝기·선 빛을 올림) → BlinkFadeSeconds 동안 걷히며 사라진다
	for (const TWeakObjectPtr<UDecalComponent>& Weak : BlinkArms)
	{
		UDecalComponent* Arm = Weak.Get();
		UMaterialInstanceDynamic* Dynamic = Arm ? Cast<UMaterialInstanceDynamic>(Arm->GetDecalMaterial()) : nullptr;
		if (!Dynamic)
		{
			continue;
		}
		Dynamic->SetScalarParameterValue(TEXT("Brightness"), BlinkFlashBrightness);
		Dynamic->SetScalarParameterValue(TEXT("LineGlow"), BlinkFlashGlow);
		const TWeakObjectPtr<UMaterialInstanceDynamic> WeakDynamic = Dynamic;
		for (int32 Step = 1; Step <= BlinkFadeSteps; ++Step)
		{
			const float Left = 1.0f - static_cast<float>(Step) / BlinkFadeSteps;
			World->GetTimerManager().SetTimer(AddReleaseTimer(), FTimerDelegate::CreateWeakLambda(this, [Weak, WeakDynamic, Left]()
			{
				if (UMaterialInstanceDynamic* Fading = WeakDynamic.Get())
				{
					Fading->SetScalarParameterValue(TEXT("LineOpacity"), BlinkArmLine * Left);
					Fading->SetScalarParameterValue(TEXT("HaloOpacity"), BlinkArmHalo * Left);
				}
				if (Left <= 0.0f)
				{
					if (UDecalComponent* Done = Weak.Get())
					{
						Done->DestroyComponent();
					}
				}
			}), BlinkFadeSeconds * Step / BlinkFadeSteps, false);
		}
	}
	// 가운데 푸른 빛이 번쩍였다 가라앉는다(붙이지 않은 점광)
	UPointLightComponent* Light = NewObject<UPointLightComponent>(Character.Get());
	Light->SetMobility(EComponentMobility::Movable);
	Light->RegisterComponent();
	Light->SetWorldLocation(Center + FVector(0.0f, 0.0f, 80.0f));
	Light->SetIntensityUnits(ELightUnits::Candelas);
	Light->SetIntensity(BlinkLightCandelas);
	Light->SetLightColor(HasteLightColour);
	Light->SetAttenuationRadius(BlinkLightReach);
	Light->SetCastShadows(false);
	const TWeakObjectPtr<UPointLightComponent> WeakLight = Light;
	for (int32 Step = 1; Step <= BlinkFadeSteps; ++Step)
	{
		const float Left = 1.0f - static_cast<float>(Step) / BlinkFadeSteps;
		World->GetTimerManager().SetTimer(AddReleaseTimer(), FTimerDelegate::CreateWeakLambda(this, [WeakLight, Left]()
		{
			if (UPointLightComponent* Fading = WeakLight.Get())
			{
				Fading->SetIntensity(BlinkLightCandelas * Left * Left);
				if (Left <= 0.0f)
				{
					Fading->DestroyComponent();
				}
			}
		}), BlinkLightSeconds * Step / BlinkFadeSteps, false);
	}
	// 여섯 팔 자리에서 얼음 조각 · 가운데 큰 조각 · 고리 하나
	for (const FVector& Direction : BlinkArmDirections)
	{
		for (const float Side : {1.0f, -1.0f})
		{
			SpawnShatterShards(Center + Direction * Side * BlinkArmRadius * 0.6f, 50.0f, 4, 320.0f, 260.0f, 1.0f);
		}
	}
	SpawnShatterShards(Center, 120.0f, 14, 420.0f, 300.0f, 1.2f);
	UMaterialInterface* Ring = NovaRingRoughMaterial.LoadSynchronous();
	SpawnFrostNova(Center, BlinkArmRadius * 1.5f, 1, 0.22f, Ring ? Ring : NovaRingMaterial.LoadSynchronous());
	const int32 Hits = ApplyAreaDamage(Center, 220.0f, BlinkShatterDamage, TEXT("STUN"), 1.0f);
	BeginHitStop(Target.Get(), 0.08f);
	UE_LOG(LogTemp, Display, TEXT("AURORA_RDRAFT blink shatter arms=%d hits=%d"), BlinkArms.Num(), Hits);
	BlinkArms.Reset();
	BlinkArmDirections.Reset();
	RestoreBlinkCamera();
}

void UAuroraSkillComponent::LeaveBlinkAfterimage(bool bFirstSwing)
{
	USkeletalMeshComponent* Body = Character.IsValid() ? Character->GetMesh() : nullptr;
	UMaterialInterface* Ice = CloneIceMaterial.LoadSynchronous();
	UAnimSequence* Swing = bFirstSwing ? CrossFirstAnimation : CrossSecondAnimation;
	// 잔상 동작 시안(Aurora.FX.RSwing): 0 = 지금(가장 빠른 순간 BlinkAfterimageLead초 앞부터), 1~7 = 처음부터 한 번
	const int32 SwingDraft = CVarAuroraRSwing.GetValueOnGameThread();
	float Seconds = BlinkAfterimageSeconds;
	float From = FMath::Max(0.0f, (bFirstSwing ? FrostCrossFirstCut : FrostCrossSecondCut) - BlinkAfterimageLead);
	float Rate = 1.0f;
	if (SwingDraft >= 1 && SwingDraft <= static_cast<int32>(UE_ARRAY_COUNT(BlinkSwings)))
	{
		const FBlinkSwing& Pair = BlinkSwings[SwingDraft - 1];
		Swing = LoadBlinkSwing(bFirstSwing ? Pair.First : Pair.Second);
		From = 0.0f;
		Rate = BlinkSwingRate;
		Seconds = Swing ? FMath::Min(Swing->GetPlayLength() / BlinkSwingRate, BlinkSwingMaxSeconds) : BlinkAfterimageSeconds;
	}
	if (!Body || !Ice || !GetWorld())
	{
		return;
	}
	// 떠나는 자리에 남아 칼을 휘두르는 빛나는 얼음 분신(캐릭터 메시 사본, 혼자 재생 — F 분신과 같은 방식). 충돌·내비는 메시를
	// 끼우기 전에 끈다(SpawnTimedMesh와 같은 까닭).
	USkeletalMeshComponent* Ghost = NewObject<USkeletalMeshComponent>(Character.Get());
	Ghost->SetCollisionEnabled(ECollisionEnabled::NoCollision);
	Ghost->SetCanEverAffectNavigation(false);
	Ghost->SetSkeletalMesh(Body->GetSkeletalMeshAsset());
	Ghost->SetUsingAbsoluteLocation(true);
	Ghost->SetUsingAbsoluteRotation(true);
	Ghost->SetUsingAbsoluteScale(true);
	Ghost->SetWorldTransform(Body->GetComponentTransform());
	Ghost->RegisterComponent();
	UMaterialInstanceDynamic* Fading = UMaterialInstanceDynamic::Create(Ice, Ghost);
	for (int32 Slot = 0; Slot < Ghost->GetNumMaterials(); ++Slot)
	{
		Ghost->SetMaterial(Slot, Fading);
	}
	Ghost->SetAnimationMode(EAnimationMode::AnimationSingleNode);
	if (Swing)
	{
		Ghost->PlayAnimation(Swing, false);
		Ghost->SetPosition(From, false);
		Ghost->SetPlayRate(Rate);
	}
	UE_LOG(LogTemp, Display, TEXT("AURORA_RDRAFT afterimage swing=%d anim=%s seconds=%.2f"), SwingDraft, *GetNameSafe(Swing), Seconds);
	const TWeakObjectPtr<USkeletalMeshComponent> WeakGhost = Ghost;
	const TWeakObjectPtr<UMaterialInstanceDynamic> WeakFading = Fading;
	for (int32 Step = 1; Step <= BlinkFadeSteps; ++Step)
	{
		// 앞 BlinkAfterimageHold 몫은 또렷하게(1), 그 뒤 0까지
		const float Left = FMath::Min(1.0f, (1.0f - static_cast<float>(Step) / BlinkFadeSteps) / (1.0f - BlinkAfterimageHold));
		GetWorld()->GetTimerManager().SetTimer(AddReleaseTimer(), FTimerDelegate::CreateWeakLambda(this, [WeakGhost, WeakFading, Left]()
		{
			if (UMaterialInstanceDynamic* Material = WeakFading.Get())
			{
				Material->SetScalarParameterValue(TEXT("Fade"), Left);
			}
			if (Left <= 0.0f)
			{
				if (USkeletalMeshComponent* Done = WeakGhost.Get())
				{
					Done->DestroyComponent();
				}
			}
		}), Seconds * Step / BlinkFadeSteps, false);
	}
}

void UAuroraSkillComponent::RDraftTick()
{
	UWorld* World = GetWorld();
	if (!World || !Character.IsValid() || GlideStarted < 0.0)
	{
		if (World)
		{
			World->GetTimerManager().ClearTimer(RDraftTimer);
		}
		return;
	}
	// 시안 8: 떠난 자리에서 갈 자리로 처음이 빠르게(1 - (1 - t)²) 미끄러져 간다
	const float Alpha = FMath::Clamp(static_cast<float>(World->GetTimeSeconds() - GlideStarted) / BlinkGlideSeconds, 0.0f, 1.0f);
	Character->SetActorLocation(FMath::Lerp(GlideFrom, GlideTo, 1.0f - FMath::Square(1.0f - Alpha)), false, nullptr, ETeleportType::TeleportPhysics);
	if (Alpha >= 1.0f)
	{
		GlideStarted = -1.0;
		World->GetTimerManager().ClearTimer(RDraftTimer);
	}
}

void UAuroraSkillComponent::ShowBlinkArmor(bool bShow)
{
	if (UStaticMeshComponent* Shell = ArmorShell.Get())
	{
		Shell->SetVisibility(bShow);
	}
}

void UAuroraSkillComponent::RestoreBlinkCamera()
{
	// 처음 자리로 돌아온 때라 숨긴 보호막도 같이 되돌린다
	ShowBlinkArmor(true);
	if (USceneComponent* Boom = BlinkBoom.Get())
	{
		Boom->SetUsingAbsoluteLocation(false);
		Boom->SetRelativeLocation(BlinkBoomRelative);
	}
	BlinkBoom.Reset();
}

void UAuroraSkillComponent::EndRDraft()
{
	if (GetWorld())
	{
		GetWorld()->GetTimerManager().ClearTimer(RDraftTimer);
	}
	GlideStarted = -1.0;
	RestoreBlinkCamera();
	if (Character.IsValid() && Character->GetMesh() && !Character->GetMesh()->IsVisible())
	{
		Character->GetMesh()->SetVisibility(true, true);
	}
	for (const TWeakObjectPtr<UDecalComponent>& Arm : BlinkArms)
	{
		if (UDecalComponent* Decal = Arm.Get())
		{
			Decal->DestroyComponent();
		}
	}
	BlinkArms.Reset();
	BlinkArmDirections.Reset();
	BlinkTarget.Reset();
}