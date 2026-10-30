#include "CharacterSkillHUD.h"

#include "CharacterSkillComponent.h"
#include "CountessSkillComponent.h"
#include "Engine/Canvas.h"
#include "Engine/Engine.h"
#include "GameFramework/PlayerController.h"
#include "ImageUtils.h"
#include "Misc/Paths.h"
#include "TopDownCombatCharacter.h"
#include "PlayerCombatComponent.h"

namespace
{
	// 16칸(Q W E R / 1 2 3 4 / A S D F / 5 6 7 8) + V(궁극기) + Space(이동기).
	constexpr int32 TotalHudSlots = 18;

	struct FHudTextureBank
	{
		UTexture2D* DockFrame = nullptr;
		UTexture2D* LifeLiquid = nullptr;
		UTexture2D* ManaLiquid = nullptr;
		UTexture2D* GlobeCavity = nullptr;
		UTexture2D* GlassSheen = nullptr;
		UTexture2D* SlotFrame = nullptr;
		UTexture2D* SlotActive = nullptr;
		UTexture2D* SkillIcons[TotalHudSlots] = { nullptr };
		bool bLoaded = false;

		void Load()
		{
			if (bLoaded) return;
			const FString BaseDir = FPaths::ProjectContentDir() / TEXT("TopDown/UI/Textures/");

			auto LoadTex = [](const FString& Path) -> UTexture2D*
			{
				UTexture2D* Tex = FImageUtils::ImportFileAsTexture2D(Path);
				if (Tex)
				{
					Tex->AddToRoot(); // Prevent GC sweep during gameplay
				}
				return Tex;
			};

			DockFrame = LoadTex(BaseDir / TEXT("T_Hud_Dock_Frame.png"));
			LifeLiquid = LoadTex(BaseDir / TEXT("T_Life_Liquid.png"));
			ManaLiquid = LoadTex(BaseDir / TEXT("T_Mana_Liquid.png"));
			GlobeCavity = LoadTex(BaseDir / TEXT("T_Globe_Cavity.png"));
			GlassSheen = LoadTex(BaseDir / TEXT("T_Glass_Sheen.png"));
			SlotFrame = LoadTex(BaseDir / TEXT("T_SkillSlot_Frame.png"));
			SlotActive = LoadTex(BaseDir / TEXT("T_SkillSlot_Active.png"));

			for (int32 i = 0; i < TotalHudSlots; ++i)
			{
				SkillIcons[i] = LoadTex(BaseDir / FString::Printf(TEXT("T_SkillIcon_%d.png"), i));
			}

			bLoaded = true;
		}
	};

	static FHudTextureBank GTextures;

	// Calm gameplay stats tracking (no idle bobbing/shaking; smooth interpolation only on stat change)
	struct FPlayerCombatStats
	{
		float MaxHP = 1000.0f;
		float TargetHP = 1000.0f;
		float DisplayedHP = 1000.0f;

		float MaxMP = 500.0f;
		float TargetMP = 500.0f;
		float DisplayedMP = 500.0f;

		int32 LastActiveSkill = 0;
		float LastTimeSeconds = 0.0f;
		float PreviousCooldowns[TotalHudSlots] = { 0.0f };

		void Update(const UCharacterSkillComponent* Skills, float TimeSeconds)
		{
			const float DeltaTime = LastTimeSeconds > 0.0f ? FMath::Clamp(TimeSeconds - LastTimeSeconds, 0.0f, 0.5f) : 0.016f;
			LastTimeSeconds = TimeSeconds;

			// Gentle passive Mana & HP recovery
			TargetMP = FMath::Clamp(TargetMP + 15.0f * DeltaTime, 0.0f, MaxMP);
			TargetHP = FMath::Clamp(TargetHP + 2.0f * DeltaTime, 0.0f, MaxHP);

			if (Skills)
			{
				const bool bPracticeMode = Skills->IgnoresCooldowns();
				if (bPracticeMode)
				{
					TargetMP = MaxMP;
				}

				const int32 ActiveSkill = Skills->GetActiveSkillNumber();
				if (ActiveSkill > 0 && ActiveSkill != LastActiveSkill)
				{
					const float ManaCosts[] = { 35.0f, 45.0f, 60.0f, 110.0f, 30.0f, 40.0f, 50.0f, 60.0f };
					const int32 CostIdx = FMath::Clamp(ActiveSkill - 1, 0, 7);
					if (!bPracticeMode)
					{
						TargetMP = FMath::Max(0.0f, TargetMP - ManaCosts[CostIdx]);
					}

					if (ActiveSkill == 4)
					{
						TargetHP = FMath::Min(MaxHP, TargetHP + 150.0f);
					}
				}
				LastActiveSkill = ActiveSkill;

				const int32 SkillCount = FMath::Min(Skills->GetSkillCount(), TotalHudSlots);
				for (int32 i = 0; i < SkillCount; ++i)
				{
					const float Cd = Skills->GetSlotCooldownRemaining(i);
					if (!bPracticeMode && Cd > 0.0f && PreviousCooldowns[i] <= 0.0f && ActiveSkill == 0)
					{
						const float ManaCosts[] = { 35.0f, 45.0f, 60.0f, 110.0f };
						TargetMP = FMath::Max(0.0f, TargetMP - ManaCosts[FMath::Clamp(i, 0, 3)]);
					}
					PreviousCooldowns[i] = Cd;
				}
			}

			// Smooth, calm interpolation without any sine-wave bobbing
			DisplayedHP = FMath::FInterpTo(DisplayedHP, TargetHP, DeltaTime, 6.0f);
			DisplayedMP = FMath::FInterpTo(DisplayedMP, TargetMP, DeltaTime, 6.0f);
		}
	};

