# 궁수 이펙트 색상 조사 — 2026-10-16

가져온 `ParagonSparrow` 팩 기준이다. 현재 외형은 **Rogue**, 스킬은 **기본 Sparrow FX**를 사용한다. 이번 조사는 읽기 전용이며 기본 색상·스킨·E 동작을 변경하지 않았다.

| 구분 | 현재 기본 FX 색상 | 팩에 있는 Rogue 전용 FX 색상 | 현재 참조 |
|---|---|---|---|
| 평타 | 금빛·주황·백색 | 붉은색·진홍색, 그림자 잔상과 밝은 섬광 | `Primary/FX/P_Sparrow_PrimaryAttack`, `P_Sparrow_Primary_Ballistic_HitPlayer`, `P_Sparrow_Primary_Ballistic_HitWorld`, `P_SparrowPrimaryMuzzleFlash` |
| Q | 금빛·백색 화살＋연보라·분홍 안개/잔점 | 붉은 화살·광원, 일부 밝은 금빛 모듈 잔존 | `RainOfArrows/FX/P_RainArrowsTarget`, `P_RainofArrows`, `P_RainofArrowsProj` |
| W | 보라·연보라 충전/띠＋금주황 발사·피격 | 붉은 충전·띠·피격과 그림자 잔상 | `DrawABead/FX/P_Sparrow_RMB`, `Ultimate/FX/P_Sparrow_UltHit`, 평타의 발사 섬광·월드 피격 |
| E | 현재 Relentless 패시브, 별도 시전 FX 없음 | 해당 패시브 전용 FX 항목 없음 | `CastEffect`·`ImpactEffect` 없음 |
| R | 금주황 버프·강화 화살·피격＋백색 섬광 | 붉은 버프·강화 화살·피격과 그림자 잔상 | `Ultimate/FX/P_SparrowBuff`, `P_Sparrow_UltArrow`, `P_Sparrow_UltHit`, `P_Sparrow_UltHitWorld` |

현재 참조 표의 경로 앞에는 `/Game/ParagonSparrow/FX/Particles/Sparrow/Abilities/`가 붙는다. Rogue 대응 자산은 `/Game/ParagonSparrow/FX/Particles/Sparrow/Skins/Rogue/`에 있다. 자산이 존재해도 현재 캐릭터가 그 자산을 사용한다는 뜻은 아니다. `P_ReleaseArrow`는 조사했지만 현재 W 코드의 발사 참조가 아니므로 위 참조 표에 포함하지 않았다.

외형 폴더는 **AutumnFire / FelineQueen / Monarch / Raven / Rogue / Tough / ZechinHuntress** 7종이다. 스킨 전용 Particle FX 폴더는 **Rogue 1개, 자산 17개**다. 다른 6종의 전용 FX 폴더는 현재 가져온 팩에 없다. 원작 게임의 모든 스킨 구성까지 뜻하지 않는다.

원본 색상 분포 예: 기본 Q `Falling=(25,20,5)`, `PurpleFallingMist=(2,0.1,2)`; 기본 W `RibbonTrail=(1,0.5,0.958333)`; Rogue Q `Falling=(25,0,0)`, Rogue W `Flare=(5,0,0)`, Rogue R `RibbonTrail=(10,0.5,0.5)`.

이 수치는 **HDR 입력 RGB**다. 머티리얼·텍스처·굴절·블룸·조명이 합성되므로 최종 화면 RGB나 색상 비율로 해석하지 않는다. `EmitterEditorColor`는 에디터 표시용 색이며 근거에서 제외했다. 기존 수련장 `dual-character-polish-20261016/regression-60-01/screenshots`의 Q 화살비·W 충전/발사·R 강화 공격 PNG에서도 기본 금빛/보라 조합을 확인했다.

검증 근거:

- 현재 참조: `Source/LearnTopDown/SparrowSkillComponent.cpp`의 생성자, `ExecuteAction`, `SpawnArrow`, `FireBasicAttack` 및 `Tools/CharacterPipeline/Profiles/sparrow.json`.
- 최신 원본 조회: `Saved/QA/CharacterPipeline/sparrow-palette-20261016/fresh-01/sparrow-native-inventory.json` — 기본 13개＋Rogue 17개, 총 30개 모두 존재 확인.
- Native inventory SHA-256: `d581050b3a8eb2476d54f3cf758fc1fb900f857e9da69744f1fe889dd4aec2ca`.
- `palette-inspection.json`: `passed=true`, `source_unchanged=true`; 전체 `ParagonSparrow` 원본 패키지 해시 전후 동일.
- `palette-summary.json`: 위 native 해시 일치 재확인, emitter별 LOD0 활성 상태·머티리얼·정확한 색상 분포 보관. 원본 패키지 저장 없음.