	static FPlayerCombatStats GCombatStats;
}

void ACharacterSkillHUD::DrawHUD()
{
	Super::DrawHUD();
	const ATopDownCombatCharacter* Character = PlayerOwner ? Cast<ATopDownCombatCharacter>(PlayerOwner->GetPawn()) : nullptr;
	const UCharacterSkillComponent* Skills = Character ? Character->GetSkills() : nullptr;
	if (!Canvas || !Skills || !Skills->IsEnabled())
	{
		return;
	}

	GTextures.Load();

	const double WorldTime = GetWorld() ? GetWorld()->GetTimeSeconds() : 0.0;
	const float TimeSeconds = static_cast<float>(WorldTime);
	GCombatStats.Update(Skills, TimeSeconds);
	const UPlayerCombatComponent* Combat = PlayerOwner->FindComponentByClass<UPlayerCombatComponent>();
	const bool bDamageFeedback = Combat && Combat->UsesNonInterruptingDamageFeedback();
	const float ActualHP = bDamageFeedback ? FMath::Clamp(Combat->GetHealth() / Combat->GetMaxHealth(), 0.0f, 1.0f) : 1.0f;
	const float TrailHP = bDamageFeedback ? FMath::Clamp(Combat->GetDamageTrailHealth() / Combat->GetMaxHealth(), ActualHP, 1.0f) : ActualHP;
	// A quiet edge gradient warns only at low health; ordinary hits do not
	// flash the screen, shake the camera, or pause the player's animation.
	if (bDamageFeedback && Combat->IsAlive() && ActualHP < 0.30f)
	{
		const float Danger = FMath::Clamp((0.30f - ActualHP) / 0.20f, 0.0f, 1.0f);
		const float Pulse = 0.85f + 0.15f * FMath::Sin(TimeSeconds * 4.0f);
		const float Depth = Canvas->SizeY * 0.065f;
		constexpr int32 Steps = 24;
		const float Band = Depth / Steps;
		for (int32 Index = 0; Index < Steps; ++Index)
		{
			const float Inset = Index * Band;
			const float Falloff = FMath::Square(1.0f - (Index + 0.5f) / Steps);
			const FLinearColor Color(0.45f, 0.012f, 0.018f, 0.30f * Danger * Pulse * Falloff);
			DrawRect(Color, Inset, Inset, Canvas->SizeX - 2.0f * Inset, Band);
			DrawRect(Color, Inset, Canvas->SizeY - Inset - Band, Canvas->SizeX - 2.0f * Inset, Band);
			DrawRect(Color, Inset, Inset + Band, Band, Canvas->SizeY - 2.0f * (Inset + Band));
			DrawRect(Color, Canvas->SizeX - Inset - Band, Inset + Band, Band, Canvas->SizeY - 2.0f * (Inset + Band));
		}
	}

	// =========================================================================
	// 2-A FINAL HUD LAYOUT METRICS (Reference Canvas: 1376 x 304)
	// - Left & Right Gem-Studded Orbs (Calm Liquid, Zero Idle Wave Animation)
	// - Left 4x2 (Q,W,E,R / 1,2,3,4) & Right 4x2 (A,S,D,F / 5,6,7,8) Skill Banks
	// - Center Golden Winged Flame Shield & 3D Horn/Amber Crown
	// - Full-Bottom Diablo 3 Style 10-Segment Golden EXP Bar
	// =========================================================================
	constexpr float RefW = 1376.0f;
	constexpr float RefH = 304.0f;
	// Scale HUD to a sleek top-down ARPG proportion (~14.5% of screen height / ~38% of screen width)
	const float ScaleByH = (Canvas->SizeY * 0.148f) / RefH;
	const float ScaleByW = (Canvas->SizeX * 0.385f) / RefW;
	const float Scale = FMath::Clamp(FMath::Min(ScaleByH, ScaleByW), 0.25f, 0.62f);

	const float DockW = RefW * Scale;
	const float DockH = RefH * Scale;
	const float DockX = (Canvas->SizeX - DockW) * 0.5f;
	const float DockY = Canvas->SizeY - DockH;

	const float HpFraction = bDamageFeedback ? ActualHP : FMath::Clamp(GCombatStats.DisplayedHP / GCombatStats.MaxHP, 0.0f, 1.0f);
	const float MpFraction = FMath::Clamp(GCombatStats.DisplayedMP / GCombatStats.MaxMP, 0.0f, 1.0f);

	// Helper lambda to draw a calm, static glass orb cavity + vertical liquid fill + static glass sheen
	auto DrawCalmOrbInterior = [&](float RefCenterX, float RefCenterY, float RefRadius, UTexture2D* LiquidTex, float Fraction, const FLinearColor& MeniscusColor, float DamageTrail = 0.0f)
	{
		const float OrbDiameter = (RefRadius * 2.0f) * Scale;
		const float DrawX = DockX + (RefCenterX - RefRadius) * Scale;
		const float DrawY = DockY + (RefCenterY - RefRadius) * Scale;

		// 1. Dark glass cavity backplate
		if (GTextures.GlobeCavity)
		{
			DrawTexture(GTextures.GlobeCavity, DrawX, DrawY, OrbDiameter, OrbDiameter,
				0.0f, 0.0f, 1.0f, 1.0f, FLinearColor::White, BLEND_Translucent);
		}

		// Retain just the lost slice briefly so damage is readable without
		// delaying the actual health level or changing the original orb art.
		if (LiquidTex && DamageTrail > Fraction + 0.001f)
		{
			const float Slice = DamageTrail - Fraction;
			DrawTexture(LiquidTex, DrawX, DrawY + OrbDiameter * (1.0f - DamageTrail), OrbDiameter, OrbDiameter * Slice,
				0.0f, 1.0f - DamageTrail, 1.0f, Slice, FLinearColor(1.0f, 0.65f, 0.45f, 0.55f), BLEND_Translucent);
		}

		// 2. Calm vertical liquid fill (NO sine wave bobbing or stretching)
		if (LiquidTex && Fraction > 0.002f)
		{
			const float LiquidH = OrbDiameter * Fraction;
			const float LiquidY = DrawY + (OrbDiameter - LiquidH);

			DrawTexture(LiquidTex,
				DrawX, LiquidY, OrbDiameter, LiquidH,
				0.0f, 1.0f - Fraction, 1.0f, Fraction,
				FLinearColor::White, BLEND_Translucent);

			// Subtle horizontal meniscus line when partially filled
			if (Fraction > 0.03f && Fraction < 0.97f)
			{
				const float RelY = (0.5f - Fraction) * 2.0f; // -1 at top, +1 at bottom
				const float ChordRatio = FMath::Sqrt(FMath::Max(0.0f, 1.0f - RelY * RelY));
				const float ChordW = (OrbDiameter - 6.0f * Scale) * ChordRatio;
				const float ChordX = DockX + RefCenterX * Scale - ChordW * 0.5f;
				DrawRect(MeniscusColor, ChordX, LiquidY, ChordW, FMath::Max(1.0f, 1.5f * Scale));
			}
		}

		// 3. Static glass specular highlight
		if (GTextures.GlassSheen)
		{
			DrawTexture(GTextures.GlassSheen, DrawX, DrawY, OrbDiameter, OrbDiameter,
				0.0f, 0.0f, 1.0f, 1.0f, FLinearColor(1.0f, 1.0f, 1.0f, 0.75f), BLEND_Translucent);
		}
	};

	// =========================================================================
	// 1. LEFT & RIGHT ORB INTERIORS (Drawn behind T_Hud_Dock_Frame's bezel)
	// =========================================================================
	DrawCalmOrbInterior(127.5f, 184.0f, 84.0f, GTextures.LifeLiquid, HpFraction, FLinearColor(1.0f, 0.55f, 0.55f, 0.55f), bDamageFeedback ? TrailHP : HpFraction);
	DrawCalmOrbInterior(1248.5f, 184.0f, 84.0f, GTextures.ManaLiquid, MpFraction, FLinearColor(0.55f, 0.82f, 1.0f, 0.55f));

	// =========================================================================
	// 2. UNIFIED 2-A SCULPTED DOCK, GEM-STUDDED ORB BEZELS & GOLDEN SHIELD
	// =========================================================================
	if (GTextures.DockFrame)
	{
		DrawTexture(GTextures.DockFrame, DockX, DockY, DockW, DockH,
			0.0f, 0.0f, 1.0f, 1.0f, FLinearColor::White, BLEND_Translucent);
	}

	// =========================================================================
	// 3. LEFT 4x2 (Q,W,E,R / 1,2,3,4) & RIGHT 4x2 (A,S,D,F / 5,6,7,8) SKILL BANKS
	// =========================================================================
	const TCHAR* SlotKeys[TotalHudSlots] = {
		TEXT("Q"), TEXT("W"), TEXT("E"), TEXT("R"),
		TEXT("1"), TEXT("2"), TEXT("3"), TEXT("4"),
		TEXT("A"), TEXT("S"), TEXT("D"), TEXT("F"),
		TEXT("5"), TEXT("6"), TEXT("7"), TEXT("8"),
		TEXT("V"), TEXT("SPC")
	};
	constexpr float RefSlotSize = 72.0f;
	constexpr float RefSlotGapX = 6.0f;
	constexpr float RefSlotStepY = 82.0f;
	constexpr float RefSlotTopY = 116.0f;
	constexpr float RefBankW = 4.0f * RefSlotSize + 3.0f * RefSlotGapX; // 306.0f
	const float RefBankStartX[2] = { 294.0f, RefW - 294.0f - RefBankW };

	const int32 SupportedSkills = Skills->GetSkillCount();
	const bool bLettersLeft = Skills->PlacesLetterKeysOnLeftHud();
	const float SlotSize = RefSlotSize * Scale;
	const float Inset = 5.0f * Scale;

	for (int32 BankIdx = 0; BankIdx < 2; ++BankIdx)
	{
		for (int32 RowIdx = 0; RowIdx < 2; ++RowIdx)
		{
			for (int32 ColIdx = 0; ColIdx < 4; ++ColIdx)
			{
				int32 SlotIndex = BankIdx * 8 + RowIdx * 4 + ColIdx;
				// 글자 키만 쓰는 캐릭터는 왼쪽 아랫줄(1~4)과 오른쪽 윗줄(A~F)을 맞바꿔 스킬을 왼쪽 묶음에 모은다.
				if (bLettersLeft && BankIdx + RowIdx == 1)
				{
					SlotIndex = (BankIdx == 0 ? 8 : 4) + ColIdx;
				}
				// 그 경우 오른쪽 윗줄(숫자 1~4)이 비므로 앞 두 칸에 V(궁극기)·Space(이동기)를 그린다.
				if (bLettersLeft && BankIdx == 1 && RowIdx == 0 && ColIdx < 2)
				{
					SlotIndex = 16 + ColIdx;
				}
				const float RefX = RefBankStartX[BankIdx] + ColIdx * (RefSlotSize + RefSlotGapX);
				const float RefY = RefSlotTopY + RowIdx * RefSlotStepY;

				const float SlotX = DockX + RefX * Scale;
				const float SlotY = DockY + RefY * Scale;

				// 칸 번호가 띄엄띄엄인 캐릭터(예: Gideon Q W E R + A)는 이름 없는 칸을 빈 칸으로 그린다.
				const bool bLinkedSkill = (SlotIndex < SupportedSkills) && !Skills->GetSkillDisplayName(SlotIndex).IsEmpty();
				const float CooldownRem = bLinkedSkill ? Skills->GetSlotCooldownRemaining(SlotIndex) : 0.0f;
				const float RecastRem = bLinkedSkill ? Skills->GetSlotRecastRemaining(SlotIndex) : 0.0f;
				const bool bReturnActive = RecastRem > 0.0f;
				const float Remaining = bReturnActive ? RecastRem : CooldownRem;
				const bool bPassive = bLinkedSkill ? Skills->IsSkillPassive(SlotIndex) : false;
				const bool bReady = !bPassive && (bReturnActive || Remaining <= 0.0f);
				const bool bActiveCast = bLinkedSkill && (Skills->GetActiveSkillNumber() == (SlotIndex + 1));

				// 3-1. Dark Slot Backplate
				DrawRect(FLinearColor(0.04f, 0.03f, 0.03f, 0.98f), SlotX + Inset * 0.5f, SlotY + Inset * 0.5f, SlotSize - Inset, SlotSize - Inset);

				// If no skill is assigned to this slot, keep it as an empty socket without fake icons/hotkeys
				if (!bLinkedSkill)
				{
					if (GTextures.SlotFrame)
					{
						DrawTexture(GTextures.SlotFrame, SlotX, SlotY, SlotSize, SlotSize,
							0.0f, 0.0f, 1.0f, 1.0f, FLinearColor(0.32f, 0.30f, 0.28f, 0.40f), BLEND_Translucent);
					}
					continue;
				}

				// 3-2. Skill Icon Texture (Only for actual skills)
				if (SlotIndex < TotalHudSlots && GTextures.SkillIcons[SlotIndex])
				{
					const FLinearColor IconTint = (!bReady && !bPassive)
						? FLinearColor(0.42f, 0.42f, 0.42f, 0.78f)
						: FLinearColor::White;
					DrawTexture(GTextures.SkillIcons[SlotIndex],
						SlotX + Inset, SlotY + Inset, SlotSize - Inset * 2.0f, SlotSize - Inset * 2.0f,
						0.0f, 0.0f, 1.0f, 1.0f, IconTint, BLEND_Translucent);
				}

				// 3-3. Double-Beveled Antique Gold Slot Frame
				if (GTextures.SlotFrame)
				{
					DrawTexture(GTextures.SlotFrame, SlotX, SlotY, SlotSize, SlotSize,
						0.0f, 0.0f, 1.0f, 1.0f, FLinearColor::White, BLEND_Translucent);
				}

				// 3-4. Active Cast / Recast Highlight
				if ((bActiveCast || bReturnActive) && GTextures.SlotActive)
				{
					const FLinearColor GlowTint = bReturnActive
						? FLinearColor(0.85f, 0.40f, 1.0f, 0.80f)
						: FLinearColor(1.0f, 0.85f, 0.32f, 0.85f);
					DrawTexture(GTextures.SlotActive,
						SlotX - 2.0f * Scale, SlotY - 2.0f * Scale, SlotSize + 4.0f * Scale, SlotSize + 4.0f * Scale,
						0.0f, 0.0f, 1.0f, 1.0f, GlowTint, BLEND_Translucent);
				}

				// 3-5. Cooldown Shroud & Countdown Timer
				if (Remaining > 0.0f)
				{
					DrawRect(FLinearColor(0.0f, 0.0f, 0.0f, 0.72f),
						SlotX + Inset, SlotY + Inset, SlotSize - Inset * 2.0f, SlotSize - Inset * 2.0f);

					const FString CdText = bReturnActive
						? FString::Printf(TEXT("%.1f"), Remaining)
						: (Remaining >= 10.0f ? FString::Printf(TEXT("%.0f"), Remaining) : FString::Printf(TEXT("%.1f"), Remaining));

					float Cw = 0.0f, Ch = 0.0f;
					const float FontScale = FMath::Max(0.85f, 1.05f * Scale);
					GetTextSize(CdText, Cw, Ch, GEngine->GetSmallFont(), FontScale);
					const FLinearColor CdColor = bReturnActive ? FLinearColor(0.95f, 0.60f, 1.0f) : FLinearColor(1.0f, 0.90f, 0.42f);
					DrawText(CdText, CdColor,
						SlotX + (SlotSize - Cw) * 0.5f, SlotY + (SlotSize - Ch) * 0.5f - 2.0f * Scale,
						GEngine->GetSmallFont(), FontScale);
				}

				// 3-6. Bottom-Center Golden Hotkey Badge (2-A Style)
				// 글자가 긴 키(SPC)도 테두리 안에 들어가게 폭을 글자에 맞춰 넓힌다.
				float Kw = 0.0f, Kh = 0.0f;
				const float KeyScale = FMath::Max(0.75f, 0.88f * Scale);
				GetTextSize(SlotKeys[SlotIndex], Kw, Kh, GEngine->GetSmallFont(), KeyScale);
				const float BadgeW = FMath::Max(24.0f * Scale, Kw + 8.0f * Scale);
				const float BadgeH = 15.0f * Scale;
				const float BadgeX = SlotX + (SlotSize - BadgeW) * 0.5f;
				const float BadgeY = SlotY + SlotSize - 6.0f * Scale;

				DrawRect(FLinearColor(0.08f, 0.07f, 0.05f, 0.96f), BadgeX, BadgeY, BadgeW, BadgeH);
				DrawRect(FLinearColor(0.72f, 0.59f, 0.34f, 0.92f), BadgeX, BadgeY, BadgeW, 1.0f);
				DrawRect(FLinearColor(0.72f, 0.59f, 0.34f, 0.92f), BadgeX, BadgeY + BadgeH - 1.0f, BadgeW, 1.0f);
				DrawRect(FLinearColor(0.72f, 0.59f, 0.34f, 0.92f), BadgeX, BadgeY, 1.0f, BadgeH);
				DrawRect(FLinearColor(0.72f, 0.59f, 0.34f, 0.92f), BadgeX + BadgeW - 1.0f, BadgeY, 1.0f, BadgeH);

				DrawText(SlotKeys[SlotIndex],
					bReturnActive ? FLinearColor(0.92f, 0.65f, 1.0f) : FLinearColor(0.98f, 0.91f, 0.72f),
					BadgeX + (BadgeW - Kw) * 0.5f, BadgeY + (BadgeH - Kh) * 0.5f,
					GEngine->GetSmallFont(), KeyScale);
			}
		}
	}

	// =========================================================================
	// 4. DIABLO 3 STYLE 10-SEGMENT BOTTOM GOLDEN EXP BAR (Static, No Shimmer)
	// =========================================================================
	{
		const float ExpTopY = DockY + 286.0f * Scale;
		const float ExpBarH = 18.0f * Scale;
		const float ExpPad = 4.0f * Scale;
		constexpr float ExpFraction = 0.68f;
		const float FillW = (DockW - ExpPad * 2.0f) * ExpFraction;
		const float InnerH = FMath::Max(2.0f, ExpBarH - 5.0f * Scale);
		const float InnerY = ExpTopY + 3.0f * Scale;

		// Golden gradient fill (upper bright amber-gold, lower warm antique gold)
		DrawRect(FLinearColor(0.92f, 0.74f, 0.24f, 1.0f), DockX + ExpPad, InnerY, FillW, InnerH * 0.55f);
		DrawRect(FLinearColor(0.72f, 0.52f, 0.12f, 1.0f), DockX + ExpPad, InnerY + InnerH * 0.55f, FillW, InnerH * 0.45f);
		// Subtle static tip marker at the current EXP frontier
		DrawRect(FLinearColor(1.0f, 0.96f, 0.76f, 0.95f), DockX + ExpPad + FillW - 2.0f * Scale, InnerY, 2.0f * Scale, InnerH);

		// 10 Equal Segment Tick Dividers
		for (int32 Seg = 1; Seg < 10; ++Seg)
		{
			const float TickX = DockX + DockW * (static_cast<float>(Seg) / 10.0f);
			DrawRect(FLinearColor(0.04f, 0.03f, 0.03f, 0.90f), TickX - 1.0f, ExpTopY + 2.0f * Scale, 1.0f, ExpBarH - 4.0f * Scale);
			DrawRect(FLinearColor(0.68f, 0.56f, 0.33f, 0.95f), TickX, ExpTopY + 2.0f * Scale, 1.0f, ExpBarH - 4.0f * Scale);
		}
	}

	// Practice Mode & Input Feedback Banners
	if (Skills->IgnoresCooldowns())
	{
		const FString Practice = TEXT("PRACTICE MODE: NO COST / NO COOLDOWNS");
		float Tw = 0.0f, Th = 0.0f;
		GetTextSize(Practice, Tw, Th, GEngine->GetSmallFont(), 0.90f);
		DrawText(Practice, FLinearColor(0.60f, 0.95f, 0.70f, 0.90f),
			(Canvas->SizeX - Tw) * 0.5f, DockY + 78.0f * Scale, GEngine->GetSmallFont(), 0.90f);
	}

	const FString Feedback = Skills->GetInputFeedback();
	if (!Feedback.IsEmpty())
	{
		float Fw = 0.0f, Fh = 0.0f;
		GetTextSize(Feedback, Fw, Fh, GEngine->GetSmallFont(), 1.0f);
		DrawText(Feedback, FLinearColor(1.0f, 0.42f, 0.42f, 0.95f),
			(Canvas->SizeX - Fw) * 0.5f, DockY + 58.0f * Scale, GEngine->GetSmallFont(), 1.0f);
	}
}
