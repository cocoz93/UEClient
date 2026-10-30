# LearnTopDown 세션 인계 — 2026-10-21

사용자가 새 세션을 시작하기 전에 지금까지의 기억을 별도로 저장해 달라고 요청하여 작성했다. 이 문서는 세션 상태와 결정 사항이며, 세부 수치·도구 노하우는 [SkillPolishKnowhow.md](SkillPolishKnowhow.md)를 정본으로 삼는다. 과거 대화를 전부 다시 탐색하지 말고 여기에서 필요한 근거로 이동한다.

> **최신 상태:** 10-22 후속 요청은 **§22**다. 궁수 후딜 중 이동 클릭 유실을 수정해30/60fps 통과했고, Q/W/R 발사 보강·A직전 외형 복원·S불꽃 날개·D이동 대형을 적용했다. E3안/A3안/새 이동 애니메이션4개는 미채택 비교용이다. 최신 실제 영상17개는 `Saved/QA/CharacterPipeline/sparrow-finish-20261022/preview.html`, 최종 실행은 `Play-CurrentSkills.cmd` → 숫자2다. 기존 열린 Development에디터 DLL은 교체하지 않았다.

## 1. 새 담당이 먼저 알아야 할 상태

- 프로젝트: `C:/Users/USER/Desktop/MyGit/UEClient/LearnTopDown`, UE 5.8. git 저장소 밖이다(2026-10-30 MMO_Zone 저장소에서 옮김).
- 기본 필드: `/Game/TopDown/TrainingRoom/Maps/Lvl_DarkTrainingRoom`. 숫자 **1 암살자(Countess), 2 궁수(Sparrow), 3 Gideon, 4 Aurora**. 오래된 F1/F2 및 기본 TopDown 필드 기록으로 되돌리지 않는다.
- 최근 완료: 암살자 E **A/D 시안 보강**, 이어서 스킬 노하우 기록 점검·취합. 이번 인계 작성에서는 게임 코드·에셋·설정 변경이나 새 빌드·PIE를 하지 않았다.
- **A/D 시안은 기본 E에 아직 설치하지 않았다.** 현재 E의 본체·분신 협공은 유지되며, 설치된 FX는 `M_CountessETargetCut`이다. 사용자는 그 직선 참격 외형에 불만을 표시하여 제로베이스 시안을 요청했다. 구현되어 있다는 사실을 사용자 채택으로 해석하지 않는다.
- 다음 개발 작업은 아직 새로 지시되지 않았다. 사용자가 새 세션에서 우선순위를 정하면 이어간다. A/D 선택·실제 적용은 미결이다.
- 사용자 말로는 다른 Claude 작업에서 3번 캐릭터를 작업 중이었다. 현재 완료 여부·그 담당의 최신 diff/빌드/검사 상태는 이 인계에서 확인하지 않았다. 공유 파일을 수정하기 전에 최신 결과를 인계받는다.

## 2. 사용자 취향과 승인 범위

- 한국어로 결론부터 짧게 말한다. 소소해서 쿼터뷰에서 보이지 않는 수정과 반복적인 전체 검증을 싫어한다. 실제 플레이 시야에서 차이를 판별한다.
- 기존 캐릭터의 **색 + 텍스처 결 + 대비 + 잔상 + 소멸**을 함께 유지한다. 단색 면을 크게 키우거나 흰 코어를 과하게 번쩍이는 방식은 여러 번 반려됐다.
- 길이/두께, 반경/밀도/불투명도, 준비/접근/타격/회복을 따로 다룬다. 길이를 줄이면서 두꺼워지게 만들거나, 안개를 덜 짙게 해 달라는 요청에 반경을 줄이지 않는다.
- 암살자 Q의 큰 반월·모자 같은 곡면, 긴 잠자리 같은 일직선, 넓고 쨍한 단색은 반려 이력이다. E의 넓고 흐물거리는 칼 궤적과 과한 적백색 번쩍임도 반려됐다. 실패안을 기본값으로 되살리지 않는다.
- 암살자 E에서 **본체와 분신의 엇갈린 연격**, **대상 반대편에서 본체를 마주 보는 분신**, **종료 후 그림자 침식** 방향은 승인됐다. FX 최종 조형은 미결이다.
- 궁수 기본 공격은 활을 든 채 연결하고, R은 기울인 발사 자세를 연사 사이에도 유지하는 방향이다. W는 수평 방향으로 활 앞에 놓이고, 가까운 큰 원에서 먼 작은 원으로 이어지는 구성이 채택된 이력이 있다.
- 궁수 후드 추가 작업은 보류했다. 그러나 코드 기본값이 IvoryHood=1인 충돌이 있어 §6에 별도로 남겼다. 임의로 외형을 추가 변경하지 않는다.
- 사용자가 이미 승인한 계획·무인루프 범위에서는 세부 조정마다 다시 승인받지 않는다. 복잡한 새 로직은 적용되는 AGENTS.md의 계획 규칙을 지키되 이미 받은 승인을 반복 요청하지 않는다.
- “가능한지 대답만”, “후보만”, “시안”과 실제 설치 요청을 구분한다. 실제로 보지 않은 동작을 검증 완료라고 말하지 않는다.

## 3. 마지막 대화에서 한 말과 하지 않은 일

- 사용자는 매번 컨펌하지 않고 기존 Claude/Codex 작업을 바탕으로 여러 스킬을 자율 제작할 수 있는지 질문했다. 가능하며, 묶음 범위를 한 번 정해 설계→구현→수련장 확인→수정 후 비교 결과를 제시하는 방식을 설명했다.
- 캐릭터당 2~3개로 시작하는 방안과 “암살자·궁수 각각 3개, 기존 스킬 보존”이라는 **예시 요청문**을 제시했을 뿐이다. **신규 6개 제작은 승인되거나 착수된 일이 아니다.** 자동화·새 세션·서브에이전트 실행도 이 질문으로 승인된 것으로 취급하지 않는다.
- 협업 권고는 한 메인 세션 + 캐릭터별 독립 작업 담당이다. 공통 소스·맵·프로필·빌드·에셋 저장·GPU 에디터는 통합 담당이 조율한다. Claude의 3번 작업 완료 후 인계받고 다음 묶음을 진행하는 편을 권했다. 이는 현재 담당이 실제 실행 중이라는 뜻이 아니다.
- 모델 권고는 일반 구현 Sol High, 명확한 국소 값 조정 Medium, 복잡한 상태·타이머·연결 XHigh, 어려운 교차 시스템 원인 분석 Astra High/XHigh였다. 추천만 했으며 설정을 변경하지 않았다. 다음 세션의 실제 모델 가용성은 별도로 확인한다.

## 4. 최신 비교 시안과 재현 근거

- [E A/D 비교 HTML](../../Saved/QA/CharacterPipeline/countess-E-AD-refined-20261021/E-AD-preview.html)
- 기존 주소: `http://127.0.0.1:55811/countess-E-AD-refined-20261021/E-AD-preview.html`
- [결과 JSON](../../Saved/QA/CharacterPipeline/countess-E-AD-refined-20261021/result.json): 저장된 결과는 `passed=true`, `installed_skill_changed=false`, `native_build_performed=false`. 이 인계 작성 시 파일 존재와 값을 재확인했다. 현재 소스 전체가 과거 검사 당시와 동일함을 새로 검증한 것은 아니다.
- A 최종 프레임 근거: [field-a-final/e-concepts.json](../../Saved/QA/CharacterPipeline/countess-E-AD-refined-20261021/field-a-final/e-concepts.json). D 근거: [field/e-concepts.json](../../Saved/QA/CharacterPipeline/countess-E-AD-refined-20261021/field/e-concepts.json). A는 한 번 더 보강했으므로 `field`의 오래된 A를 최종본으로 사용하지 않는다.
- 원본 실제 PIE 캡처 700×330, 시안별 36프레임 표본. 연속 영상이나 고해상도 최종 품질 검증과 구별한다. 화면에서 6타·총 피해 45·분신·회복을 확인한 시안 작업 결과이며, 최종 미적 승인은 대기 중이다.
- A: 짧은 검붉은 절개, 안정된 외곽 + 내부 원본 노이즈 결, 작은 순간 강조. D: 대상에 누적되는 상처, 새 상처만 잠시 강조, 마지막에 제자리 침식.
- 생성 도구 [countess_e_concepts.py](countess_e_concepts.py). `COUNTESS_E_CONCEPT_REFINED=1`, `COUNTESS_E_CONCEPT_COMPARE=1`, `COUNTESS_E_CONCEPT_STYLES`로 범위 선택. 전용 재질 `FXConcepts/M_EConceptsAD_Refined_20261021`이며 원본 시안 재질과 운영 E는 보존했다.
- localhost 서버의 생존은 세션마다 확인한다. 필요하면 QA 루트 `Saved/QA/CharacterPipeline`에서 기존 HTTP 서버 방식을 재사용한다. 포트·PID가 과거에 존재했다는 이유로 현재 사용 가능하다고 단정하지 않는다. 미확정 시안과 열린 페이지 의존 파일을 자동 삭제하지 않는다.

## 5. 현재 구현 요약 — 상세값은 노하우 §8

아래는 10-21의 소스 대조 결과를 요약한 것이다. 이번 저장 때 맵, Q/W/E 기본값, 평타 설정, 후드, 모듈 manifest와 시안 파일을 좁게 재확인했으며 새 실행 검증은 하지 않았다. 다른 작업자가 수정한 내용이 있으면 실제 파일을 우선한다.

| 대상 | 이어갈 기준 |
|---|---|
| 공통 | 암살자·궁수 좌클릭 홀드 연속 평타. 연습용 `IgnoreCooldowns=1`; 정의의 쿨타임을 삭제한 것은 아님. 사용자는 테스트 중 노코스트·쿨타임 없는 사용을 원했다. |
| 암살자 Q | Presentation 3, Tone 1, LengthScale 0.52; Wispy 우선. 짧고 얇은 검붉은 바깥 베기. |
| 암살자 W | Presentation 3, Preview 0, PlayRate 1.95, `P_CountessW_VeilRing`. 피해 40/반경 240cm. 밀도·내부 알파와 반경을 구별. |
| 암살자 E | 수련장 EFlurry=1. 근접 대상에 본체 3 + 반대편 분신 3, 총 6타/45. 간격 약 0.1467초, 분신 약 0.45초 침식. 현 FX의 사용자 만족도는 낮고 A/D 선택 대기. |
| 암살자 R | 요청대로 최초 `Ability_Ultimate`, 0초부터 1배속. 준비 0.95 + 접근 0.5초, 타격 1.8/복귀 2.25초. 과거 가속 실험을 재적용하지 않음. |
| 궁수 평타 | Natural=1, HeldAim=1, Attack.Speed=1.2. 공속/발사 시점과 포즈 연결은 별개. |
| 궁수 Q | 4초/300cm/8회 피해 펄스, 시각 밀도 1.8배, 범위원 끝 0.4초 페이드. |
| 궁수 W | 준비 0.5초/발사 0.62초. 수평 활 앞 원 3개, 가까운 큰 원→먼 작은 원, 원 크기 0.5배를 포함한 구현. |
| 궁수 E | 준비 0.12초, 6발/0.16초 간격, 활 앞 원 하나. 기존 누적 피해 패시브 별도 유지. |
| 궁수 R | 10초, 중앙 및 ±12/±24도 5발 부채꼴. 몸 주변 큰 폭발은 빼고 전방 텍스처 광선 구성. |
| 궁수 망토 | 몸 PhysicsAsset 충돌원 + 이동 바람 보간. 폭주/관통/뻣뻣함은 각각 진단하며 천 시뮬레이션 비활성화를 해결로 포장하지 않음. |

## 6. 미해결·재확인 사항

1. **E A/D 최종 선택과 설치**: 아직 미결. 시안을 운영본으로 승격하거나 기존 E를 완성이라고 보고하지 않는다.
2. **궁수 후드**: 보류 의사와 달리 현재 `Sparrow.Appearance.IvoryHood=1`, `BeginPlay` 재질 교체 경로가 존재한다. 후드 작업 재개 시 실제 재질과 원하는 기준을 맞춘다. 이번 인계에서 변경하지 않았다.
3. **암살자 LevelStart 누락 참조**: 이전 10-21 로그 점검에서 Shinbi/Mudang `Animations/LevelStart`, `P_Mudang_LevelStart_Heart` 의존성 누락을 관측했다. 원인·플레이 영향 미확인. 무해하다고 단정하거나 Q/E 문제로 연결하지 않는다.
4. **3/4번 최신 상태**: 외부 기록 `C:/Users/USER/Desktop/MyGit/MyDocs/claude-plans/gideon-skills-progress.md`, `aurora-skills-progress.md`와 실제 소스의 최신 변경을 담당 인계와 대조한다. 기존 문서 취합이 그 작업의 최종 검증을 대신하지 않는다.
5. `presentation_contract`의 원작 행동 검증은 `unverified`인 기록이다. 기능 통과와 사용자 선택을 원작 게임 충실도 인증으로 바꾸지 않는다.
6. 오래된 README의 빠른 R, SparrowFXPalette의 패시브 E, 초기 망토 바람식, Q의 Muted 최종본 설명은 현재 구현과 다를 수 있다. [노하우 §12](SkillPolishKnowhow.md#12-근거-파일과-남겨-둔-확인-사항)의 차이 목록을 따른다.

## 7. 다음 작업의 운영 규칙

- [프로젝트 AGENTS.md](../../AGENTS.md) 및 [ParallelCharacterWork.md](ParallelCharacterWork.md)를 따른다. 명시된 범위 밖의 새 기능을 자동 추가하지 않는다.
- 국소 시각 조정은 관련 실제 화면 짧게 확인. 애니메이션·입력·판정은 해당 동작/취소/복귀. 두 FPS는 프레임 의존성 때만. 전체 회귀·Game 빌드는 통합과 위험에 맞춰 묶는다. 통과한 검사를 새 변경·실패 근거 없이 반복하지 않는다.
- 캐릭터별 전용 파일은 담당을 분리하고 공유 파일은 통합 담당이 수정한다. 작은 색/크기 조정까지 무조건 서브에이전트로 나누지 않는다. GPU 에디터는 직렬 실행한다.
- `render_lock.py`는 해당 도구를 사용하는 오프스크린 에디터끼리만 조율한다. UBT·사용자 에디터·Claude의 외부 실행 전체를 잠그지 않는다.
- 현재 manifest는 `UnrealEditor-LearnTopDown.dll`이다. 열린 에디터가 실제로 무엇을 로드했는지는 별도 확인한다. 예전 번호 붙은 DLL을 가정하지 않는다. 잠금 증거가 있을 때만 저장/종료를 요청하고 사용자 에디터를 강제 종료하지 않는다.
- 원본 팩·사용자 변경·미확정 시안 보존. 전체 해시/로그 덤프/대량 캡처를 매번 반복하지 않는다. Git 커밋·push는 이번 저장 요청에 포함되지 않는다.

## 8. 새 세션 시작 문구

> `C:/Users/USER/Desktop/MyGit/UEClient/LearnTopDown/Tools/CharacterPipeline/SessionHandoff-20261021.md`를 먼저 읽고, 필요한 부분만 `SkillPolishKnowhow.md`에서 확인해. 암살자 E A/D는 미확정 비교 시안이고 신규 스킬 일괄 제작은 아직 시작하지 않은 상태야. 다른 Claude 작업의 최신 변경과 충돌하지 않게 확인한 뒤, 내가 이어서 지시하는 작업을 진행해. 이미 승인된 방향은 재확인하지 말고 검증은 변경 위험에 맞춰 해.

## 9. 10-21 후속 — 신규 ASDF 8개와 연출 보강

- **현재 설치:** 1번 A 혈인 / S 그림자 쇄도 / D 밤의 격류 / F 그림자 매복, 2번 A 퇴로 사격 / S 연쇄 화살 / D 매복 화살 / F 낙성 일제. 숫자 1·2로 선택하고 ASDF로 사용한다. 기존 QWER과 저장된 4칸 정의는 별도로 보존했다.
- **보강:** 암살자는 원본 검 메시·잉크 질감, 실제 포즈 잔상 최대 3개, 분신 공격 동작·침식. 궁수는 활 앞 압력·후퇴 바람, 도탄 명중 문양, 화살 덫 전개/접힘, 최대 5지점 예고/낙하/착탄. 3·4번 에셋을 transient MID로 재사용하고 원본 재질을 저장하지 않았다.
- **최종본:** [보강 비교](../../Saved/QA/CharacterPipeline/new-skills-polish-20261021/preview.html), [결과](../../Saved/QA/CharacterPipeline/new-skills-polish-20261021/result.json). 서버가 살아 있으면 `http://127.0.0.1:55811/new-skills-polish-20261021/preview.html`. 암살자 화면은 `visual-03`, 궁수는 `visual-02`가 최종이다. `visual-01`과 `visual-02`의 암살자 직사각 외곽은 반려된 중간본으로 보존했다.
- **검증:** 최종 C++ Editor/Game Development 빌드 통과. 보강 묶음 60fps 130개 검사(8개 정상 피해·취소·쿨타임·덫 만료·소유자 종료 정리), 암살자 최종 재질 후속 28개 검사 통과. 최종 PIE 재질 컴파일 실패/ISM usage 경고 0. 공통/3·4번/원본 에셋 20개 hash 불변, 두 캐릭터의 피해·쿨타임·사거리·발동·복귀 배열 10개 불변.
- **이전 기능 근거:** [첫 제작 결과](../../Saved/QA/CharacterPipeline/new-skills-20261021/result.json)에 30/60fps 피해 비교와 기존 QWER·벽·이동·전환 검사가 있다. 보강은 전용 시각 효과와 분신 표현만 바꿨으며, 이 후속 재질 수정마다 전체 회귀를 반복하지 않았다.
- **파일:** `CountessSkillComponentExtras.cpp`, `CountessExtraTide.*`, `CountessExtraVisual.*`, `SparrowSkillComponentExtras.cpp`, `SparrowArrow.*`, `SparrowSkillVisual.*`와 관련 컴포넌트 선언. 전용 생성 스크립트 `countess_extra_materials.py`, 공통 PIE 도구 `new_skills_probe.py`. 신규 재질은 `M_CountessExtraInk_20261021` revision 4 한 개다.
- **남은 구분:** 실제 쿼터뷰 표본은 담당이 확인했으나 사용자의 최종 미적 채택은 아직 받지 않았다. 3·4번과 동일 품질의 객관적 인증이나 GPU 성능 계측을 뜻하지 않는다. 기존 LevelStart 누락 참조·startup Condition failed 메시지의 원인/영향은 이번에도 수정하지 않았다. 기존 E A/D 시안은 계속 미확정이며 신규 ASDF와 별개다. 커밋·push는 수행하지 않았다.

## 10. 품질 재작업 — 대표 신규 D 재설계 검토본

- **승인 경위:** 사용자가 8개 외형을 기대 이하로 평가했다. 기능 통과를 품질 완료로 보고한 판단을 정정했고, 대표 하나를 원본 입체 FX 중심으로 재설계해 실제 화면을 먼저 제시하는 방향을 승인받았다. 대표는 **1번 신규 D 밤의 격류**다. 남은 7개까지 같은 품질로 완성됐다고 보고하지 않는다. 현재 D의 미적 채택도 미결이다.
- **현재 적용:** `CountessExtraTide.*`의 평면 전면/평면 명중 형상을 제거했다. 원본 `P_Countess_BladeSiphon_Trails`의 D 전용 사본 `P_CountessNightTideBody`를 세운 입체 잉크 회오리로 전진시킨다. 원본 Wing/Blade 메시 외곽과 원본 잉크 결을 유지한 전용 재질, 제자리 파열·침식, 별도 월드 잔상을 조합했다. 실제 원본 전체 FX를 먼저 살피고 구성했으며, 둥근 붉은 코어 시안은 제외했다.
- **보존:** 피해 40, 사거리 900cm, 속도 1000cm/s, 적 판정 반경 100cm, 벽 차단/동일 대상 1회 피해 경로는 유지했다. QWER·공통·3/4번·맵/설정 등 보호 파일 22개 및 Countess 정의 배열 5개 일치. 원본 재질/PS 5개 파일도 author 전후 hash 일치. 원본 팩은 저장하지 않았다.
- **최신 근거:** [비교·영상](../../Saved/QA/CharacterPipeline/countess-D-rebuild-20261021/preview.html), [결과](../../Saved/QA/CharacterPipeline/countess-D-rebuild-20261021/result.json). 실제 캡처는 `verify-final`, 영상 `Countess-D-review.mp4`는 8.8초/1280×800/H.264/60fps/무음이다. 132개 실제 게임 프레임을 정상 속도 2회 + 0.5배속으로 편집했고, 전체 디코딩 오류 0 및 로컬 브라우저 끝 재생을 확인했다. 원격 업로드한 파일은 아니다. localhost 55811이 살아 있으면 `/countess-D-rebuild-20261021/preview.html`.
- **검증 범위:** Editor/Game Development 빌드 통과. 마지막 Countess 신규 ASDF 60fps 기능 검사 68개 통과: D 두 대상 각각 40, 측면 제외, A/S/F 피해·취소·쿨타임·회복, D/F 소유자 종료 정리. D 벽 검사는 `visual-05`의 통과 결과를 재사용했으며 그 뒤 판정 코드를 바꾸지 않았다. 원본 startup/LevelStart 경고 원인·영향 및 패키지 실행/GPU 비용은 이번에도 확인 범위 밖이다.
- **재현 도구:** `countess_tide_materials.py`가 Wing/Blade/Edge 재질과 D 전용 PS를 만든다. 원본 Wing DP의 `(WipeOn=0,WipeOff=1)`은 전체 투명이며 표시값은 `(1,0)`이다. 기존 입력/텍스처/WPO/MI 유효값을 사본에서 보존하고 D용 `TideTint/TidePhase/TideOpacity`로 제어한다. 위치 생성형 PSC는 절대 좌표로 만들어지므로, D 본체를 부착한 후 `SetAbsolute(false,false,false)`와 명시적 상대 변환을 적용한다. 이 처리가 없던 `visual-09/10`은 폐기한 비교본이다.
- **중간본 구분:** `visual-05/06`의 둥근/타원 코어는 반려한 내부 시안이며 설치 D에서 참조를 제거했다. `countess_tide_core_material.py`와 그 전용 재질은 실험 기록만 남았으며 기본 설치 도구가 아니다. `visual-11`은 본체가 처음 제대로 따라간 버전, `verify-final`이 사용하지 않는 코어 참조를 정리한 현재 버전이다. 초기 audition/author 실패는 QA Python API/재진입 문제였으며 통과로 바꾸지 않았다.
- **앞선 2차 보강:** `new-skills-quality2-20261021/visual-02`는 이번 D 직전의 화면이다. Countess A의 작은 실제 타격 파열 보강은 앞서 작성됐지만 빌드 전 대기하던 것으로, 이번 통합 빌드/Countess 기능 검사에 함께 포함됐다. Sparrow A/S 2차 시각 보강은 그대로 동결했고 이번 대표 D 작업에서 변경하지 않았다. quality2의 `preview.html`에는 미생성 최종 경로가 있으므로 이번 결과의 최종 링크로 쓰지 않는다.
- **다음 한 가지:** 대표 D의 실제 영상과 3/4번 기준 화면을 비교해 이 연출 방향의 미적 채택 여부를 확인한 뒤, 승인된 무인 제작 범위 내에서 나머지 신규 스킬에 각자의 본체·명중·소멸 구성을 적용한다. 기존 E A/D 미확정 시안과는 별개다. 커밋·push/클라우드 업로드 없음.

## 11. 사용자 직접 플레이용 현재 작업 취합

- **최신 지시:** “지금까지 작업한 거만 취합해 봐 내가 직접 게임에서 보게.” 추가 후보 조사·품질 보강은 중단했다. 다음 작업은 직접 플레이한 사용자 피드백을 받은 뒤 정한다.
- **실행:** 프로젝트 루트 `Play-CurrentSkills.cmd`. 열린 Development 에디터 PID 22204가 이전 DLL을 로드 중이므로 보존하고, 별도 DebugGame DLL로 수련장을 게임 창에 실행했다. 숫자 1/2 선택, ASDF 신규, QWER 기존, 우클릭 이동·좌클릭 기본 공격. 쿨타임 무시 연습 설정 유지. 실행 PID와 로딩 상태는 [play-session.json](../../Saved/QA/CharacterPipeline/current-skills-review-20261021/play-session.json)에 남겼다. PID는 다음 세션에서 생존 여부를 재확인한다.
- **취합:** 암살자 A/F 원본 입체 FX 연결 및 전용 PS 5개, S 기존 실제 포즈 잔상, D §10 재설계본. 궁수 ASDF는 quality2 보강본이다. 궁수의 추가 원본 PS 연결은 하지 않았고, `SparrowSkillVisual.*`의 준비 함수는 호출되지 않는다. 생성한 8칸 그림은 콘셉트 자료이며 게임에 구현된 모습이 아니다.
- **저장 문제 해결:** `ParticleModuleLocationBoneSocket.bEnabled`는 Python에서 읽기·쓰기가 보호된다. 기존 `CountessFXAutomation.cpp`에 전용 사본 5개만 허용하는 에디터 보조 명령을 추가했다. `countess_af_effects.py`가 이를 호출하고 원본 5개 hash 불변을 확인한다. 초기 author 실패 3회는 기록으로 남기고 최종 `verify-04`만 현재 근거로 사용한다.
- **검증:** DebugGame Editor 빌드 및 신규 8개 60fps 기능 검사 130개 통과. 선택 보호 파일 22개, 두 캐릭터 정의 배열 10개 불변. A/F 실제 대표 프레임 확인. A 준비가 표본에서 약하게 보이고 F 명중이 밝은 주황색으로 보이는 현재 상태를 보관했다. 미적 완성 판정이나 새 전체 QWER 회귀·패키징 검증은 하지 않았다.
- **결과:** [result.json](../../Saved/QA/CharacterPipeline/current-skills-review-20261021/result.json), [플레이 안내](../../Saved/QA/CharacterPipeline/current-skills-review-20261021/PLAY-REVIEW.md). 기존 E A/D 비교 시안은 계속 별개·미확정이다. 커밋·push 없음.


## 12. 기존 QWER 재작업 — 확인 완료한 묶음

- Countess E: 본체3+분신3·45피해·기존 타이밍/배치/침식 보존. 실제 검 소켓 궤적과 원본 XSlash/피격/마지막 파열을 연결했다. 원본 ColorA/B/C 정보를 실제 FMaterialParameterInfo로 읽어 MID만 조정하며 EInkGain 기본 .06을 채택했다. 원본 전체 형태를 .44초/1.05~1.22크기로 확보했다. 원본 RGB/실제 렌더 MID 3개/2개 일치 로그를 확인했다.
- Countess W 입력은 V로 이동했다. 기존 슬롯1/40피해 유지, W는 Countess에서 무시. HUD도 V. 다른 캐릭터의 W/V는 기존 라우팅이다.
- Sparrow 평타: 공통 opt-in ShouldFinishBasicAttackMontage 기본 false, Sparrow만 true. 조기 recovery/reset 예약을 제외하고 클릭 해제 후에도 공격 종료까지 활 준비 포즈를 보존한다. 단클릭 0.8초까지 완주/홀드 반복/해제 복귀를 실제 입력으로 확인했다.
- Sparrow W: 보관파일 그대로의 롤백은 확인되지 않아, 기록된 수평 3원 구성으로 복원했다. 추가 ShotAccent 직선 바람·섬광만 제거했다. E/R은 Rogue 원본 활·화살·명중 FX로 연결해 붉은 톤으로 확인. E6발/R10초5발·기존 수치 보존.
- 근거: `Saved/QA/CharacterPipeline/qwer-rework-20261021/result.json`. 기능은 `verify-sparrow`와 Countess V 개별 통과 행, Countess E/중단은 `verify-countess-tint`/`verify-gain`. GPU 경고가 나타난 초기 궁수 캡처는 채택하지 않고 기존 QA 512MB texture cache/1024 VSM pages 조건의 `verify-final`에서 W/E/R을 재확인했다. 설정은 해당 QA 프로세스만 적용했다.
- 단클릭 첫 검사는 0.833초 모션에 .85초까지 공격 상태를 요구한 검사 오류였고, 실제 시점 .80초까지로 바로잡았다. 초기 before 취소 호출은 Python 비노출 API 오류였다. 실패 기록을 통과로 바꾸지 않는다.
- 보호 파일17개·기존 수치배열10개 일치를 당시 확인했다. 이후 §13에서 사용자가 허용한 ASDF 제거/R 변경이 진행되므로 이 기록을 그 이후 전체 소스 보존 주장으로 재사용하지 않는다. 최종 패키징/성능 계측/사용자 미적 채택은 미확인이다.

## 13. 추가 무인 요청 — 구현·검증 완료

- 사용자 새 요청이 이전 R 원속도 보존과 궁수 ASDF 유지 조건을 명시적으로 덮는다. 현재 묶음 종료 후 단계별로 끝까지 진행하도록 승인했다. 추가 확인 질문·별도 자동화/스레드를 만들지 않고 같은 작업에서 이어간다.
- 1번 R: 유효한 적 옆으로 즉시 순간이동 후 원본 Ultimate의 start1.05/rate1.75 구간. 약 .43초 피해80/.69초복귀, 기존500범위/벽·캡슐·스턴정리 유지. 실제 즉시 접근·80피해·복귀·중단 시 무피해/스턴 해제·벽 거부를 확인했다.
- 1번 Space: 커서 위치 최대750cm blink, 안전한 바닥/캡슐/벽 검사, 이동 구간 붉은 짧은 포즈잔상3개. 슬롯17이며 다른 빈 슬롯은 이름 없이 비운다.
- 2번 이전 ASDF를 실행 경로에서 제거했다. A는320cm/s/90피해/1800범위의 수평 회전 톱날 화살(벽 차단·표적당1회), S는8초 후드 해제+황금날개 변신, D는뒤쪽 양옆 금/흰분신2개가각3발 사격/합계60피해. 새 F는 비웠다. QWER·평타는 §12 상태를 유지한다. 과거 ASDF 저작 에셋과 기록은 원본 보존을 위해 남겼으나 새 런타임에서 호출하지 않는다.
- 실제 자산 확인: `qwer-rework-20261021/verify-gain/ascension-wing-assets.json`. Sparrow Rogue 후드 MaterialID13(슬롯명M14_CloakHood), Serath 날개 IDs12/13. Serath wing 기본 WingAlpha=0이므로 표시값을 별도 설정해야 한다. Holy 재질에 파랑/보라 값도 있으므로 원본 패턴 보존 MID 황금색 보정 필요. LOD별 section 정보는 JSON에 있다.
- Countess 담당은 component.cpp/.h, Sparrow 담당은 전용 character/component/새 visual·projectile·저작 도구. 공통 입력/HUD·빌드·에셋 저장·GPU검증은 부모만 수행한다. 기준선은 `Saved/QA/CharacterPipeline/ascension-skills-20261021/baseline`. 열린 사용자 Development 에디터 PID16340(22:02 생성)은 강제 종료하지 않는다. 최신 검토 모듈은 별도 DebugGame DLL이다.
- **최종 근거:** [실제 화면·조작 안내](../../Saved/QA/CharacterPipeline/ascension-skills-20261021/preview.html), [결과](../../Saved/QA/CharacterPipeline/ascension-skills-20261021/result.json). `verify-ascension` 60fps 31개 검사 전체 통과, `verify-safety-30` 30fps 75개 검사 전체 통과. A의 두 대상 각90/측면 제외/벽, A/S/D 발동 전 중단, 비행 중 A 소유자 종료, A 실제 쿨타임, S 중복 방지·후드 복원·S+D 공존·전환 정리를 확인했다. R의 벽 거부와 Space의 시전 중 입력 거부·6초 쿨타임도 통과했다.
- **개별 통과 취합:** `verify-mobility`의 R 정상·중단 및 Space 정상, `verify-final`의 Space750cm/벽/잔상 소유자 종료는 해당 case의 통과 행38개를 `result.json`에 명시했다. 두 실행 전체는 실패 기록이다. 첫 range 입력은 화면 밖 벽을 가리켜 clear floor1100cm 입력으로 격리했고, A의 X1050 fixture는 Z711 높이의 구조물 위여서 같은 바닥 X450/X750(Z90)으로 바로잡았다. 벽 충돌을 우회하거나 실패 기록을 통과로 바꾸지 않았다.
- **시각 수정:** A의 닫힌 동전 모양을 작은 중심축+열린12개 살/칼날로 교체하고 ISM2개로 묶었다. D의 초기 회색 망토는 전용 재질의 clothing usage 누락이었으며, `used_with_clothing=True`로 재저작한 최종 실제 프레임에서 금/흰 망토까지 확인했다. 최종 검사 로그에 해당 재질 usage/컴파일 실패가 없다. S는 원본 Serath wing IDs12/13만 표시하며 `Wings_Unfold` 후 펼친 `Idle_Pose_Wings`를 유지한다. 본체 후드의 LOD별 기존 표시 상태를 저장·복구한다.
- **빌드·보존:** DebugGame Editor 최종 빌드14.61초, Development Game 빌드117.99초 통과. 선택 보호 소스/설정7개, §12 이후 Countess E 함수10개, 기존 QWER 정의 배열10개 일치. 신규 소스는 `SparrowAscension.*`, 전용 재질2개는 `sparrow_ascension_materials.py`로 생성했다. 원본 팩을 저장하지 않았다. 전체 프로젝트 해시 감사나 패키지 실행/GPU 비용 계측은 수행하지 않았다.
- **플레이:** 숫자1/2 선택, 1번V/E/R/Space, 2번A/S/D와 빈F. 쿨타임 무시 연습 설정은 유지하며 쿨타임 검사는 QA 프로세스 안에서만 정상 모드로 전환했다. 최신 게임 창 실행 상태는 같은 결과 폴더 `play-session.json`에 저장한다. 기존 사용자 Development 에디터의 Play가 최신 DebugGame 코드와 같다고 말하지 않는다. 커밋·push 없음.

## 14. 10-22 궁수 공속·W 두께·황금색 팔레트

- 사용자 요청: 2번 기본 공격을 현재보다1.5배 빠르게, W 투사체를 두껍게, E 및 거의 모든 FX를 황금/흰색 중심에 필요한 소량의 보라색으로 통일.
- `Sparrow.Attack.Speed` 기본1.2→1.8. 기존 BeginPlay 경로가 평타 몽타주와 반복 대기 시간을 같은 배율로 조정한다. 단클릭 완주 정책은 유지했다. 실제 몽타주 위치/시간 기울기1.799999, 이전 대비1.499999를 확인했다. 연속 공격의 초당 피해도 늘어나는 의도된 변경이다.
- W만 `ASparrowArrow::SetVisualWidthScale(2)` 적용. 로컬Z가 길이인 메시에는(2,2,1), 액터X 방향 궤적에는(1,2,2) 적용. 충돌 반경12/발사 속도/피해 유지. 실제 게임 화살 컴포넌트 값과 화면을 함께 확인했다.
- E/R Rogue 붉은 PS 선택을 제거하고 기존 기본 Sparrow의 황금/흰색 PS로 연결했다. 짧은 준비 리본·활 불꽃·발사·화살·명중 모두 같은 계열이다. 기존 평면 R fan을 다시 켜지 않았다. Q와 평타, 이미 황금/흰색인 A/S/D는 같은 계열을 유지한다. W 원본에는 소량의 보라 중심선이 있다. 원본 팩/저장 에셋 수정 없음.
- 근거: `Saved/QA/CharacterPipeline/sparrow-gold-speed-20261022/result.json`, 실제 프레임은 `verify-final/screenshots`, 60fps 관련 검사43개 통과. 단클릭·홀드·해제·W폭/충돌반경·E중단·R5발 및 Q/W/E/R 화면 확인. 기존 QWER의 수치 배열5개 일치. 처음 verify의 배속 계산은 블렌드아웃 후 빈 몽타주 표본까지 포함한 검사 오류였고, 실제 몽타주가 있는 표본으로 계산한 verify-final이 최종이다.
- DebugGame Editor와 Development Game 빌드 로그는 같은 결과 폴더에 있다. 이전 전체 ASDF·두FPS 검사를 이번 국소 조정에 반복하지 않았다. 최신 게임 창/모듈 확인은 `play-session.json`을 사용한다.

## 15. 10-22 평타 멈춤 단축 · W 시안 · 활 후보 조사

- 사용자 요청: W 원형 이펙트 평가와 몇 가지 시안, 빨라진 공속에 맞춰 평타 중 멈춤 축소, 프로젝트 활 스킨 조사. W 최종안이나 활 교체를 승인한 요청은 아니다.
- 실제 게임 변경은 `SparrowCharacter.cpp`의 평타 전환과 추가 대기다. `ComboRestartCooldown=min(기존값,.08)/AttackSpeed`로 현재 .167→.044초. 일반 몽타주를 런타임 transient 사본으로 만들어 BlendIn .12/1.8, BlendOut .18/1.8; HeldPrimary가 계승하고 HeldInnerFire도 공속으로 전환 시간을 나눈다. 한 발의 전체 모션·발사 시점·피해는 유지한다.
- `sparrow-flow-concepts-20261022/verify2/attack-flow.json`: 실제 60fps 연사 간격 .6167/.6000/.6000초, 공격 사이 대기 .05초. 단클릭 완주·한 발 피해20·홀드/해제·발사 전 취소·이동 복귀 통과. R 강화 평타 발사/복귀는 `bows-view/new-skills.json`에서 확인했다.
- W 기본 연출은 기존 그대로다. A 작은 절개 고리, B 양옆 곡선, C 직선 광창을 실제 PIE에 임시 배치한 정지 시안으로 만들었다. 신규 preview 재질3개만 `/Game/TopDown/Characters/Sparrow/Previews/W20261022`에 저장했다. 최종 스킬 타이밍/잔상은 미저작·미채택이다. `preview.html`, `W-comparison.png` 참고.
- 활은 기본/Rogue/AutumnFire/FelineQueen/Monarch/Raven/Tough/ZechinHuntress 총8개 실제 SkeletalMesh를 조사했다. 기본·Raven·ZechinHuntress와 현재 Rogue 외형, Raven의 무기 섹션3/7 분리 표시를 `bows-view/screenshots`에서 직접 확인했다. 독립 활 설치가 아니라 후보 조사·비교만 진행했다. Tough는 별도 스켈레톤이라 실제 자세 비교에서 제외했다.
- 활 도구의 초기 오류·잘못된 자세 캡처는 최종으로 채택하지 않았다. `SkeletalMeshEditorSubsystem`의 LOD/section 조회는 PIE 전, runtime은 그 매핑만 사용한다. 비교 액터는 실제 Sparrow `LeaderPoseComponent`를 사용하고 재질을 각 스킨 기본값으로 명시 배정한다. 회전은 `leader.get_world_rotation()`에서 yaw만 바꾼다. 임시 액터 제거·held 입력 해제·운영 메시 보존을 확인했다. 최종 근거는 `sparrow-flow-concepts-20261022/result.json`과 `bows-view`다.
- DebugGame Editor 13.98초, Development Game31.08초, Development Editor153.57초 빌드 성공. 당시 사용자 에디터가 종료된 상태라 일반 에디터 모듈도 갱신했다. 전체 ASDF/30fps/패키징·성능 측정을 추가 반복하지 않았다. 커밋·push 없음.

## 16. 10-22 W A 계열 보강 4안 · Raven 활 임시 장착

- 사용자 요청: A가 밋밋하므로 A 느낌의 여러 시안, 보라색 활 교체 가능 여부와 다른 활 후보. 이번에도 시안·가능성 확인 범위이며 영구 적용은 하지 않았다.
- A1 겹날 압력환, A2 각인된 성환, A3 깃털빛 환, A4 파열 압력환. `/Game/TopDown/Characters/Sparrow/Previews/WRefined20261022`에 신규 재질4개만 저장했다. 기존 W 액터를 실제 발사 순간에 임시 변경한 정지 형태 시안이다. `sparrow_flow_concepts.py`의 `SPARROW_W_REFINED=1` 저작 경로와 `refined_sequence`로 재현한다. 최종 회전·퍼짐·소멸 타이밍은 미저작·미채택이다.
- Raven 활은 실제 Rogue 플레이 캐릭터에 크기1로 임시 장착했다. Rogue의 LOD별 Arrow/String/Bow 슬롯2/5/6을 숨기고, Raven 슬롯3/7만 표시한 임시 액터가 실제 mesh LeaderPose와 월드 위치/회전을 따르게 했다. 의상 메시·재질 유지, 기본 공격·W/E/R·S 변신 장면, 종료 후 원래 무기 섹션 복구 및 임시 액터 제거를 확인했다. `sparrow_bow_audit.py`의 `fitting_sequence`이며 운영 C++에 장착 코드를 추가하지 않았다.
- `Saved/QA/CharacterPipeline/sparrow-A-refined-20261022/verify/new-skills.json` 60fps 검사38개 통과, `sparrow-bow-fitting.json` passed/sections_restored/preview_cleaned=true. 실제 PNG 확인 완료. 네이티브 수정이 없어 빌드·이전 평타 회귀를 반복하지 않았다. 시작 시 UnifiedErrorTest 출력은 PIE 시작 전 엔진 테스트 로그이며 이번 재질 컴파일 실패는 없었다.
- 사용자 비교판: 같은 폴더 `preview.html`, `W-A-comparison.png`, `Raven-fitting-comparison.png`. 비교판은 원본 게임 프레임의 같은 비율 확대이며 각 원본 링크를 남겼다. 원본 팩·게임 기본값·평타 설정 변경 없음. 활 후보는 Raven, 기본 금속/금빛 장식형, Zechin 목재형. AutumnFire/FelineQueen/Monarch의 BowAndArrow 슬롯은 기본 재질을 공유한다. 커밋·push 없음.

## 17. 10-22 W=A1 · A=A3 깃털환 실제 적용

- 사용자 채택: W는 A1, A스킬은 A3 느낌. 활은 추가 후보 여부 질문이며 교체 요청은 아니므로 현재 Rogue 활 유지.
- W `ASparrowShotWave`: 운영 재질 `M_SparrowShotSplitRing`과 두 겹 절개 고리. 평면 스케일2.6/1.5에서0.4 확대, 앞쪽 보조 고리는 간격95cm·밝기0.5, 빠른 진입 후0.12초부터 페이드. 원래 액터 수명0.42초/카메라 반동/발사·피해 유지. `ASparrowBowFeedback`의 기존 E/R 재질 참조는 그대로다.
- A `ASparrowGearArrow`: Hub/Teeth/Spokes 금속 톱니를 `M_SparrowGearFeather` 두 Plane으로 교체. 메인/보조 평면 스케일2.35/1.6, 보조 위치-30cm·밝기0.45, 중심 금속 화살과540deg/s 회전 유지. 기존 속도320/범위1800/반경70/표적당90피해와 관통·소멸 경로, S/D 본문 보존.
- `sparrow_flow_concepts.py`의 `SPARROW_W_INSTALL=1`은 채택한 A1/A3 공식만 운영 Materials 폴더에 저장한다. 기존 시안4개/원본 팩은 보존. 검사 focus `sparrow_adopted`는 임시 메시나 재질 덮어쓰기 없이 실제 운영 클래스를 사용한다.
- 근거: `Saved/QA/CharacterPipeline/sparrow-A1-A3-installed-20261022/verify2/new-skills.json` 관련60fps 검사28개 통과. W35피해·2겹·정리, A속도319.99999cm/s·직선 표적2개 각각90피해·측면 제외·수명 종료/캐릭터 전환 정리, 실제 W/A 화면 확인. 첫 verify는 검사 대기가 W의 기존2.25초 복귀보다 짧아 실패했고 검사 대기만 보정했다. 그 실패를 통과로 덮어쓰지 않았다.
- 일반 Development Editor·Development Game·기존 별도 창용 DebugGame Editor 모두 갱신. 실제 PIE 확인은 Development Editor 구성이다. 패키징/새 활 설치/30fps 전체 회귀는 수행하지 않았다. 커밋·push 없음.
- 활 추가 검색: 현재 Content의24868개 uasset 파일명에서 bow/crossbow/archer/weapon 후보를 다시 검색했으며 추가 무기 모델로 확인된 것은 없다. `SM_Sparrow_Bow_Flames`는 활 불꽃 FX이며 추가 활 스킨이 아니다. 알려진 Sparrow 메시8개와 앞선 실제 슬롯 조사 근거를 함께 남겼다(`bow-search.json`). 외부 에셋 전체에 활이 없다고 뜻하지 않는다.

## 18. 10-22 궁수 범위기·다발사격·황금 변신·동행 분신

- 사용자 승인: Q의 대상 지정 제거, W의 짧은 발사 연출, E 여러 시안, 다량 화살 R, 작은 A, S의 망토 제거와 황금 외형, D의 실제 스킬 복제. 서브에이전트/단계별 무인 진행을 명시 허용했다. 부모가 공통 입력과 W, 각 담당이 Q/R·A/S/D·E 시안의 파일을 소유했고 빌드·GPU 검사는 직렬로 수행했다.
- **Q:** `ESkillTargeting::Ground`를 기존 enum 뒤에 추가했다. `KwangPlayerController::UseSkill`에서 pawn/훈련 표적을 제외한 커서 바닥 좌표를 전달해 적 중심으로 스냅하지 않는다. 사거리1400/반경300/4초8회/총40피해 유지. Hail 입자 밀도1.8→2.4와 짧은 착탄 섬광을 적용했다. 다른 캐릭터의 타기팅은 기존 경로다.
- **W:** 채택된 A1 두 고리를 유지하며 고리당0.28→0.14초, 액터0.42→0.24초로 압축했다. 축 방향 섬광은0.10초, 기존 주 발사 emitter는0.18초 안에 정리한다. 투사체 두께2배/피해35/발사0.62/복귀2.25초는 유지했다. **A:** 깃털 평면2.35/1.6→1.6/1.08로 약32% 축소, 중심 금속1.8→1.35. 속도320/반경70/거리1800/피해90/관통은 유지했다.
- **R:** 이전10초 평타 강화 버프를 능동 다발사격으로 교체했다. 78도 부채꼴21발×3회=63발, 준비0.12/간격0.22/복귀0.94초, 속도2600/거리1800. 회차별 공유 피격 집합으로 대상당 최대20×3=60피해를 제한하고 패시브 중첩은 제외한다. 벽에는 차단되며 표적은 관통한다. 우클릭/시전 취소는 남은 발사를 중단한다. 첫 실제 화면의 번개 같은 궤적을 검토한 뒤 R만 두 교차 평면의 곧은 금빛 잔상으로 바꿨다.
- **S:** Rogue의 ID3 `M16_CloakStraps`, ID7 `M08_Cloak`, ID13 `M14_CloakHood`를 모든 LOD에서 숨긴다. 본체16개 재질을 기존 황금 분신 재질의 MID로 바꾸며8초 후 재질·이전 section 표시 상태를 복구한다. Serath/Muriel wing 후보를 확인했으나 바로 교체 가능한 디아블로식 긴 빛줄기 날개는 확인하지 못했다. 사용자의 조건에 따라 기존 Serath 날개 형태는 유지했다.
- **D:** 양옆 뒤의 금/흰 분신2개가10초 따라다니며 본체의 실제 평타·Q/W/E/R/A 발동을 각30%피해로 복제한다. 자동3발 사격은 제거했다. S는 외형/날개만 동기화한다. 분신의 재귀 생성·패시브 누적은 막고, 각 R 분신도 독립 회차별 피격 제한을 쓴다. 본체와 두 분신이 전부 맞히면 R 최대96피해다. 취소/캐릭터 교체/수명 종료 때 정리한다.
- **E 시안만:** `sparrow_e_variants.py`가 기존6발/간격/피해를 유지한 실제 PIE에서 E1 열린 이중 곡선, E2 여섯 깃털/별빛, E3 짧은 축 섬광/잔상을 비교한다. 신규 재질3개만 `Previews/E20261022`에 저장했으며 운영 E는 바꾸지 않았다. 원본 프레임0.20/0.53초 두 장과 확대 출처를 비교 페이지에 표시했다. E3를 우선 추천하되 사용자 선택은 아직 없다. Q 마지막 낙하/깃털 흔적, W 준비 고리 압축, A 명중 깃털 파편은 페이지의 **추가 제안이며 미적용**이다.
- **검증:** `verify60/new-skills.json` 127개, `verify30/new-skills.json` 65개 모두 통과. 빈 땅 Q/반경·피해, 짧은 W 정리, 작은 A/관통, R63발·회차별 피해 제한·측면 제외·중단, D 동행·실제 발동 복제·수명·전환 정리, S 재질/망토 복원·D 날개 연동을 확인했다. 60fps는 R 잔상 최종 조정 전 Development Editor, 30fps는 최종 직선 잔상 적용 후 DebugGame Editor다. R 최종 화면은 `verify30`, 나머지 대표 화면과 E 시안은 `verify60`를 사용한다.
- **빌드/근거:** 최종 Development Editor7.75초, DebugGame Editor38.42초, Development Game53.71초 성공. [실제 화면·시안](../../Saved/QA/CharacterPipeline/sparrow-arsenal-20261022/preview.html), [결과](../../Saved/QA/CharacterPipeline/sparrow-arsenal-20261022/result.json). 기존 AnimBP 초기화 divide-by-zero/누락 패키지5개/PIE 이전 UnifiedErrorTest 로그는 이전 실행에도 존재해 이번 신규 실패로 집계하지 않았다. 패키징·성능 벤치마크·사용자 미적 채택은 미확인. 원본 팩 저장·커밋·push 없음.

## 19. 10-22 궁수 FX 질감 보강 · 짧고 촘촘한 R 186발

- **사용자 방향:** 모든 스킬의 비어 보이는 느낌을 줄이되 3번 캐릭터를 그대로 복제할 필요는 없다. R은 이전 긴 방사형 궤적을 반려하고, 훨씬 작고 짧은 화살이 빽빽하게 쏟아지는 형태를 요청했다. 기존 무인 진행 승인 범위에서 담당별 파일 소유권을 지키고 GPU 에디터·빌드를 직렬 실행했다.
- **R:** 31발×6회=186발, 준비 .12/간격 .10/복귀 .94초. 전체 피해60/거리1800/속도2600/78도 부채꼴은 유지하고 회차별10피해로 제한한다. 작은 화살촉 .45–.60, 꼬리30–55cm/폭1.5–2cm, 앞뒤 시각 위치0–35cm를 분산했다. 원래 3회의 발사 애니메이션을 압축해 유지한다. 명중 .65크기/.55초, 겹침이 과했던 R 벽 착탄만 추가 .22배/.18초로 축소했다. 분신은 동일한186발을 각30%로 복제한다. 입력 취소·관통/벽 차단 경로는 유지한다.
- **Q:** 원본 Falling/FallingLingerArrows만 밀도3.2, 본체 rain scale .78. 경계 밝기 .28, 지면에 원본 구름 텍스처를 쓰는 전용 재질 `M_SparrowHailAtmosphere`를 추가했다. 매 낙하의 착탄과 마지막 파열도 보강했다. 원본의 충돌 이벤트/착탄 연결,4초8회/피해40/반경300은 유지한다. 파티클 전체를 일괄 증폭하지 않는다.
- **W/E:** W의 채택된 A1 고리 .14초/액터 .24초는 유지하고 원본 Wisps/Airglow의 짧은 발사 압력을 추가했다. 고리 밝기는 .7/.32, 입자 안전 정리 .30초. E는 원본 PrimaryTrail을 유지하고 폭1.5와 별도 Wisps 질감 PSC(80–110cm, alpha .5,45/s)를 덧댔다. 발사광 .24초, 활의 BowFlames/Embers만 추린 transient 효과, 작은 연속 명중을 연결했다. E6발/기존 타이밍·피해·패시브 유지. 이전 E 시안3개를 자동 채택한 변경이 아니다.
- **A/S/D:** 작은 A 깃털환 크기는 유지하고 local Airglow 중심 .70scale과 실제 명중 시 원본 Sparks/MainFlames/Wisps 파편을 추가했다. S/D 등장은 원본 Burst의 plasma/flame shard만 추려 짧게 사용한다. D는 실제 발사 때 윤곽을 강조한다. S8초/망토3·7·13 제거와16재질 복원/기존 Serath 날개, D2개10초·동행·실제 스킬 복제는 유지했다. 새 디아블로식 날개나 활 스킨을 설치하지 않았다.
- **현재 근거:** [영상·실제 화면](../../Saved/QA/CharacterPipeline/sparrow-volume-20261022/preview.html), [결과](../../Saved/QA/CharacterPipeline/sparrow-volume-20261022/result.json). R 영상은 `verify-r-final`의 실제42프레임/1280×720/30fps/1.4초 무음이며 보간하지 않았다. 정상·0.5배속 브라우저 재생, 이미지8개 로딩, 전체 영상 디코딩을 확인했다. 다른 스킬 최종 화면은 `visual-final-2`다.
- **검증:** `verify60`109개는 1차 전체 기능 검사, `visual-final-2`26개는 W/E/A 재보강 후 국소 검사, `verify30`65개는 최종 작은 화살 R/D/S·취소·복원, `verify-r-final`19개는 벽 착탄만 추가 보정 후 R/D 화면 검사다. 전부 passed. R186개 실측, 중앙 대상60피해, 분신186개 복제, 중단 이후 추가 발사 없음, 소유자 종료 정리를 확인했다. 30/60은 고정 timestep 조건이며 성능 측정이 아니다.
- **빌드/실패 기록:** 최종 DebugGame Editor12.95초, Development Editor11.79초, Development Game28.25초 성공. 초기 native const API 빌드 오류는 수정 후 성공했다. `visual-final`은 선행 W의 대상 패시브1중첩을 검사 기대값에 빠뜨려 실패했으며, 실제 중첩 수를 읽어 계산한 `visual-final-2`가 현재 근거다. Q 재질 재저작 중의 연결 미완성 경고는 중간 상태였고 최종 저장본을 새 에디터에서 열어 재질 컴파일 실패0을 확인했다. 실패 폴더는 남겼다.
- **다음:** 사용자가 영상/직접 플레이로 느끼는 밀도·길이·밝기 피드백을 기준으로 해당 스킬만 조정한다. 구현/기능 통과를 미적 승인으로 취급하지 않는다. 원본 에셋 팩 저장·패키징·성능 벤치마크·커밋·push는 하지 않았다.

## 20. 10-22 Q/W/A 조정 · S 에너지 질감 · E/A/D 추가 시안

- **사용자 요청:** Q의 바닥 안개 제거/낙하 화살20% 감소, W 후딜 거의 제거, E 다른 시안, A 감속과 갈리는 느낌 보강법, S 마인 같은 몸 질감, S 중에도 D 분신 날개 금지/다른 외형 여러 시안, 구르기 애니메이션 조사. 기존 무인 진행 범위에서 확정 수정과 임시 시안을 구분했다.
- **실제 Q/W/A:** `HailVisualDensity`3.2→2.56. Atmosphere 생성·tick·cleanup·FHailZone 포인터 제거, 기존 저작 재질 파일은 보존했다. Q4초/40피해/반경300 유지. W 발사 .62/복귀2.25→.72, W만 blendout .06. BP에 저장된 과거 기본2.25/2.75도 이행한다. 실제 발사 후 잠금은30/60fps 모두 .100초이고 이동·발사 전 취소·피해35 통과. A320→220cm/s,90피해/반경70/1800거리/관통 유지; 비행이 길어져 소유 PSC Airglow 반복을 화살 수명에 맞췄다.
- **실제 S/D:** S 전용 `M_SparrowAscensionEnergy`를 추가해 내부 흐름/결/윤곽광/소량 보라 명암을 사용한다. 원래 Echo 재질과 분리했으며8초 뒤16재질/망토3·7·13 복원 통과. 날개 형상은 기존 Serath. D의 WingEcho 컴포넌트/SourceWings/복사 경로를 제거했다. 본체 S 날개1개만 남고 D는 자세·망토 표시만 동기화한다. D 기본 메시와 에코 피해/동작은 그대로다.
- **E 시안 v2:** `sparrow_e_texture_studies.py`는 실제6발/피해를 유지한다. E1 원본 긴 trail 임시 숨김+짧고 굵은 Wisps, E2 원본 곡면 Flames2 약4배 확대, E3 원본 입자 색 곱을 MID로 역보정한 백금 흐름. 첫3안은 쿼터뷰 차이가 너무 작아 실제 화면을 보고 수정했다. E2가 가장 뚜렷하고 E1/E3 차이는 상대적으로 작다. 운영 E 및 원본 PS/재질은 바꾸지 않았다.
- **A/D 시안:** `sparrow_form_studies.py`. A1 실제 접촉 뒤 .00/.08/.16/.24초 절삭 불티, A2 양옆 파열. 피해 추가는 없다. 강한 기존 코어 때문에 아직 완성된 분쇄감으로 평가하지 않는다. D1 Raven 부유 활, D2 Raven 투구/어깨/상체+75–110cm 하체 fade, D3 Raven 전신 궁수령. D2 초기 Rogue 부분 섹션은 장식이 떠다녀 폐기하고 preview전용 `M_SparrowUpperBodySpiritStudy`로 수정했다. 각 분신 실제 공격 에코/cleanup 확인. 미채택 시안을 기본 외형에 설치하지 않았다.
- **구르기:** `production60/sparrow-dodge-audit.json`. 현재 Content24874개 파일명과 후보10개의 실제AnimSequence/스켈레톤/길이/루트모션/포즈샘플 확인. 전용 구르기로 확인된 것은 없다. MM_Dash(.967초), Aurora RMB4종(1.933초)은 다른 스켈레톤으로 리타게팅 필요. Sparrow 점프/착지/물구나무는 같은 스켈레톤이나 구르기로 단정하지 않는다. 외부 에셋 전체 부재나 회피스킬 설치를 뜻하지 않는다.
- **검증/실패:** `production60`28개 passed. `studies30`의 W30/S/D1/D3 포함39개 통과 행을 재사용하되 A시안 helper의 미노출 `deactivate_system` 오류로 실행 전체는 failed를 유지한다. Python `deactivate`로 수정한 `studies-final`38개 passed에서 A2를 사용. D2/A1/E v2 최종 `studies-refined`37개 passed. S/D 원본 수명·복원과 다른 기능 검사를 반복하지 않았다. DebugGame Editor16.39초/Development Editor15.04초/Game22.66초 성공. 패키징·성능 계측은 하지 않았다.
- **전달:** [비교 페이지](../../Saved/QA/CharacterPipeline/sparrow-feedback-20261022/preview.html), [result.json](../../Saved/QA/CharacterPipeline/sparrow-feedback-20261022/result.json). 실제 영상9개/30fps, 보간 없음. Q는production60, S/D1/D3는studies30, A2는studies-final, D2/A1/E는studies-refined가 현재 프레임 출처다. 영상 전체 디코딩·브라우저9개 로딩·재생/.5배속·확대 보기를 확인했다. 기본 게임 반영과 임시 시안 채택 여부를 섞지 않는다. 원본 팩 저장·커밋·push 없음.

## 21. 10-22 Q 추가 감량 · 가로 A와 꼬리 · 단색 S · E/W 시안

- **실제 적용:** Q `HailVisualDensity=2.56/3`으로 직전 낙하량의1/3, 안개 없음/피해40 유지. A150cm/s·90피해·관통 유지, 원본 `R_Ability_Fast_Fire`를 A에만 사용해 가로 활 자세로 발사(.42/복귀.90). 210cm 다섯 갈래 꼬리를 교차 평면2개로 연결한 `M_SparrowGearWake`, 코어.70→.52. S8→40초, 새 opaque/unlit `M_SparrowArchonSilhouette`로 장비 텍스처 없는 단색 몸, `M_SparrowWingUnfurlAccent`12갈래가.8초만 펼쳐지고 원래 Serath 날개로 정착한다. D에 날개는 계속 없다.
- **S 참고 범위:** 공식 Blizzard Archon 설명은 순수 에너지 변신을 확인해 주지만 이전 작업이 공식 영상과 충실히 대조됐다는 근거는 없다. 이번은 사용자 요청의 단색 실루엣을 반영한 해석이며 원작 동일 외형 인증이 아니다.40초 만료 시16재질/망토 section 복원 확인.
- **E/W 미설치 시안:** `sparrow_ew_studies.py`는 E4 깃날/E5 나선/E6 결정 파편, W1 성창/W2 쌍날/W3 파편 탄두. 첫 E는 도형만 남아 원본 ArrowTrail·RapidFlow를 복구하고 도형 강도 절반으로 보완했다. 실제 E6가 가장 뚜렷하며 E4/E5 차이는 작다. W3는 원본 파편과 자연스럽고 W2는 문양 성격이 강하다. E최종=`refined60`, W=`ew30`. 기존 운영 E/W와 원본팩은 보존했다.
- **이동기 조사/시안:** `sparrow_mobility_studies.py`로 Sparrow Jump_Start_TravelMode/Knock_Bwd, Mannequin MM_Dash, Aurora Ability_RMB_Fwd를 맞는 원본 메시에서 실제 재생했다. 전용 구르기 신규 발견은 아니며 다른 스켈레톤2종은 리타게팅 필요. Knock_Bwd는 피격 반응이라 우선 추천하지 않는다. M5는 기존 자세의 단색 몸·압축·위치 이동·3잔상으로 만든 금빛 이동 시안이며 관절 구르기/게임 이동 판정/무적/키 바인딩은 설치하지 않았다. M1–4=`production30-v2`, M5최종=`refined60`.
- **D/R 평가만:** D의 스킬 복제 역할은 살리고 발동 신호/엇갈린 복제를 강화하는 쪽을 제안했다. R은 규칙적 격자와 큰 착탄광이 문제라 수 증가 대신 군집 편차/착탄 감량을 제안했다. 이번에 D/R 동작이나 외형 후보를 추가 설치하지 않았다.
- **검증/실패 구분:** DebugGame Editor18.14초/Development Editor/Development Game25.25초 성공. `production30`은 EW helper import 경로 오류로 PIE전 실패, 수정 후 `production30-v2`51검사 통과. 다만 A HLSL 예약어 `line` 때문에 회색 재질이 보여 시각 반려했다. `ew30`43검사 통과 중 E6도 같은 예약어 오류로 시각 반려. `strand`/`spineMask` 수정 후 `refined60`38검사와 실제 정상 화면 확인. A가로 활축 수직성분.093(30)/.084(60), 취소·복귀·150속도·90관통·소유자 종료정리 확인. 실패 실행/중간 이미지는 보존했다. 재저작 전에 옛 에셋을 여는 경고까지0이라고 주장하지 않는다.
- **전달/다음:** [비교 페이지](../../Saved/QA/CharacterPipeline/sparrow-reforge-20261022/preview.html), [결과](../../Saved/QA/CharacterPipeline/sparrow-reforge-20261022/result.json). 실제 영상13개(30/60fps) 전체 디코딩 및 브라우저 로딩·재생·반속·확대 확인. S대표는 `production30-v2/screenshots/S_solid_silhouette_unfurl_video_0023.png`. A/E6 초기 회색판 영상을 최종으로 사용하지 않는다. 사용자 채택 전 E/W/이동기를 자동 설치하지 않는다. 원본팩 저장·패키징·커밋·push 없음.


## 22. 10-22 이동 클릭 복구 · Q/W/R 발사 · A복원 · S/D · 새 이동4안

- **요청/범위:** 스킬 난타 뒤 이동이 안 되는 증상, Q 발사 효과, W 임팩트 유지한 보강, E 화려한 여러 안, R 활 쪽 보강, A 직전판 롤백+새 시안, S 은은한 불꽃 날개, D 이동 어색함, 이동 애니메이션 여러 개와 후퇴 동작 조사. 사용자 무인/서브에이전트 승인을 유지했다.
- **이동 원인/수정:** `KwangPlayerController::MoveToCursor`가 `IsCombatBusy`에서 커서 목표를 읽기 전에 반환해 짧은 우클릭이 소실됐다. Sparrow의 유효 내비 목표 한 개를 보관하고 후딜/종료 root-motion의 path-follow 제한이 풀리면 소비한다. 새 공격/성공한 새 스킬/입력flush/캐릭터전환에서 제거한다. 다른 직업은 기존 규칙이다. 진단 로그 `Character.Input.TraceMove`의 기본값은0이다.
- **이동 검증:** `move-before30`237개에서8종행동 모두0cm, 회복후 새클릭은 정상이라 영구busy는 재현되지 않았다. `move-after30`252개에서8종413–427cm 이동/16회난타/flush·전환, `move-after60`106개에서8종후딜·복귀·새클릭 통과. 실제42프레임 영상에서Q후딜뒤353cm 이동. 첫 `production30`의0cm 실패 원인은 미확인으로 보존하며 이후 통과로 덮지 않는다.
- **Q/W/R 실제:** 원본팩을 저장하지 않고 transient Sparks/Wisps를 짧은 발사 파편으로 재구성한다. Q 활 준비와 위로 발사하는 순간을 보강하되 낙하2.56/3·피해40·안개없음 유지. W 고리.14초/후딜.10초 유지+짧은 전방 파편. R186발/6회/60피해 유지+활불꽃·파동별파편. 새운영재질 `M_SparrowReleaseWisps`는 원본SubUV.A형태/R명암을 사용한다.
- **A 실제 롤백:** §21의가로발사·210cm교차꼬리를 철회했다. 기존Primary 자세·220cm/s·core.70·피해90·관통을 복구했다. 발사.42/복귀.90은 유지. 실제 활축 수직성분.9992, 속도219.99999, 거절된Wake컴포넌트없음을 확인했다.
- **S/D 실제:** S단색몸/40초/망토복원/Serath날개형태는 유지하며 `M_SparrowWingFlame`6개가 원본날개뼈를 따라 느리게 흐르고 불티가 뜬다. 전개직선광 강도55%로 낮춤. D는 이동방향으로대형90도/s회전, offset감쇠/지면·벽보정, 본체평행이동즉시복제. 정지조준180도에대형이도는현상 제거. 천시뮬이없어굳던분신망토/끈3·7만숨김. 본체천·10초·30%실제스킬복제·분신무날개 유지. `trace-and-forms30` 실제우클릭두구간·급회전·W복제·S소유자정리 통과.
- **E/A 미설치:** `sparrow_fresh_studies.py` E7황금깃불/E8백금가속/E9곡면파편, A3층상절삭불꽃/A4나선파편/A5백금꼬리. 시안A만Core.36으로낮춰꼬리를드러낸다. E6발·A90피해·cleanup실검사. 최종영상 출처는 `delivery-clips.json`이다. E9=`studies30`, A4=`refined30`은 해당분기와재질이후수정영향없어재사용했다. 사용자미적선택은미결이다.
- **새 이동 애니메이션:** `Previews/Fresh20261022/AS_Sparrow_M6..M9_MobilityStudy`4개. 각165본을같은스켈레톤원본포즈로리샘플·보간했다. 전진도약340/측면회피280/후방도약270/지면백스텝220cm, 실제위치곡선과금빛잔상. 스킬키·충돌·무적·리타게팅은설치안함. SparrowJog_Bwd_Start/Stop같은스켈레톤, AuroraRMB_Bwd/BwdLeft/BwdRight1.933초는다른스켈레톤임을실제로드로확인했다.
- **시각 실패/해결:** Wisps확대시사각형→새재질RGBmax마스크로구슬이되어둘다반려. 원본T_Plasma_Wisps읽기전용export와실제재질그래프에서opacity=SubUV.A확정. B가대부분최대값이므로RGBmax를opacity로쓰면안된다. A형태/R명암으로고친`alpha-check30`Q/E7과`final30`W/R/E8/A3/A5가최종이다. 초기실패영상은남겼으나전달페이지에서사용안함.
- **빌드/전달:** DebugGameEditor6.58초와DevelopmentGame31.83초성공. 열린사용자에디터PID39888/DevelopmentDLL을건드리지않았다. 새게임은 `Play-CurrentSkills.cmd`로확인한다. 로컬서버127.0.0.1:55811재시작. 실제17영상전체디코딩/브라우저readyState4·오류0·재생/반속/확대확인. [비교페이지](../../Saved/QA/CharacterPipeline/sparrow-finish-20261022/preview.html), [최종기록](../../Saved/QA/CharacterPipeline/sparrow-finish-20261022/result.json). 원본팩저장·패키징·성능계측·커밋·push없음.


## 23. 10-23 R 끝맺음 · S 에너지 날개 · D 1인 · Space M9/W 인계 · E7/E9 정제

- **실제 적용 R:** 마지막 회차의 활 Wisps를 제거하고 짧은 Sparks만 사용한다. R 착탄 전용 transient는 Main Flames/Light를 빼고 .10–.18초 Flare/Wisps/Sparks만 남긴다. 186발/6회/총60피해는 유지. `SparrowArrow.cpp`, `SparrowShotWave.cpp`, `FireMultishotWave` 참조.
- **실제 적용 S:** 기존 Serath 깃털 메시를 숨기고 6개 불꽃판 경로를 제거했다. 전용 `SM_SparrowEnergyWings`/`M_SparrowEnergyWings`를 새로 저작했다. 긴 곡선14줄+끝갈라짐14개/2576tri, Fire.r/g를 쓰는 백금 코어·황금 불꽃. 첫 가는 철사 같은 결과는 반려하고 폭12→30cm계열/코어.72→.23/화염sheath.38→.92로 보완했다. 실제 최종 형태는 `integration-final30/screenshots/S_energy_hold.png`. 단색 몸/망토 제거/40초/기존재질·section 복원 유지. 원작과 동일 외형이라는 인증은 아니다.
- **실제 적용 D:** 양옆2명→뒤135cm의1명으로 변경. 벽이 있으면95/55cm로 축소한다. 10초/각30%스킬복제/무날개 유지. 따라서 복제 최대피해는 이전2×30%에서1×30%로 줄었다. 정지 큰 조준 회전은 뒤로 즉시 재배치+.14초 dissolve로 원주 미끄러짐을 줄인다. 실제 우클릭 이동·W복제를 확인했다.
- **실제 적용 Space:** `SparrowBackstepEcho`와 `SparrowSkillComponentBackstep.cpp` 추가. 기존 컨트롤러 slot17 바인딩을 사용한다. M9/.60초/목표220cm, 실제 몽타주 blend 종료까지212.455cm. 출발점에1.10초 분신을 고정하며 W 발사 전이면 남은 ActionTimer 시각에 원래W 한 발만 인계한다. 이미 발사했으면 추가 발사 없음. 다른 준비 시전은 취소하고 백스텝 우선. 이동 중 새 스킬 거부, 벽 sweep/지면·nav 검사, root-motion/회전 복원,6초 쿨타임. D 파트너와 별개이며 소유자 종료 때 지연W·효과·이동상태를 정리한다. 피해/무적 추가는 없다.
- **E7/E9는 시안만:** `sparrow_e_refinement.py`. E7=3단 발사 깃불/두 줄 주 불꽃/방향성착탄, E9=정돈한3곡면편/발사파편. v1은 과도한 감량으로 비어보여 반려, v2 E7은 새 재질의 낮은alpha 증폭·수명침식 누락으로 구름처럼 뭉쳐 반려했다. 최종 E7 주층만 원본 `M_Plasma_v5_Flipbook2` transientMID/Param0으로 바꾸고 크기·수명을 유지했다. E9 최종은v2. 운영 E/공유재질/원본팩은 변경하지 않았다.
- **검증:** `backstep60`115개 passed(실제키 idle/W준비/W발사후/6초쿨타임), `integration-final30` 일반 DevelopmentEditor65개 passed(D이동·복제/S생성·복원/E7피해·정리/W인계·이동복귀), `backstep-dev30`35개 passed. `backstep30` 첫7케이스138개 통과 범위로 벽67.60cm/Q준비취소/D공존/전환정리를 재사용한다. 해당run전체는 마지막 cooldown getter Python미노출로 failed 유지. R9검사는 `integration30`, E9 11검사는 `e30-v2`의 변경없는 분기를 재사용했다.
- **실패 구분:** S 첫 검사는 생성프레임/첫Tick 전 가시성 경합, 다음은 Python미노출 getter였다. false→true 한Tick 및 엔진노출 component 조회로 고쳤다. `visual-final30`은 새에셋 저작과 S/E 뒤 Space1회거부가 있었으나 당시 feedback미기록으로 원인미확정이다. 일반모듈 단독35개와 동일 S/E/Space순서의 새세션65개는 이후정상이다. 검증실패를 덮어쓰거나 게임결함/환경원인을 추정확정하지 않는다.
- **빌드/전달:** DebugGameEditor7.39초/DevelopmentEditor24.21초/Game30.34초 성공. 당시 열린 UnrealEditor가없음을 확인한뒤 일반모듈도 갱신했다. 실제영상8개/30fps/전체디코딩, 브라우저8개readyState4/오류0/재생·반속·확대·overflow없음 확인. [새 비교페이지](../../Saved/QA/CharacterPipeline/sparrow-partner-20261023/preview.html), [기록](../../Saved/QA/CharacterPipeline/sparrow-partner-20261023/result.json). 실행은 `Play-CurrentSkills.cmd`→숫자2, 이동기는Space. 원본팩저장/패키징/성능계측/커밋/push없음. 사용자 미적채택은 아직 미결이다.


## 24. 10-23 황금 천사 날개 재해석 · 붙는 그림자 · 순간 백스텝 · R 섬광을 A로 이동

- **참고 수정:** 사용자가 뼈/캐리건 같은 형태를 명백히 거부했다. Blizzard 공식 `Wings of Valor Now Available`의 GIF 33프레임 중0/11/22를 직접 보고 넓은 황금 화염/밝은 어깨 뿌리/흩어지는 가장자리로 다시 해석했다. 공식 URL은 https://news.blizzard.com/en-gb/article/13407835/wings-of-valor-now-available . GIF는 QA 참고자료일 뿐 게임 에셋으로 가져오지 않았다.
- **S 실제:** 14갈고리와 물리fork를 버리고 좌우3개씩 넓은 곡면 화염띠(6144tri)로 다시 저작. 첫 화면은 교차면/HDR 중첩으로 너무 하얘 반려했다. 재질r2는 alpha28% 감소, 황금색 몸통과 제한된 whitehot 뿌리/열점을 분리했다. 원본Serath 숨김·단색 몸·망토 제거·40초·기존재질/section 복원 유지. 실제 최종은 `forms-fast30-v2/screenshots/S_energy_hold.png`. 사용자 미적 승인은 미결이다.
- **D 실제:** 뒤135cm→45cm/측6cm. 본체와 같은 포즈/회전을 즉시 따라가는 반투명 단색 `M_SparrowShadowPartner`를 새로 추가했다. 공유Echo Visibility는 dissolve도 겸하므로 덮어쓰지 않았다. 독립 대형 yaw/보간/재배치 fade/별도 지면높이를 제거했다.1명/10초/30%스킬복제/날개 없음 유지.
- **Space 실제:** 이동.60→.16초, 몽타주도 약.20초로 함께 압축하고 blend .012/.025초. 첫 순간에 크게 이동하는 감속 곡선과 출발점 짧은 파편. 실제30/60fps 모두220cm. W 남은 발사 타이머는 배속과 독립이며 발사 전이면 원래 한 발만 출발점 분신이 인계한다. 벽 sweep/지면/nav/6초 쿨타임/취소·root-motion/회전 복원을 유지한다. Native 안전조건을 완화하지 않았다.
- **W 실제:** 준비 중 작은 BowFlames/Embers를 활에 부착하고, 발사 때 양옆11도에 짧은 깃파편을 추가했다. 인계 W도 `ReleasePiercingShot`을 공유하므로 분신 위치에서 같은 효과가 난다.35피해·발사후.10초 잠금·기존 짧은 고리 유지.
- **R/A 실제:** R target/world 착탄 모두 Sparks만 남기고 넓은 원본fallback도 제거. R의 PrimaryMuzzle 호출도 없앴다. 제거한 Flare는 A 명중점에서 원래R.65의2/3=.4333333 크기로0/.055/.11초3회 재생한다. `ASparrowTransferredHitFlash`는.35초 수명, 투사체가 사라져도 마무리하고 본체종료에는 즉시 정리한다. R186발/6회/60, A220cm/s/90/관통 유지. 섬광은 추가피해가 없다.
- **E는 미채택 시안:** E10은 활 앞 축소 황금날개 익궁, E11은 좁고 앞쪽으로 모이는6핀/층상 불꽃. revision4의 E11 흰 구름과 revision5 E10의 큰 흐린 비행층을 시각 반려했다. 최종 E10 revision7은 원본 침식 불꽃 MID/폭1.05/반복큰Wisps 제거. E11은revision5 조형 그대로이며 같은 원본 침식재질을 쓴다. 임시 메시/MID만 만들고 운영 E는 교체하지 않았다. 원본SubUV.A/수명침식 유지, 실제6발·피해·정리를 검사한다.
- **검증 범위:** `hits-e-fast30`181passed(R/A/Space3경우; E옛안은 기능만 통과하고 시각 반려). `nav-sequence30`72passed(저작없이 S/D→W→Space 동일순서). 일반 DevelopmentEditor `backstep-dev60`172passed(7경우: idle/W준비/W발사후/벽70cm/Q취소/D공존/소유자교체). S/D/W 최종 영상은 `forms-fast30-v2`의 통과한 해당case만 쓰며 run전체를 통과라고 부르지 않는다. E11 최종은 `e-final30`25passed 중 변경없는 E11분기, E10은 `e-order30`25passed의후속E10분기 참조. E11은 `e-final30`의후속E11분기다.
- **실패 보존:** `forms-fast30`과v2는 새 S메시/재질 저작을 동반한 세션에서 Space 거부. v2로그는 바닥정상/목적지(-220,-400,96.15)/`ProjectPointToNavigation=false`를 확인했다. 재저작 없는 같은순서는 정상이며 근본원인은 미확정이다. 임의로 일시적nav재빌드/이동잠금 결함이라고 단정하지 않는다. 실제키 거부사유와좌표 로그를 유지했고 안전조건은 그대로다.
- **빌드/전달:** DebugGameEditor21.69초+진단6.72초, DevelopmentEditor18.15초, DevelopmentGame26.89초 성공. 직접 실행은 `Play-CurrentSkills.cmd`→숫자2, Space. 최종영상별출처는 `sparrow-gold-revision-20261023/delivery-clips.json`, 검증은 `result.json`, 페이지는 http://127.0.0.1:55811/sparrow-gold-revision-20261023/preview.html . 원본팩 저장·패키징·성능계측·커밋·push 없음.

- **최종 미디어/첫시전 관찰:** 실제영상9개/30fps/전부전체디코딩, 브라우저9개readyState4·오류0·재생/반속/확대·단일재생·가로overflow없음 확인. 첫 E의흐린후류는실행순서를뒤집으면먼저시전한안에서나타났고후속시전은선명했다. 원본침식재질을쓰되최종E비교영상은양쪽모두1회시전뒤촬영했고, 로딩/렌더의근본원인은계측하지않아미확정이다. 큰Wisps감량만으로모든흐림이해결됐다고주장하지않는다. HTTP서버가닫혀31532로127.0.0.1:55811에재시작했으며최신페이지탭을남겼다.


## 25. 10-23 원본 S 형태 복원 · R 착탄 복구 · W/A 가독성 · Space 잔상

- **사용자 교정:** 새6개 황금띠 날개는 반려. 기존 날개 형상을 롤백하고 최근 황금 불꽃 질감만 적용한다. D는 의견/시안, W는 실제로 읽히는 차이, R은 큰 섬광만 빼고 원래 착탄과 활 발광 복구, A는 비행체 개선, Space는 짧은 금빛 잔상을 요청했다. E10/E11도 반려했다.
- **S 실제:** 기존 Serath skeletal mesh·Unfold/Idle·재질12/13을 복구했다. spline 원본은 gold MID, membrane은 원본 재질을 새 `M_SparrowSerathGoldFlame`으로 복제해 opacity/WPO 그래프를 보존하고 emissive만 흐르는 금빛 Fire.r/g로 교체한다. 원본 메시/재질3파일 저작 전후 해시 동일. 새 에너지띠 생성 경로는 제거했으며 기존 파일은 보존했다. 단색 몸/망토 제거/40초/원래 재질·section 복원 유지. `sparrow_serath_flame.py`를 사용하고 `sparrow_energy_partner.py` author는 실행하지 않는다.
- **W 실제:** 기존 작은 준비 불티/짧은 고리만으로는 차이가 약했다. `ASparrowArrow::EnableChargedAura`가 원본 `P_Sparrow_UltArrow`의 MeshCoronaLarge/SparksTrailing을 transient 복제한다. 원본 Aura mesh·MeshMaterial override·DynamicParameter·색을 함께 유지하고 불티수명만.12초. PSC축척(1.5,.8,.8), 활 앞 추가발광. 분신 W도 공유 발사 경로를 사용한다.35피해·발사 후 잠금.10초·속도/판정 유지.
- **R 실제:** Sparks만 남겼던 과도한 삭제를 철회했다. Main Flames/Wisps/Sparks/SparkTrailHeads/Line Burst 복구, Flare/AddFlare/LightsOnly·ParticleLight만 제외한다. 착탄.65축척/.24초 정리·수명.12~.20. 각 파동 활 앞 MuzzleGlow/Airglow/Wisps/Sparks 복구.186발/6파동/60피해 유지. A의3연속Flare는 그대로 둔다.
- **A 실제:** 중심 노란 구체가 회전 날을 가리는 실제 화면을 확인했다. CondensedCore .70→.24, 두 번째깃고리 Envelope .32→.46. 기존 UltimateTrail 안에 이미 Aura/Sparks가 있어 새 PSC는 중복 추가하지 않았다.220cm/s/90피해/외경/회전속도/3연속착탄 유지.
- **Space 실제:** 기존.16초/220cm 후퇴 중25/50/75% 실제 안전 이동경로에3개 pose snapshot을 남겨.22초 제곱 fade한다. 충돌/내비/회전·root-motion 복원/원점1.10초 분신/예정 W 한 발/6초 쿨타임은 유지. 위치 snapshot이므로 벽 뒤에 잔상을 만들지 않는다. 새 피해/복제 공격은 없다.
- **D 시안:** 생산 D는 바꾸지 않았다. 새 `M_SparrowDShadowStudy`를 실제 한 명 분신에 study MID로만 적용한다. D1은 평소alpha.018·실제 echo 때.28초 금빛 윤곽. D2는 허리 아래fade·상반신 영체. D1 첫 대표PNG는 pulse 직전 렌더라 실제2프레임 뒤video_0027을 선택한다. D2 첫판은 금색 채움 덩어리로 반려하고 fill.065/rim.32/몸 backface 제외로 재촬영한다. native pointer가 갱신하는 MID와 시안 MID는 분리하며 소유자 전환에서 정리한다.
- **E 시안:** `sparrow_e_recast.py`는 새 도형/안개 대신 원본 금색 Aura와 SparksTrailing의 완성된 재질 체인을 재사용한다. native8개 자산 감사는 성공했으나 첫 cross-pack Python ObjectIterator의 class wrapper에서 TypeError가 난 기록은 보존했다. class wrapper skip으로 수정했고 추가 전체 감사는 하지 않았다. flow30 첫 안의1.05폭은 너무 가늘어 시각 반려, 횡폭/활발사 리듬을 보강해 재촬영한다. 운영 E는 교체하지 않았다.
- **현재 통과 근거:** `sparrow-texture-restore-20261023/visual30`74개(S/D시안/W/R/A), `flow30`165개(E첫안6발/피해·Space5경우), 일반DevelopmentEditor `backstep60`100개(잔상/W인계/전환정리). DebugGameEditor는 S의 raw pointer/TObjectPtr 조건식 C2445 한 건을 `.Get()`으로 수정한 뒤6.86초 성공. DevelopmentEditor18.05초/Game28.98초 성공. 모든 통과는 미적채택과 구분한다.

- **최종 E/D2·전달:** 일반DevelopmentEditor `final30`22개 passed. D2는fill.065/rim.32/몸backface 제외로금색채움중첩을낮췄다. E revision2는 비행X1.05/YZ1.89(횡폭1.8배)와 실제6발마다 같은원본외피의.14초활앞맥동6개를넣었다. 원본mesh/ParticleModuleMeshMaterial/DP4개/gold색을유지하고짧은PSC는정리한다. 실제6발/기존passive포함62.625피해/복귀·cleanup통과. 이는새비교안이며운영E는교체하지않았다.
- **전달 완료:** [실제9영상](../../Saved/QA/CharacterPipeline/sparrow-texture-restore-20261023/preview.html), [기록](../../Saved/QA/CharacterPipeline/sparrow-texture-restore-20261023/result.json). 모든영상원본1280×720/30fps/연속프레임·전체디코딩통과. 브라우저9개readyState4/오류0/반속·확대재생·동시1개·가로overflow없음확인. 서버127.0.0.1:55811과기존tab2를유지했다. S/W/R/A/Space는적용,D/E는시안. Play-CurrentSkills.cmd→숫자2. 패키징·성능계측·커밋·push없음. 미적채택은사용자판단대기이다.


## 26. 10-23 S 화염 강화·부드러운 시전 / W 강한 방출 / A6~A8 새 시안

- **요청:** 사용자가 원본형 S를 수용하고 더 타오르는 질감과 부드러운 시전을 요청했다. W는 강렬함 부족, A는 다시 시안을 요청했다. E/D/R/Space 디자인은 이 묶음에서 변경하지 않는다.
- **S 실제:** `M_SparrowSerathGoldFlame`의 Fire.r/g 흐름.30→.68, UV뒤틀림·열점대비를 보강하고 넓은 균일 발광보다 어두운 골/밝은 화염결을 분리했다. 원본 Serath 형상·opacity/WPO는 유지한다. 시전 Action.45→.52/Recovery.90→1.35초, S 몽타주 blend .16/.24초, 날개Unfold.8배·Idle전환타이머도동일배속보정, 진입opacity.24→.55초. 기존 저장 BP의 S정의도 CreateExtraMontages에서 같은 값으로 동기화한다. 다른스킬몽타주/공통피해는 유지한다.40초 변신/망토·재질복원 유지.
- **W 실제:** 메시폭2→2.6/AuraYZ.8→1.85, 원본축재질190cm의짧은두가닥. 열린고리.14초수명은유지하고1.65→3.15팽창·740cm/s전방방출로대비를 키웠다. pressure Wisps는더작고짧게. 첫실제촬영에 남은큰구름은 PrimaryMuzzle와 GetMultishotBowGlow의 Wisps중복이었다. W전용 GetPiercingMuzzle은 MuzzleGlow/Airglow/Sparks/작은MuzzleFlare만남기고 두호출을.14초/.85 한 번으로대체한다. R의활발광함수/착탄/A3파열은그대로.35피해/4000속도/.10후딜/Space인수는공유ReleasePiercingShot경로유지.
- **A 미적용 시안:** `sparrow_a_revisions.py`와 전용 preview재질1개. A6=12금속광륜톱, A7=4갈래교차절삭날, A8=원본액체Aura핵+찢긴화염꼬리. 실제A의1발/220cm/s/90피해/관통/기존3연속착탄을유지하고외형만잠시교체한다. 첫A6/7의큰노란면은시각반려하여어두운청동면/금색bevel/white razor를분리했다. A8초안의핵은원본.55초수명후사라져시각반려, .30초마다원본Aura를교대생성/.55초수명·최대2개로유지한다. 임시PSC와컴포넌트override는시안종료/소유자전환에서복구한다.
- **첫검증:** `sparrow-fire-forge-20261023/visual30`50개 passed. 이run의 S는새화염·1.35초몽타주·실제S후딜우클릭큐이동·재질/망토복원·전환정리 통과로 최종영상 재사용. W/A는기능통과지만외형반려였으므로최종영상에사용하지않는다. DebugGameEditor7.04초, W구름교정후DebugGameEditor12.55초/DevelopmentEditor12.19초 성공. 최종W/A 촬영과통합Game빌드는아래에추가한다.

- **최종검증/전달:** 일반DevelopmentEditor `final30`32개 passed(W35피해·복귀/세A1발·220·90·복구·정리), `smooth60`의S시전·실제우클릭복귀/원본형·재질복원 검사통과. Game24.82초 성공. S는 첫실제촬영을재사용하고 W/A만재촬영했다. [최종5영상](../../Saved/QA/CharacterPipeline/sparrow-fire-forge-20261023/preview.html), [범위·검사기록](../../Saved/QA/CharacterPipeline/sparrow-fire-forge-20261023/result.json). 원본1280×720/30fps 연속실제프레임만 인코딩·전체디코딩. S/W적용,A6~A8시안. 미적승인은사용자판단대기이며원본팩저장·패키징·커밋·push없음.
- **브라우저:** 최종5영상모두readyState4/오류0/원본1280×720/가로overflow없음 확인, 기존tab2를새페이지로열어deliverable로유지했다. 재생·반속·확대·단일재생코드는직전검증판과동일하므로변경없는컨트롤회귀는반복하지않았다. S60검사는19개passed.


## 27. 10-23 날개 표면 자체의 화염 · W 얇은 투사체 복구 · A6/A8 혼합

- **사용자 교정:** S가덧댄이펙트처럼보인다고다시거부했다. 고정에셋이라불가능한지질문했고 W는얇게크기롤백, A6/A8느낌을합친시안을요청했다.
- **S 실제:** 이전막은원래opacity의94~100%를유지했고spline12는고정gold여서표면무늬인상이남았다. 이제막13과골격12를각각원본에서복제한두전용재질로직접불꽃화한다. 두표면은 root+caster Side/BackAxis 상대의같은상승Fire장을사용하며원래opacity는지원mask로만쓰고불꽃이4~96%coverage를결정한다. 원본메시/WPO·1.35시전/.8Unfold/40초/몸·망토복원을유지한다. S입장에덧붙이던별도P_Sparrow_Burst plasma/flame PSC호출은제거했다. D/A의공유accent는보존. 원본S메시/재질3파일저작전후해시같음.
- **W 실제:** 메시폭2.6→2.0, Aura(1.65,1.85,1.85)→(1.5,.8,.8), 양옆190cm보조두가닥생성제거. 최근발사압력/짧은고리/단일muzzle는유지한다.35피해/4000속도/.10후딜과Space원점인계경로유지.
- **A9 미적용:** A6금속톱외곽·명암을유지하고안쪽에A8느낌의흐르는황금핵과짧은Flames2꼬리를합쳤다. sourceAura핵을작게/크게/앞쪽정렬해도희미한초안은모두보존했다. 원본MeshCoronaLarge가LOD1~3에서꺼지는사실은확인했지만강제LOD0만으로도원인이확정되지않아LOD문제라고단정하지않는다. 최종은기존Rotor표면에FireTexture로깊이명암·흐름을가진핵을직접통합하고A9의추가corePSC는만들지않는다. A6/A7의Hybrid기본값은0, A9앞고리만1. 꼬리는원본Flames2/.20초·.16간격. 실제220/90/관통/기존3연착탄·생산A보존.
- **검증/빌드:** visual30의S/W/A9기능34개passed. A9이후짧은4개수정run각9개passed이지만핵이희미한이전영상은전달에서제외했다. 최종A9는a9-kernel30. DebugGameEditor12.84초, Game21.55초, DevelopmentEditor13.61초 성공. 초기사용자에디터39628은건드리지않았고이후프로세스없음을확인한후일반에디터DLL도갱신했다. 시전·판정은변경하지않아이번재질/크기튜닝은짧은30fps실제화면범위로검사했다.
- **전달:** [실제3영상](../../Saved/QA/CharacterPipeline/sparrow-native-flame-20261023/preview.html), [적용·시안·검사기록](../../Saved/QA/CharacterPipeline/sparrow-native-flame-20261023/result.json). S/W는visual30, A9는a9-kernel30만최종으로사용한다. 미적채택은사용자판단대기. 원본팩저장·패키징·성능계측·커밋·push없음.
- **최종브라우저:** 실제3영상연속프레임인코딩/전체디코딩, 브라우저3개readyState4·오류0·원본1280×720·가로overflow없음. 기존tab2를새페이지에유지하고deliverable로표시했다. 검증된플레이어코드유지.

## 28. 10-23 미리보기 검은 영상 수정 · 임시 캡처 정리

- **실제 문제:** 사용자가 영상이 보이지 않는다고 보고했다. MP4는 readyState4·오류0·재생 시간 증가에도 IAB 화면이 검게 나왔다. 메타데이터 확인만으로 실제 화면 출력을 검증했다고 볼 수 없었다.
- **수정/확인:** 같은 실제 캡처를 VP9/WebM·yuv420p로 인코딩하고 카드에서 우선 사용한다. MP4는 보존용/대체 소스로 유지한다. S/W/A9 모두 실제 화면 출력과 재생을 확인했고 W 확대·반속·닫기와 단일 재생도 확인했다. 재생 Promise 거부를 조용히 삼키지 않고 안내를 표시한다. 게임 코드와 에셋은 이번에 변경하지 않았다.
- **정리:** 사용자 요청으로 이 작업에서 만든 번호형 임시 PNG 9,823개, 18,481,845,679바이트(17.21GiB)를 삭제했다. 각 시퀀스 첫/중간/마지막, 문서·코드·페이지에 명시된 개별 파일, 최종 영상·대표 이미지·로그·QA JSON은 보존했다. 대상과 실행 후 잔여0은 최신 QA의 `cleanup-plan.json`/`cleanup-result.json`에 기록했다. 이제 정리한 연속 PNG 전체는 남아 있지 않으며, 완료 영상이 보존본이다.
- **이후 운영:** 각 묶음에서 최종 영상 인코딩·전체 디코딩·실제 브라우저 화면 출력을 확인한 뒤 재사용하지 않을 연속 캡처와 실패한 변환 임시 파일을 바로 정리한다. 게임 적용 파일·원본 에셋·현재 전달 영상은 정리 대상에 넣지 않는다.

## 29. 10-23 W 착탄 파열 · S 밀도/일렁임 · A 감속

- **요청/영향:** W는 얇은 투사체를 유지하며 폭발 보강, S는 현재 방향에서 일렁임/밀도 보강, A는 추가 감속, 구르기 조사 상태 확인. W 착탄은 `SparrowArrow.cpp`의 전용 transient 복제본만 사용해 R/평타/원본 팩을 보존한다. S 저작은 소유 재질 두 개, A는 공유 GearSpeed만 변경한다.
- **W 실제:** 원본 UltHit의 Main Flames/메시·DP·Wisps/불티/선형 파열을 보존한 6층 복제본. 작은 Flare 핵은.055~.075초, 화염은.025초 뒤6개와.045초 간격3개, .22~.34초 수명으로 퍼진다. 얇은 화살/35피해/4000속도/.10후딜 유지. 착탄 컴포넌트는.58초에 정리. 큰 추가 Flare와 ParticleLight 제외. 실제 촬영에서 금빛 화염과 선형 파편 확인.
- **S 실제:** `sparrow_serath_flame.py`가 root 상대 Fire장의 큰 호흡/잔물결과 coverage.12~.98을 두 원본형 표면에 적용한다. 원본 WPO 입력은 보존하고 소유 Custom 하나로 뿌리24~130cm anchor, 뒤축 최대1.6cm/상하.6cm 일렁임만 더한다. 두 번 저작해 노드 중복 없이 성공. 형상/전개/1.35시전/40초/망토·재질 복원 유지. 별도 판/파티클 추가 없음. 실제 hold에서 불꽃 밀도와 접합부 확인.
- **A 실제:** GearSpeed220→160cm/s(약27.3% 감속),90피해/관통/외형/3연착탄 유지. A9 영상도 같은 실제 속도지만 외형 채택은 여전히 미결. `sparrow_a_revisions.py`의 관찰 시간을3.6초로 늘려 늦어진 명중까지 확인한다.
- **구르기:** 기존 `sparrow-feedback-20261022/production60/sparrow-dodge-audit.json`의 실제 애니메이션/스켈레톤/길이 조사와 현재 파일명 확인을 대조했다. 현 프로젝트에서 전용 구르기로 확인된 것은 없다. MM_Dash/AuroraRMB 회피 후보는 다른 스켈레톤이며 리타게팅 필요. Space는 기존 M9/.16초 백스텝+금빛 잔상이다. 새 구르기 설치는 이번에 하지 않았다.
- **검증:** `visual30`의 S13개 통과, 전체 run은 W 검사 범위 오류1건으로 실패 상태 보존. HasImpactLightModules가 실제 W 표적효과뿐 아니라 사용하지 않는 기존 벽 충돌효과의 광원도 검사했다. 해당 검사를 바로잡고 변경 없는 S는 재촬영하지 않았다. `final30`의 W/A19개 통과(실제 W 복제본/35피해/효과 정리, A160/90/관통/시안 복구). DebugGameEditor10.33초, DevelopmentEditor12.79초, Game21.05초 성공. 사용자 에디터 강제 종료 없음.
- **전달:** [실제3영상](../../Saved/QA/CharacterPipeline/sparrow-impact-flow-20261023/preview.html), [기록](../../Saved/QA/CharacterPipeline/sparrow-impact-flow-20261023/result.json). S=visual30, W/A=final30. VP9/WebM 우선·MP4 보존, 전체 디코딩과 브라우저3개 실제 화면 출력/재생·오류0 확인. 검토 완료 연속 PNG는 대표/이름 있는 캡처만 남겨 정리했고 바이트는 cleanup-result.json에 기록. 미적 채택은 사용자 판단 대기. 패키징/성능계측/커밋/push 없음.

## 30. 10-23 무료 구르기 외부 에셋 조사

- 사용자가 다른 캐릭터 메시+원래 구르기 애니메이션을 금빛 실루엣으로 잠시 보여주는 방식을 제안했고, 보유/파라곤/무료 외부 에셋 조사를 요청했다. 원래 스켈레톤의 시각용 대역이면 Sparrow로의 리타게팅은 생략할 수 있다. 현재 프로젝트 안 전용 구르기 확인 없음과 외부 무료 구르기 존재 여부는 구분한다.
- **확인된 1순위:** [Quaternius Universal Animation Library 1](https://quaternius.itch.io/universal-animation-library). 공식 [애니메이션 뷰어](https://quaternius.com/animviewer.html)에서 Roll 검색 후 `Roll`, `Roll_RM` 양쪽의 Standard 표시를 직접 확인했고 Roll을 눌러 몸을 접는 실제 구르기 포즈를 보았다. 무료 Standard ZIP15MB, CC0는 공식 배포 페이지에서 확인. 전체120+가 모두 무료라고 보고하지 않는다. 원래 마네킹과 함께 금빛 대역으로 쓰는 방식에 맞는 후보이다.
- **대안:** [voxel vision Free Animation Library / Fab](https://www.fab.com/listings/481ef75b-892b-424f-a213-f1cc058c9c19). 공식 구성에 Roll1개·UE 형식 명시, Fab 공식 카테고리에서 From Free. 다운로드 후 내용/재생은 아직 검증하지 않았다. Twinblast 무료 팩도 찾았지만 실제 Roll 포함은 확인하지 못했으므로 확정 후보로 추천하지 않았다.
- **상태/근거:** `sparrow-roll-research-20261023/result.json` 및 공식 뷰어 캡처. 외부 에셋 다운로드·프로젝트 설치·Space 변경·빌드는 이번 조사에서 하지 않았다. 취소한 Game Animation Sample 실험은 건드리지 않았다.

## 31. 10-23 Quaternius 원본 Roll · 황금 실루엣 Space 실제 적용

- **요청/영향:** 사용자가 §30의 1번 무료 Roll을 가져와 황금 실루엣으로 적용하고, 출발점 분신/W 이어쏘기를 보존하며 실제 게임 영상을 요청했다. 이동·충돌을 바꾸지 않고 `SparrowBackstepEcho`의 시각용 대역만 추가했다. `SparrowSkillComponentBackstep.cpp`의 이동 경로와 W 발사 인계 로직은 그대로다.
- **원본/설치:** 공식 Quaternius Universal Animation Library Standard의 CC0 원본을 받았다. `quaternius_roll_import.py`가 GLB에서 Roll 이외 애니메이션과 참조 없는 버퍼만 제외하며 원래 메시/스킨/샘플을 유지한다. 원본 Roll 1.4666667초와 일치하는 마네킹을 `/Game/TopDown/Characters/Sparrow/Mobility/Quaternius`에 설치했다. Sparrow 리타게팅은 하지 않았다. 보존 소스는 `SourceAssets/Quaternius/Roll/Quaternius_Roll.glb` 777,700바이트와 라이선스/출처이며, 설치 6uasset 합계 2,530,626바이트다. 임시 ZIP/전체 애니메이션 GLB는 성공 뒤 삭제했다.
- **실제 표현:** 충돌 없는 `SparrowGoldRoll` skeletal component에 원래 Roll을 재생하고 기존 `M_SparrowArchonSilhouette`/BodyTint(1.35,.85,.10)로 전체 슬롯을 황금색으로 만든다. 캡슐 높이의90%에 맞추고 후퇴 방향으로 향한다. 실제 이동 진행률에 원본 클립 시간을 맞추며 root motion은 이동에 쓰지 않는다. 구르는 동안 본체와 소유 S 날개를 숨기고 종료/벽충돌/owner 종료의 같은 경로에서 원래 가시성을 복원한다. 이동 잔상3개도 실제 구르기 포즈를 복사한다.
- **보존:** .16초/220cm/6초 쿨타임, sweep/지면/nav, 이동·회전 복원, 출발점 Sparrow 분신1.10초를 유지한다. 준비 중 W만 남은 원래 시각에 분신이1발 인계하고, 이미 발사한 W는 추가0발이다. W35피해·D 공존·S40초와 기존 망토/재질 복원도 유지. 무적이나 추가피해는 넣지 않았다.
- **검증:** `final30` 전체9case330개 통과(idle/W준비/W발사후/S/벽/Q취소/D공존/교체정리/쿨타임), `final60` 관련4case260개 통과. 벽 앞70cm 정지, 평지220cm, 구르기 뒤 실제 이동 입력 복귀, S의 같은 날개 actor/재질/section 복원 확인. `visual30`은 Python CurrentAsset 미노출로 중단된 실패 기록을 보존했고, 읽기 전용 native `GetRollAnimation()`을 추가한 뒤 두 최종 run에서 실제 바인딩과 재생 위치까지 확인했다. 중간 getter const 빌드 오류도 수정 후 통과했다.
- **빌드/전달:** 최종 DebugGameEditor6.13초, DevelopmentEditor12.43초, DevelopmentGame22.45초 성공. [실제60fps 영상4개](../../Saved/QA/CharacterPipeline/sparrow-gold-roll-20261023/preview.html), [결과](../../Saved/QA/CharacterPipeline/sparrow-gold-roll-20261023/result.json). 모든 영상 전체 디코딩과 브라우저 실제 출력/시간 진행·오류0·반속/확대·단일 재생을 확인했다. .16초 동작은 반속 버튼으로도 볼 수 있다. 실행은 `Play-CurrentSkills.cmd`→숫자2→Space. 미적 채택은 사용자 판단 대기다.
- **정리:** 전달 확인 뒤 이번 run의 번호형 PNG417개/781,905,572바이트(약746MiB)를 삭제했다. 시퀀스별 첫/중간/마지막27장, 이름 있는 캡처, 영상/포스터/로그/QA JSON은 보존했고 삭제 예정 잔여0을 `cleanup-result.json`으로 확인했다. 원시 연속 프레임 전체가 남아 있는 것은 아니다. 사용자 에디터 강제종료·패키징·성능계측·커밋·push 없음.

## 32. 10-23 Space 구르기 롤백 · 빈 F 슬롯으로 독립 분리

- **사용자 교정/계획:** Space는 직전 구르기 적용만 롤백하고, 구르기는 별도 빈칸에서 충분히 길게 시전하도록 요청했다. 기존 F(slot11)가 입력/HUD에 연결된 빈칸임을 확인했다. Space .16초/220cm/분신/W 인계 보존과 F 원본1.4666667초/마우스 방향480cm/독립6초 쿨타임 계획을 먼저 보고한 뒤 적용했다.
- **Space 실제:** `SparrowBackstepEcho`에서 Roll 대역과 몸/날개 숨김을 제거했다. 원래 Sparrow 백스텝 몽타주와 같은 메시의 금빛 잔상3개를 복원했다. 몸과 S 날개는 계속 보인다. 출발점1.10초 분신/준비 중 W 원래1발 인계/발사 후 추가0발, .16초/220cm/6초, sweep/지면/nav/복귀는 유지했다. 이제 Space는 Quaternius 에셋에 의존하지 않는다.
- **F 실제:** 새 `ASparrowGoldRoll`이 원본 Quaternius Roll과 매칭 마네킹을 황금 실루엣으로 표시한다. 원본1.4666667초를 정속으로 끝까지 샘플링하고, 마우스 방향480cm를 부드럽게 이동한다. root motion은 쓰지 않고 본체 capsule sweep이 충돌을 소유한다. 안전한 지면/nav 목적지를 검사한다. F는 원점 분신이나 피해/무적을 추가하지 않으며, 다른 시전 중에는 거부하고 F 중에는 Space/다른 스킬/평타를 막는다. `IsCasting`/활성 슬롯12/HUD명/쿨다운/CancelSkill/EndPlay를 연결했다. 완료·충돌·취소·owner 종료에서 본체 가시성·S의 같은 날개 actor/hidden 상태·root motion/회전을 복구한다.
- **검증:** `f30` 전체7case268개 통과(idle/S/벽/직접Destroy취소/W 중 F거부/숫자전환/일반쿨타임). 평지480cm, 벽 앞190cm, 원본 Roll의 .20/.65/1.10초 포즈 진행과1.60초 완료, 실제 새 이동 입력 복귀를 확인했다. `f60` idle/S 관련181개 통과. `space30` 전체9case275개 통과하며 W 인계1발/중복0발과 S 몸/날개 계속 표시도 확인했다. QA helper는 `SPARROW_ROLL_REVIEW=1`로 F, 기본은 Space이며 `SPARROW_MOBILITY_VIDEO_CASES`로 필요한 영상만 촬영한다.
- **빌드/실행환경:** 최종 DebugGameEditor21.19초/DevelopmentEditor16.61초/DevelopmentGame25.32초 성공. 최초 제한 환경의 dotnet이 컴파일 전 멈춰 본 작업의 확인된 프로세스만 종료한 뒤 필요한 도구 권한으로 재실행했다. 소스 컴파일 실패는 없었고 사용자/공용 프로세스를 종료하지 않았다. FFmpeg 경로 접근도 제한 환경에서 거부돼 필요한 권한으로 인코딩했다.
- **전달/정리:** [실제30fps 영상3개](../../Saved/QA/CharacterPipeline/sparrow-roll-split-20261023/preview.html), [기록](../../Saved/QA/CharacterPipeline/sparrow-roll-split-20261023/result.json). F/S-F는f30, Space-W는space30의 실제 연속 캡처다. 모든 영상 전체 디코딩과 브라우저 실제 출력·시간 진행·오류0·반속/확대를 확인했다. 번호형 임시 PNG129개/243,685,028바이트(약232MiB)를 삭제하고 시퀀스별 대표9장/이름 있는 캡처/영상/포스터/로그/JSON은 보존했다. 직접 실행은 `Play-CurrentSkills.cmd`→숫자2→F 또는Space. 새 다운로드/패키징/성능계측/커밋/push 없음. 미적 채택은 사용자 판단 대기다.


## 33. 10-23 F 전방 회전 교정 · R 즉시 황금 활 · A 파열 · V 이동 · 예약 이동 손실 수정

- **요청/영향:** 두 Diablo3 영상(atOHBsm57Bw 약3초 이후, EwJ3KwNaMu8 약48초)의 실제 Vault 자세를 브라우저에서 확인했다. F 대역의 방향/재생 곡선, R 활 전용 재질/착탄 크기, A 길이/파열, Sparrow 입력 큐와 변신 키를 수정한다. 원본 Quaternius 메시·포즈와 Space .16초/220cm/분신/W 인계 경로는 보존한다. D 교체와 변신 입장 연출은 선택용 시안이다.
- **F 실제:** 원본 glTF 전방+Z가 UE import에서+Y가 되는 것을 원본 bone과 엔진 ConversionUtilities.h로 확인했다. 대역 yaw를 캡슐 yaw-90도로 맞춘다. 전진은 .05초부터 .70초까지480cm, 전체1.05초이며 마지막 .35초는 착지·회복이다. 원본1.4666667초 포즈는 .12/.62/1.05초 구간 매핑으로 연결하고 대역에만28cm 도약 호를 준다. 본체 capsule sweep/지면/nav/6초쿨다운과 종료·충돌·취소·전환의 복원을 유지한다. Diablo 원본 애니메이션을 가져온 것은 아니다.
- **이동 오류 실제:** W 중 우클릭 이동을 예약한 뒤, 거절되는 평타 클릭이 들어오면 KwangPlayerController::AttackPressed가 예약을 지웠다. 새 우클릭은 정상이라 영구 이동잠금과 구분했다. Sparrow의 평타가 실제 수락됐을 때만 예약을 지우며 PlayerTick의 held-attack 수락 경로도 동일하게 처리한다. 재현 전 lost=true, 수정 후30/60fps lost=false와 실제 이동 복귀를 확인했다. 모든 이동 오류가 해결됐다는 주장은 아니다.
- **R/A 실제:** ASparrowMultishotBowTint가 승인된 R 입력에서 bow-only M17_Bow(현 Rogue slot6)를 즉시 금색 MID로 바꾸고 정상종료/취소에 복원한다. 변신 종료가 R 중 재질을 복원하면 갱신된 원래 재질을 추적해 만료된 변신 MID를 되살리지 않는다. 실제 첫 처리프레임 .0333초에서 활 슬롯만 바뀜을 확인했다. 착탄 .65→.325, 원래 emitter/186발/6파동/60피해 유지. A 메시·꼬리 길이15%축소, 비행 중 .16초 간격 작은 파열과 접촉 양옆 불티를 추가했다.160cm/s/90피해/관통/기존3연Flare 유지.
- **V 실제:** 변신 S(slot9)를 V(slot16)로 옮겼다. 기존 정의9/몽타주를 내부적으로 사용하고 HUD·활성 슬롯·쿨타임/상태를16에 연결한다. S는 거부하며 Countess V 분기는 보존한다. 변신40초/현재 날개 형상·질감·망토 및 재질 복원은 유지한다.
- **미적용 시안:** sparrow_transform_entry_studies.py의 V1 응축핵/양날개 점화, V2 상승화염/날개맥 전파, V3 3연파열/잔편을 실제 PIE에서 비교한다. 최종 entries-final30만 전달한다. 초기 약한 시안은 실제 활성 입자0이었으며 component_tags/overlap 등 editor property를 Activate 뒤 설정해 non-auto-active PSC가 꺼지는 것을 확인했다. 모든 속성 설정 뒤 활성화하고 emitter mask를 적용해 출력했다. LOD만 바꾼 시도는 해결 근거가 아니며 템플릿 임시 변경 실험은 최종에서 제거했다. 원본팩/새 입장 재질 저장 없음.
- **D 시안:** sparrow_sentry_study.py에서 고정 황금 궁수2명/8초/.72초 간격을 보여준다. 본체 실제 이동 뒤에도 drift0, 각10회 사격/이동 후8회,8초 종료·전체정리 확인. 시각용 화살이며 피해/자동타깃/충돌/실제 D 교체는 없다. 원래 날개 없는 D는 유지한다.
- **검증 범위:** F idle/S는 combined30의 해당196검사만, 나머지6케이스는 remaining30의164검사와 이동복귀48검사만 재사용한다. 두 run 전체의 실패 상태는 보존한다(바닥 밖 QA 조준좌표, 키 처리 전 재질 조회). presentation30의 R/취소33검사, studies30의 변신 중 R 복원/A18검사를 사용한다. 나머지 중단은 QA use(V)의 조준 누락과 Python 미노출 getter였고 수정했다. f-recovery60 전체250, entries-final30 전체46, sentry-active30 전체14 통과. 총769개 scoped checks이며 미적 채택과 구분한다.
- **빌드/전달:** DebugGameEditor 최종5.53초, DevelopmentEditor33.92초, DevelopmentGame42.37초 성공. [실제영상7개](../../Saved/QA/CharacterPipeline/sparrow-vault-arsenal-20261023/preview.html), [근거/실패범위](../../Saved/QA/CharacterPipeline/sparrow-vault-arsenal-20261023/result.json). 전체 디코딩과 IAB 실제화면/시간진행/오류0/반속/확대/단일재생/overflow없음을 확인했다. 직접 실행 Play-CurrentSkills.cmd→숫자2→F/R/A/V. 사용자 시안 선택은 미결이다.
- **정리:** 이번 QA 폴더에서 번호형 PNG1,576개/2,976,452,877바이트(약2.77GiB)를 삭제했다. 시퀀스 첫/중간/끝69장과 이름 있는 캡처/영상/포스터/로그/JSON은 보존했고 예정 삭제파일 잔여0이다. 원시 연속 프레임 전체는 남지 않는다. 사용자 에디터 강제종료·새다운로드·패키징·커밋·push 없음.


## 34. 10-23 F 잔상·착지 연결 / V2 축소·가속 / D 고정 궁수 / W 슬림 / A·신규 시안

- **요청/영향:** 사용자가 F 출발·도착을 자연스럽게 잇는 금빛 잔상, V2 채택·펼침1.5~2배·날개 추가20% 축소, D 망토·본체 동일 공속, W 더 얇은 투사체를 요청했다. A의 원형 이펙트 등 여러 보강안과 신규 스킬 여러 시안도 요청했다. R은 현 상태 유지, Space 분신/W 인계 유지다. 기존 무인 진행 승인 안에서 영향과 구현 계획을 먼저 알리고 진행했다.
- **F 실제:** 1.05초/480cm/6초·기존 capsule sweep/nav/방향·포즈 곡선을 유지한다. 소유 M_SparrowRollBlend의 Visibility로 원본 Roll 대역과 본체 자세의 금빛 전환 메시를 교차 표시하고, 실제 본체는 .85초부터 다시 보여 종료 전에 연결한다. UPoseableMesh 잔상5개는 생성 순간의 월드 위치·뼈 자세를 고정해 .32초간 감쇠한다. V 날개도 같은 연결 계수로 나타난다. 본체 재질/section은 건드리지 않는다. 첫 실제 화면의 딱딱한 금빛 망토판은 LeaderPose가 cloth 시뮬레이션 정점을 복사하지 않기 때문이어서, 전환 메시에서만 Cloak/CloakStraps/CloakHood 슬롯을 숨겼다. 본체 cloth 시뮬레이션은 보존했다.
- **V 실제:** 기존 Serath 날개 모양/표면 화염을 유지하고 크기0.8배·펼침 .8→1.4(1.75배), 위치 anchor도 같은 비율로 맞췄다. 상승 불꽃 뒤 날개를 따라 번지는 V2 입장 효과12개를 native에 적용했다. 위치별 지연 점화/끝 불티로 날개 근처에 집중하고 짧게 소멸한다. 40초 지속과 변신 해제 재질·망토 복구는 유지한다.
- **D 실제:** 이전 추종 분신을 뒤130/좌우165cm의 고정 궁수2명으로 교체했다. 8초 유지, 망토·끈 표시/후드 제거/변신 날개 없음. GetBasicAttackCycleSeconds가 실제 평타 몽타주 길이·재생률·ComboRestartCooldown으로 주기를 계산하며 현재 .600000024초다. 근처 유효 표적+시야 검사 후 한 발6피해(기본20의30%)로 쏘고, 표적 없으면 피해0 시각 사격이다. 실제 이동 중 drift0, 각13발, 플레이어 스킬 이벤트 중복사격0, 자동 소멸·준비취소·캐릭터 전환 정리를 확인했다.
- **W 실제 / 유지:** charged W 몸통 폭2→1.1(기존55%), 비행 aura YZ .8→.46으로 줄였다. 길이·4000cm/s·35피해·기존 착탄6emitter는 유지한다. R과 Space native 경로는 이번에 수정하지 않았으며 기존 broad suite는 반복하지 않았다.
- **시안:** A10 이중공전환/A11 파열톱니환/A12 쌍갈고리후류/A13 나선잔륜, 신규 N1 황금결박/N2 전방반격막/N3 빛회수 모두 실제 게임 시각 시안이다. 운영 A와 키 연결은 미변경이며 신규 제어·반사·회복 판정은 없다. A12/N3는 첫 화면에서 형태가 약해 실제 렌더를 보고 기존 NoxGlowStrip/NoxSpark의 금빛 MID 곡선과 둥근 핵으로 보강했고 refined30을 최종 전달한다.
- **검증 범위:** final60 전체1124검사(F idle/변신·잔상·착지·이동큐, V/D), concepts30 전체160검사(V/D 전체·시안), refined30 전체21검사(A12/N3) 통과. review30 전체는 실패로 보존하고 F_wall/F_destroy_cancel의130통과검사만 재사용한다. 이 run의 이동큐 실패는 NoNavProjection으로 입력이 예약되지 않은 QA 좌표였으며, projection을 먼저 확인하도록 fixture 수정 후 final60에서 회복을 확인했다. arsenal30은 바닥 밖 A10 조준으로 실패, 선행 W12통과검사만 사용한다. motion60은 전환 망토를 숨긴 뒤 구형 QA 기대값으로 중단됐고 최종 검사로 대체했다. 기존 실패 run을 전체 통과로 기록하지 않는다.
- **빌드/전달:** 최종 DebugGameEditor5.95초/DevelopmentEditor21.08초/DevelopmentGame30.06초 성공. [실제 영상12개](../../Saved/QA/CharacterPipeline/sparrow-vault-v2-sentries-20261023/preview.html), [결과](../../Saved/QA/CharacterPipeline/sparrow-vault-v2-sentries-20261023/result.json). MP4/WebM 전부 전체 디코딩, IAB 12개 실제 재생/시간진행/오류0·반속·확대·단일재생·가로넘침없음 확인. 실행 Play-CurrentSkills.cmd→숫자2→F/W/V/D. A/신규 시안의 미적 선택은 사용자 판단 대기다.
- **정리:** 전달 확인 후 이번 폴더 번호형 PNG1,882개/3,563,774,421바이트(약3.32GiB)를 삭제했다. 첫/중간/끝57장과 이름 있는 캡처/영상/포스터/로그/JSON/소스는 보존, 삭제예정 잔여0·보존누락0. 새 원본 다운로드·사용자/공용 프로세스 강제종료·패키징·성능계측·커밋·push 없음.


## 35. 10-23 황금 결박·전방 반격막 / Space 구르기 / Countess 백스텝 / 선택용 시안

- **실제 적용:** Sparrow S(slot9/활성10)는 커서 근처 적1명/900cm/시야 검사 후12피해·2초 결박·10초 쿨다운. F(slot11/활성12)는 .18초 진입 뒤2.2초 정면 방어·12초 쿨다운, 지원하는 실제 SparrowArrow/GideonProjectile 차단 후 원래 발사자에게12피해 반격이다. 본인 소유/같은 유효 controller/뒤쪽 공격은 통과한다. V(slot16)와 S의 쿨다운·시전 상태는 독립이다.
- **결박·충돌 복구:** StopMovementImmediately가 AI 요청을 Abort한 실제 실패를 확인했다. 이동모드 유지/PauseMove/StopMovementKeepPathing/원래 CMC tick 상태 lease로 바꾸고, 마지막 해제에 같은 request만 Resume한다. 재시전·취소·owner 전환과 기존 ROOT 표식 보존을 확인했다. F는 선행 Tick에서 미리 탄을 삭제하지 않는다. 약참조 guard registry의 교차 분율을 native Sweep 정렬 Hit.Time 사이에서 처리해 앞선 벽·표적·굴절을 보존한다.
- **이동기 실제:** 기존 F 구르기를 Sparrow Space(slot17/활성18)로 옮겨1.75배/.60초/480cm/6초 쿨다운으로 맞췄다. 포즈·금빛 잔상·착지 연결을 함께 가속하고 sweep/nav/정상·취소·전환 복원을 유지한다. Countess Space는 .16초/220cm 붉은 분신 백스텝이다. 준비 중 V(Blade Siphon) 한 번만 원래 시각에 분신이 인계하고, 발사 후에는 중복0; 벽·취소·전환·이동큐를 검사했다. 뒤의 Countess 전면 재설계는 별도 미착수다.
- **선택용 시안:** W1~3 직선잔광/미세광침/분절후광, V1~3 작은 날개 표면 화염, A14~16 A10 이중궤도 파생, D1 매/D2 쇠뇌/D3 수정포대는 실제 게임 장면의 transient 비교다. 운영 W/V/A/D와 R은 유지했다. D 시안은 피해·AI·키 연결이 없는 시각 prototype이며 실제 설치형 D 교체 완료로 표현하지 않는다.
- **최종 검증:** sanctuary-final30 전체59, final60 전체40 통과. 30fps는 S12피해/AI request1→Paused1→Resume1·정지0cm·재개3.3333cm/재시전·취소·전환/기존ROOT 보존까지 확인했다. F는30/60fps에서12000cm/s 두 실제 투사체를 각각 차단·12피해 반격, 방어 전 본체 native hit1→방어 후0, 본인 탄/뒤쪽 통과. 같은 프레임24000cm/s 벽 선행은153cm에서 원래 WorldHit를 남기고 block0/counter0이었다.
- **재사용 범위:** mobility-pose30 전체1365, countess-first30 전체247, concepts-final30 전체86 통과. timing60의1213 중 구르기/Countess1184만 사용하고 구형 S/F29는 위 최종 검사로 대체한다. concepts-first30은 A14의9검사/영상만 사용한다. sanctuary-first30/input30/nav30 및 mobility-first30의 실패 상태는 보존하고 최종 통과로 덮지 않는다.
- **빌드/전달 상태:** DebugGameEditor10.30초/DevelopmentEditor34.13초/DevelopmentGame40.62초 성공. S65/F108 실제 화면은 확인했다. [18개 실제 영상](../../Saved/QA/CharacterPipeline/sparrow-sanctuary-arsenal-20261023/preview.html)과 [범위·결과](../../Saved/QA/CharacterPipeline/sparrow-sanctuary-arsenal-20261023/result.json); WebM/MP4 전체 디코딩 통과. IAB18개 readyState4·시간진행·오류0과 실제 화면 출력, 확대/0.5배속/단일재생/가로넘침없음을 확인했고 browser-proof.png를 남겼다. 번호형PNG2,539개/4,787,585,016바이트를 사전검사 뒤 삭제해 예정 삭제 잔여0·보존누락0이다. 대표 번호형83장·이름 있는 캡처/영상/포스터/로그/JSON/소스는 보존했다. 원시 연속 프레임 전체는 남지 않는다. 기존 export6개/71,309,226바이트 삭제·잔여0도 완료다. 원본팩 저장·새 원본 다운로드·패키징·커밋·push 없음.
- **다음 작업:** next-countess-request.md의 V/폭풍·분신/A/S/R/D/E 전면 개편은 미착수이며 이번 문서 종료 뒤 이어간다. 새 사용자 답변은 없지만 실제 HUD의 V 왼쪽slot1/remap을 확인해 ‘오른쪽’을 HUD slot16으로 가정하고 commentary에 알렸다. RMB 이동 유지/F 기존 순간이동/Space 새 붉은 분신 백스텝으로 진행한다. 해당 파일의 예전 답변대기 표기는 이 최신 가정으로 대체한다.


## 36. 10-23 Countess 전면 개편 · 검붉은 폭풍/악마화/곡면 검격

- **상태/범위:** 선행 Sparrow §35의 18영상·빌드·정리는 완료 상태를 유지한다. 후속 Countess는 운영 적용·30/60fps 기능 검증·8종 실제 화면·최종3종 빌드·8영상 전달과 브라우저 확인·임시 정리까지 완료했다. 마지막 V 주변 암전 보강도 별도 촬영과 정상 밝기 복귀 화면으로 확인했다. 기존 ASDF의 운영 진입점을 제거했으며, 남아 있는 모든 legacy 코드를 삭제했다고 뜻하지 않는다. Q는 기존 Shadow Slip을 보존하고 W는 비웠다. 원본 팩 저장·패키징·성능계측·커밋·push 없음.
- **입력:** V는 오른쪽 HUD slot16/active17로 옮겼고 우클릭 이동은 유지했다. F(slot11)는 기존 커서 순간이동 최대750cm/6초, Space(slot17/active18)는 붉은 출발점 분신과 .16초/220cm 후퇴/별도6초 쿨다운이다. 예전 §35의 Countess 미착수 표기는 이 절로 대체한다.
- **V:** .40초 발동/3.80초 행동 종료/18초 쿨다운. 3.6초 세계 효과의 반경이100→430cm로 커지고 붉은 그림자가 교차하며12×7피해를 준다. 본체 capsule은 지면에 두고 mesh만 부양한다. 최종 local ColorGain(.15,.10,.12,1)/Vignette.78/BlendWeight(.98×envelope)로 주변을 암전시키며 AutoExposureBias override는 쓰지 않는다. v-blackout30의 실제 최고점에서 어두운 주변과 붉은 검격의 가독성을 확인했고, 마지막0130프레임에서 폭풍 소멸과 정상 밝기 복귀를 확인했다. 발동 후 Space를 써도 폭풍은 원점에 남는다. 발동 전 .20초에 후퇴하면 원래 .40초까지의 남은 예약을 원점에 한 번만 인계한다.
- **A/S:** A는 전방을 왕복하는 회전 그림자 두 개/2.3초/6×10피해/.22초 발동/.75초 행동 종료/9초 쿨다운이다. S는 검붉은 질감의 악마화24초/신규 스킬 피해1.2배/.18초 발동/.85초 행동 종료/30초 쿨다운이며 진입20기본피해에도 배율이 적용돼24다. V/F/Space 중 같은 변신 재질을 유지하고24초 만료 시 원래 재질·section을 복구한다.
- **E/R/D:** E는 지면 지정 반경240cm/55피해/.32초 발동/.80초 행동 종료/8초 쿨다운이다. R은 기존 Ability_Ultimate를 유지하며 전방140/360/580cm 세 구역의 비스듬한 가시가 순차 솟고 공유 hit set으로 한 대상 총90피해/.50초 발동/1초 행동 종료/14초 쿨다운이다. D는 평행한 곡면 검격3회/3×18피해/.18초 발동/.62초 행동 종료/7초 쿨다운이다. D 시각 길이520cm와 판정 중심280/반경280/반폭160cm는 구분한다.
- **최종 시각 교정:** 처음 Aurora Spike의 원래 WPO/마스킹을 잃어 생긴 직사각형을 실제 화면에서 반려했다. 다음 저폴리 검은 삼각형도 반려했다. 최종 E/R은 실제 체적 fragment/crater를 얇고 비정형으로 배치하고, 전용 M_CountessRuinShadow v2에 원본 ink/noise의 이동·검붉은 면 변화·가는 균열·붉은 가장자리를 넣었다. 원본 opacity/dissolve와 source material hash는 보존했다. D는 소유 SM_CountessRuinClawBlade의32분할/256삼각형을 spline으로 휘어 가느다란 곡면3개를 만든다. ruin-final30 E/R/D 실제 화면에서 평면판 문제 해소와 곡면3개를 확인했다. 미적 채택은 사용자 판단이다.
- **판정/복원:** WorldStatic/WorldDynamic 중 Visibility Block만 경로를 막고 Pawn/TrainingDummy는 장애물에서 제외한다. 새 시전 중 우클릭 예약·거절된 평타·종료 후 새 이동, F 안전 착지/벽/Space와 독립 쿨다운, V 설치효과/남은 발동 인계, S 재질 유지/만료, 캐릭터 전환의 actor·예약피해 정리를 확인했다. mesh 상대 offset/root motion/회전의 복구도 별도 검사했다.
- **통과 근거:** boundary30 전체102, visual-refined30 전체148, ruin-final30 전체62, timing-final60 전체308(main15case203+boundary7case100+startup5), move-recheck30 전체51 통과. 최종 영상은 refined30의 A/S/F/Space4개, ruin-final30의 E/R/D3개, v-blackout30의 V1개를 쓴다. V 최종25검사와 시전 후 복구도 통과했다. timing-final60 뒤 gameplay 수정은 없고 Ruin 형상/재질 및 V 주변 감광만 바뀌었다. 최종 V는 별도 재촬영했고 A/S/F/Space는 재사용했다.
- **실패 기록:** visual-baseline30의 gameplay120통과와 시각 반려를 구분한다. functional30은 main203개만 통과했고 boundary enum 노출 오류로 run 전체 실패다. form-move-boundary30의 S/F는 통과했으나 Space 안전/nav 거부 원인은 확정하지 못했다. 같은 S→F→Space 순서의 move-recheck30과60fps는 통과했으며 이를 nav 버그 수정 근거로 쓰지 않는다. space-boundary60의 Space는 통과했고 E 실패는 커서 ray가 벽 앞을 고를 수 있다는 QA 가정 문제였다. behind point의 공개 native 호출과 Visibility Ignore 뒤 실제 키 positive control로 바로잡았다. 실패 JSON은 보존한다.
- **빌드:** 암전 전 DebugGameEditor5.59초/DevelopmentEditor22.67초/DevelopmentGame25.44초 성공. 최종 암전 반영 DebugGameEditor5.58초/DevelopmentEditor5.88초/DevelopmentGame13.50초도 성공했다. 실행은 Play-CurrentSkills.cmd→숫자1→E/R/A/S/D/V/F/Space.
- **전달 완료:** [8영상 페이지](../../Saved/QA/CharacterPipeline/countess-inferno-20261023/preview.html), [상태/범위](../../Saved/QA/CharacterPipeline/countess-inferno-20261023/result.json). 최종8개 WebM/MP4 전체 디코딩과 IAB8개 readyState4·시간진행·오류0·1280×720 출력을 확인했다. 최종 암전 V도 별도 browser-verification-v-blackout.json으로0.5배속/단일재생/가로넘침없음과 실제 출력을 확인했고 browser-proof.png를 갱신했다. V131/E60/R69/A89/D47/S60/F36/Space36프레임이다. F/Space는 각각1.2초이며 일괄 ‘4초’로 표현하지 않는다. V만 교체 인코딩했고 나머지7개 미디어 hash는 유지됐다. 최초 번호형PNG1,301개/2,423,439,412바이트와 최종V128개/161,004,677바이트, 합계1,429개/2,584,444,089바이트를 삭제했다. 대표 번호형66장과 이름 있는 참조·미디어·로그/JSON·소스를 보존했고 최종347보존파일의 누락0·예정잔여0·실패0을 두 cleanup-result로 확인했다. 전체 원시 프레임은 남지 않는다.
- **핵심 파일:** CountessSkillComponentReforge.cpp 및 기존 component/header, CountessRuinVisual.*, CountessInfernoVisual.*, CountessDemonForm.*, CountessBackstepEcho.cpp, KwangPlayerController.cpp. QA는 countess_reforge_review.py/countess_reforge_boundary_review.py, 시각 저작·조사는 countess_ruin_surface.py/countess_ruin_asset_inspect.py/countess_demon_form_material.py다.


## 37. 10-23 Sparrow Space 추가 가속 · 변신 순간이동 · 결박/W/V 구분 시안

- **상태/영향:** 선행 Sparrow §35와 Countess §36의 완료 기록은 유지한다. 이번 운영 변경은 Sparrow Space 일반 구르기 추가 가속과 V 변신 중 순간이동 분기다. 이동기 적용·관련30/60fps 검사·대표 실제 화면·3종 빌드와 결박/W/V9시안의 실제 화면 비교까지 통과했다.11영상 인코딩·전체 디코딩·브라우저·정리까지 완료했다. 시안9개를 운영 스킬에 설치했다고 보고하지 않는다.
- **일반 Space:** SparrowGoldRoll의 PlaybackRate1.75→2.625로 원래1.05초 presentation phase를 실제.60→.40초로 줄였다(추가1.5배). 이동·원본Roll 자세·잔상·착지 연결을 같은 배속으로 진행한다.480cm/6초 쿨다운/캡슐 sweep·지면·nav 검사는 유지한다. 기존 QA의 F_idle 등의 이름은 역사적 case 이름이며 실제 입력은 SpaceBar/slot17/active18이다.
- **변신 Space:** TryRoll 수락 시 GetAscensionRemaining()>0이면 같은 actor의 blink 모드를 선택한다. IsTeleporting()은 선택된 모드를 노출한다. 실제시간 .035초 경과 후 SetActorLocation(MoveEnd,true,Hit,TeleportPhysics)를 한 번 수행하고 전체 .14초 동안 소멸/출현한다. threshold 실제 실행은 프레임 단위다. 출발 잔상은 현재 변신 본체 포즈이며 이동 경로에 구르기 대역을 만들지 않는다.480cm와6초 쿨다운은 일반 모드와 공유한다. 발동 전 목적지 검사에 더해 실제 이동 시 sweep도 적용한다.
- **복구:** 본체 가시성·재질/section·root motion·회전, 살아 있는 같은 V 날개의 visibility/기존 hidden 상태를 정상 종료·취소·벽·전환에서 복구한다. blink 중 변신 만료도 별도 검사했다. HUD는 일반 Golden Roll/0.40s, 변신 Golden Blink/0.14s를 표시한다. Countess 및 다른 스킬 피해/타이밍 변경은 없다.
- **검증/빌드:** mobility30 전체812개 통과(일반6case와 변신6case), mobility60 전체593개 통과(일반idle/변신blink·취소/예약이동 복귀). root가 F_idle_t055와 Space_V_blink_t100/t200 실제 화면을 확인했다. 최종 DebugGameEditor28.64초, DevelopmentEditor14.76초, DevelopmentGame21.48초 성공. concepts-first30은 전체79검사 중 S1 활성입자0 검사에서 실패한 상태로 보존한다. 첫 run의 V2 13검사/영상만 재사용한다. concepts-refined30 전체94검사(W각11,V1=13,V3=14,S각11,startup1)가 통과했고 root가 수정8개 실제 화면을 비교용 전달 수준으로 확인했다.
- **미적용9시안:** W1 긴 백금 직선/압축 후폭풍, W2 세 단15광침, W3 두 분절 후광 개방으로 형태와 발사 후 타이밍을 나눈다. 실제 W의 얇은 화살·35피해·4000속도·6층 착탄은 보존하고 추가 광침은 피해 없는 소품이다. S1 황금 사슬/수갑, S2 접히는 광깃 족쇄, S3 위아래 백금 인장이다. S의 기존12피해·2초 결박 lease·AI 재개는 native가 소유한다. V1 불사조 깃불/V2 백금 가지 광맥/V3 외곽 불꽃 왕관은 실제 날개 형상/.8크기/1.75배 펼침/40초를 유지하는 표면·입장 비교다. 최종9개 실제 화면이 선택용 비교 시안으로 수용됐고 운영 선택 적용은 하지 않았다. W1에 남은 원래 분절 고리는 AirWave0/1의 native Tick이 컴포넌트 visibility를 다시 쓰는 경로여서, 새 시안에서는 actor HiddenInGame으로 억제·복원한다. W1은 각진 V자 압축선, W3는 같은 반경 안의6분절×3층 arc로 두께/명암을 보강했다. refined30 실제 화면에서 고리 제거와 W1/2/3 형태 구분을 확인했다.
- **에셋 경계:** W/S는 transient actor/MID/visibility만 쓰고 저장하지 않는다. V는 /Game/TopDown/Characters/Sparrow/Previews/VSignature20261023 아래6개 소유 재질만 저작하는 범위이며 운영 Membrane/Splines2재질은 바꾸지 않는다. first30 V 저작6재질과 source hash 불변은 통과했다. refined 시안의 source hash 불변·임시 슬롯/actor 복구도 통과했다. 원본 팩 저장·패키징·성능계측·커밋·push 없음.
- **기록/소스:** [현재 결과](../../Saved/QA/CharacterPipeline/sparrow-signature-20261023/result.json), [계획](../../Saved/QA/CharacterPipeline/sparrow-signature-20261023/plan.md). native4파일은 SparrowGoldRoll.cpp/.h, SparrowSkillComponentBackstep.cpp, SparrowSkillComponent.cpp이며 QA는 sparrow_backstep_review.py/sparrow_phase_mobility_review.py다. 시안은 sparrow_w_signature_studies.py/sparrow_binding_signature_studies.py/sparrow_v_signature_studies.py. 11영상 전체 디코딩과 브라우저 readyState4·시간진행·오류0·확대0.5배속 실제 출력을 확인했다. 번호형PNG1,598개/3,010,321,892바이트를 정리했고 대표51장·총229보존파일 누락0,33미디어 hash 변경0,삭제예정 잔여0·실패0이다. media-verification.json/browser-verification.json/cleanup-result.json이 근거다.

- **다음 작업 접수:** 사용자가 Countess 현재 전 스킬의 시각 품질을 반려하고2/3/4 수준에 맞을 때까지 무인 반복 보강을 요청했다. next_work=countess-quality-20261023은 Sparrow 전달 완료 후 현재 진행 중인 작업이다. Q/E/R/A/S/D/F/V/Space 전부를 실제 비교하며 빈 W에 임의 스킬을 넣지 않는다. 검붉은 톤·승인 기능/키를 유지한다. §36의 기능·빌드·당시 전달 완료는 과거 사실로 보존하며, 새 미적 반려를 새 품질 작업으로 기록한다. 요청 원문은 이번 QA 폴더 next-countess-polish-request.md에 있다.


## 38. 10-24 Countess 전 활성 스킬 품질 재작업

- **요청/상태:** 사용자가 §36의 외형을 반려해 Q/E/R/A/S/D/F/V/Space 전체를 2/3/4의 실제 자료와 비교하며 재작업했다. 기존 완료 이력은 과거 기능·빌드 사실로 보존한다. 세 차례 형상/표면 보강과 공통 명중 경로 교정 후 root가9개 실제 화면을 이번 전달본으로 채택했다. 사용자 미적 채택을 기능 passed로 대신하지 않는다. 빈 W와 승인된 키·피해·범위·쿨다운은 유지한다.
- **Q/F/Space:** enhanced Q의 중복 원본 XSlash를 제외하고 실제 소켓 trail 폭과 접촉 flash를 줄였다. F·Space 잔상은 소유 MotionEcho v2의 큰 잉크 흐름/역방향 침식으로 정리했다. 실제 회색 머리 문제는 Clothing 사용 플래그 누락이었으며 수정 후 재촬영에서 해소됐다. Q 대상 접근·귀환, F 커서 순간이동, Space .16초/220cm와 V 예약 인계는 유지한다.
- **E/R/D:** Ruin v5의 lit 어두운 몸체·얇은 진홍 날·낮은 균열로 면을 구분했다. E의 원본 둥근 crater와 다음 부채형 조각을 각각 실제 화면에서 반려하고7개 비정형 매립 암반으로 바꿨다. R의 비대칭 shard와 D의32분할 입체 곡면은 검은 등/붉은 날로 분리한다. 소유 복제 particle은 접촉6층/지면6층으로 선별했다.
- **A/V:** A/V의 Q용 정적 곡면을 없애고 실제 손검 AnimTrail만 남겼다. private trail에 이전 tangent 재계산과12cm/10도/8cm 보간을 적용해 ㄱ자 판 윤곽을 둥근 베기로 교정했다. V는 투영한 중심 대비를 살리는 전용 PP로 주변 암전과 본체 시인성을 나눴다.6layer의 BlackSparks/RedSparks는 최초·재활성화 뒤 제외, 실제 렌더0이며 DarkPuffs48/SmokePuffs48/SpiralArm352가 남았다. 마지막0130에서 field 소멸과 정상 밝기 복귀를 확인했다.
- **S:** 전용 v5 lit 숯빛 본체와 두 혈색 갈기로 바꿨다. 넓은 판 내부 발광은 낮추고 어두운 연속면·붉은 윤곽과 작은 표면 일렁임을 남겼다. 진입 파열은 원본 체인의6층 선별본이며24초 지속·1.2배 피해·정상 재질/section 복원을 보존한다. 완전히 다른 괴물 리그로 교체한 작업은 아니다.
- **공통 명중 잔여 해결:** 각 visual actor를 정리한 후에도 표적 주변 점판이 남았다. 실제 renderer receipt에서 CountessSkillComponentReforge의 ApplyPointDamage 뒤 별도 p_CountessUltImpact677입자를 확인했다. 해당 PSC의 Dark/Back sparks·암전 카드·굴절·Light·큰 flare8층을 꺼6층만 남겼다. impact-final30의 R에서는 RedSpark64/DirectionalSpark48/Smoke각5/TinyFlare1이며 실제 표적 점판이 사라졌다. source asset은 저장하지 않았다.
- **검증:** visual-reviewed30 전체173 중 마지막 변경에 영향 없는 Q/F/Space52검사·3영상만 재사용한다. impact-final30 전체121은 최종 E/R/A/S/D/V6영상과 피해·범위밖피해0·소멸·새이동 복귀 근거다. recovery-final60 전체164에서 S 연속 사용/24초 만료, V→Space, F 벽·안전착지,8스킬 owner 전환 정리와 이동복귀를 확인했다. 최종 피해는 Q35/E55/R90/A60/S진입24/D54/V84다.
- **실패/한계:** visual-refined30 ObjectIterator instance 경로호출, visual-final30 MeshMaterials alias 오류는 PIE 전 실패로 보존한다. 최종은 SystemLibrary 경로 조회와 원래 반사명으로 수정했다. surface-final30 일부 A/S에 일시적 VRAM 초과 문구가 있어 전달에서 제외하고 저작을 재실행하지 않은 impact-final30으로 교체했다. 경고 숨김 명령은 쓰지 않았다. 별도 성능계측은 하지 않았다.
- **빌드/전달:** 최종 DevelopmentEditor26.42초/DebugGameEditor24.73초/DevelopmentGame38.12초 성공. Play-CurrentSkills.cmd가 실제 사용하는 DebugGame 모듈도 갱신했다. [실제9영상](../../Saved/QA/CharacterPipeline/countess-quality-20261023/preview.html), [결과](../../Saved/QA/CharacterPipeline/countess-quality-20261023/result.json).18스트림 전체 디코딩·9poster·27링크와 브라우저9개 readyState4/시간진행/오류0/1280×720, V확대0.5배속·단일재생·가로넘침없음·실제픽셀을 확인했다. 원본 pack/수용 PP hash를 보존했다. 패키징·커밋·push·사용자 에디터 강제종료 없음. 임시 정리 결과는 result.json/cleanup-result.json에 기록한다.

## 39. 10-24 실제 레퍼런스 재구축 · Countess 3차 / Sparrow A·S·E·D

- **상태:** 사용자는 §38의 Countess 외형을 다시 반려했다. 이전 기능/build 완료를 새 미적 수용으로 간주하지 않는다. 실제 YouTube 지정 구간을 브라우저로 탐색하고 reference-reforge-20261024/references에 대표 화면을 기록한 뒤 새 형상을 구현했다. 이번 root 검토 3차 보정본을 게임에 적용하고11개 실제 영상으로 전달한다. 사용자 미적 채택은 별도다.
- **Countess 형상:** A는 두 분신+284도 열린 와류, R은3개 연결 지면 파열/외향 가시, E는 낮은 파열+상승막, D는 자체 생성 손바닥/4손가락/엄지 메시+3갈퀴, S는 입장 응축막3겹, V는 짧은160도 교차 검격이다. 첫 R/E 빈 붉은 고리와 D 광택 장갑을 반려했고, 두 번째 검은 벽/판을 낮추고 반투명 침식으로 바꿨다. Space 출발점 분신은 전용 DepartureInk로 녹여 없앤다. Q/F는 현재 실제 캡처 검토 후 유지. W 빈칸/F 순간이동/Space 분신 후퇴/V 오른쪽칸 유지.
- **Countess 영향:** 피해·범위·쿨다운·이동은 유지하되 D의3타 타이머를 visual commit 뒤 .21/.255/.30초에 맞췄다(총54). Space의 pending V 인계/소멸시점은 그대로다. 저작은 countess_reference_geometry.py v2, countess_departure_surface.py, countess_rupture_finish.py v1이다. 마지막 script는 E/R과 A/V만 저장하며 채택한 D/S 재질은 다시 저장하지 않는다. 원본 pack texture hash 불변 확인.
- **Sparrow A/E:** A는 원래160cm/s·90피해·관통을 유지하며 세 열린 곡면과 작은 후류3개로 변경했다. 첫 선만 보이는 후보를 반려하고 반경/전체높이 그대로 단면/면 밀도를 보강했다. 기존 회전·crackle·3회 접촉파열 유지. E는 기존6발과 판정에 opt-in HolyArrow plane/material만 추가해 백금 갈래촉/깃과 금빛 축을 표현한다. 일반화살/W/R 외형에 전파하지 않는다.
- **Sparrow S/D:** S 기존 binding 입력을 제거하고 ASparrowSharpVolley로 연결. .20/.32/.44초에9발씩27발, 파동별 shared hit set으로 적당18×3=54,1200cm/3800cm/s/40도/.68초캐스트/8초쿨다운. D는 설치궁수 입력을 제거하고 단발 native piercing 화살65피해/1500cm/6500cm/s/radius45/.38발사/.70복귀/10초쿨다운. ASparrowPiercingLance는 실제 이동거리와 벽 정지에 맞춰 광축/소규모 별타격만 표시한다. dormant 기존 binding/sentry actor 구현은 남아 있지만 S/D에서 생성하지 않는다. F 반격막은 기존 독립 pointer/cancel 경로를 보존했다. V/Space/W/R 변경 없음.
- **실제 검증:** gameplay30 전체186검사 통과 중 E/D/Space 최종영상 사용, refined30 전체146 중 Countess S/D 및 Sparrow A/S 최종영상 사용, final30 전체178 중 Countess E/R/A/V 최종영상과 S/D쿨다운·V→S/D→Space→실제평타20→우클릭이동247cm 확인. timing60 전체51은 Countess V→Space 인계와 새 S/D 발사/피해/복귀 확인. boundary-final30 전체는 실패로 보존하되 선행 S/D cancel/wall/switch6case의68통과검사만 재사용한다. 검사 API의 Python 노출 여부 오류이며 actual Repeat+Cooldown feedback 검사로 교체해 final30에서 통과했다. boundary30 cancel_skill도 비노출이어서 기존 SparrowSanctuaryQA.Cancel 콘솔로 교체했다.
- **최종 빌드/전달:** DebugGameEditor5.80초/DevelopmentEditor26.17초/DevelopmentGame35.04초 통과. Play-CurrentSkills.cmd의 DebugGame DLL이 갱신됐다. [실제 영상11개](../../Saved/QA/CharacterPipeline/reference-reforge-20261024/preview.html), [결과](../../Saved/QA/CharacterPipeline/reference-reforge-20261024/result.json).22스트림 전체 디코딩,11개 브라우저 readyState4/시간진행/오류0/단일재생,확대/반속/가로넘침없음 확인. 미선택 Space B1/B2와 V4는 [별도3시안](../../Saved/QA/CharacterPipeline/sparrow-flow-binding-20261024/preview.html)에 보존하며 운영 적용하지 않았다. 이전 S결박·A/D 선택지는 새 레퍼런스 요청으로 대체됐다.
- **정리/한계:** 이번 번호형 원시PNG1644개/2,912,271,638bytes 정리,337보존파일 누락0·33미디어 hash변경0·삭제예정잔여0. 앞선 Space/V 시안의1093개/2,061,828,529bytes도 정리했다. 이름있는 이미지/참조/소스/로그/실패기록/최종미디어 보존. 레퍼런스 동영상 다운로드·성능계측·배포패키징·커밋·push·사용자 프로세스 강제종료 없음. next: 사용자 실제영상 피드백; 기능 passed를 품질 동의로 대신하지 않는다.


## 40. 10-24 Countess 품질 재검토 · 독립 시각 판정과 최종 적용

- **상태:** 사용자가 §39 뒤 품질 완료 여부를 재질문했고, 이전 완료 판정이 성급했음을 인정한 뒤 전 스킬을 다시 검토했다. 새 `countess-quality-gate-20261024`에서 실제 캐릭터2/3/4 비교 화면과 레퍼런스를 기준으로 독립 검토자를 두었다. 첫 기능102검사 통과본도 E/A/V 외형 반려로 남겼고, 3차 실제 촬영 후 확인된 결함을 정리했다. 사용자 미적 승인을 대신하지 않는다.
- **E/R/D:** E/R의 Cup·Shroud 외벽을 생성하지 않는다. E는 열린 비대칭 crest 3면/짧은 상승 검격/낮은 균열로 지면 파열을 만든다. R은 구역별 서로 다른 높이의 가시·밑동 파편을 사용하고 .66초 시각 수명으로 지난 지점부터 힘을 뺀다. D는 손바닥/엄지/손가락을 읽히게 하는 소유 반투명 재질, 좁고 침식된 3갈퀴로 보강. 실제 피해/범위/입력/쿨다운은 유지했다.
- **A/V/S:** A/V는 두껍고 짧은 164도 절삭면+후류, 실체가 보이는 붉은 분신으로 변경. V 6개 시각 풀/18회 교차 동선과 기존 실제12회 피해를 구분하며, 중앙·양옆 경로/경사12~24도로 검격이 옆면으로 사라지는 것을 줄였다. 기존 암전·본체 부양·종료 복구 유지. S는 막이 먼저 갈라지고 본체 붉은 능선/어두운 갈기가 분리된다. 24초 지속/원형상/애니메이션/복구 보존. 새 저작은 `countess_rupture_volume.py` v3, `countess_inferno_signature.py` v3(절삭면v2), `countess_demon_silhouette_surface.py` v1이며 새 소유 에셋11개만 저장한다.
- **최종 검토/검증:** E/A/V는 pass3 64검사와 실제 화면, R/S/D는 pass2 121검사 중 해당 범위를 재사용. Q/F/Space는 변경 없이 기존 실제 영상의 독립 재검토로 유지했다. 마지막 recovery60 54검사에서 S→이동기 연계/재질 복구, V→Space 원점 인계·정리·이동복귀를 확인했다. 첫 pass1은 외형 반려, pass2 V 회색 머리는 신규 StrikeShadow의 Clothing usage 누락 로그로 원인확정 후 v3으로 수정했다. 재저작 없는 recovery60에서 missing usage/재질 compile 오류 없음. audit.json에 시각 채택 범위와 한계가 별도 기록돼 있다.
- **빌드/전달:** 최종 DebugGameEditor6.18초/DevelopmentEditor9.08초/DevelopmentGame16.46초 성공. 기존 `Play-CurrentSkills.cmd`가 사용하는 DLL 갱신. [실제 게임6영상](../../Saved/QA/CharacterPipeline/countess-quality-gate-20261024/preview.html), [적용 결과](../../Saved/QA/CharacterPipeline/countess-quality-gate-20261024/result.json). 6개 WebM/MP4 전체 디코딩 및 IAB 재생·시간진행·오류0·단일재생·확대/0.5배속 확인. 수정 전 영상과 유지한 Q/F 화면 링크도 있다.
- **정리/범위:** 번호형 임시PNG1090개/1,872,964,784bytes 삭제. 대표42장·이름있는 캡처·최종18미디어·소스/로그/감사 등189보존파일의 누락0/변경0, 삭제예정잔여0을 확인했다. 최종 result/상태 갱신은 이 검사 뒤 수행했다. Sparrow·원본팩 수정, 배포패키징, 성능계측, 커밋/push, 사용자 프로세스 종료 없음. 미선택 Sparrow Space B1/B2·V4도 그대로 미설치다.

## 41. 10-24 E 연출 의도 재확인 — 움직이는 시안만

- 사용자가 §39의 Sparrow와 §40의 Countess 시각 결과를 다시 반려했다. 앞선 빌드/기능 사실은 유지하지만 미적 품질 완료 판정은 철회한 상태다.
- 최신 요청은 1번 E부터 원본과 나란히 볼 움직이는 시안을 먼저 제시하는 것. 핵심은 캐릭터만 한 큰 화살 형성 → 촉 앞 파문 → 공격이 이어져 적 타격. 원본 완전복제는 원하지 않는다.
- 이 설명과 연결되는 원본은 앞서 2번 E에 주었던 홀리 에로우 F5biy-QGGIw 15초 구간이다. 대상 번호 확인 질문은 전달했으며, 현재 시안 기본은 최신 명시 요청인 1번/검붉은색이고 금빛 비교도 제공한다. 번호 확정·게임 적용 승인으로 간주하지 않는다.
- Saved/QA/CharacterPipeline/e-arrow-intent-20261024/preview.html: 원본 YouTube 재생+Canvas 움직임 비교, 단계 정지, 측면/쿼터뷰, 배속/색상 전환. 실제 원본 15.067/15.2/15.5 프레임 3장과 시안 WebM 약5초(0.5배속)를 보존했다. 원본 동영상 다운로드 없음.
- 게임 소스/에셋/피해/입력/빌드 변경 없음. 이 산출물은 움직임 해석이며 최종 FX 품질/사용자 수용을 검증하지 않았다. 자세한 범위는 해당 폴더 intent.md. 사용자 확인 전 운영 E에 적용하지 않는다.

- **후속 정정:** 사용자가 비동기 답변으로 대상은 **2번 E / 황금·흰색**이라고 확정했다. 위 §41의 1번/검붉은 기본 표기는 이 정정으로 대체한다. 비교 페이지·영상도 2번 금빛으로 갱신하며, 시안 채택과 게임 적용은 아직 미승인이다.

- **활 중심으로 정정:** 사용자가 “활 이펙트가 전혀없잖아. 화살이아니라 활이펙트 강조”라고 명확히 정정했다. 기존 큰 화살 중심 시안은 이전 해석이다. 같은 e-arrow-intent 페이지를 큰 황금·흰색 활 개방/빛의 깃/시위 당김·반동/전방 파문/발사·타격의 움직임 시안으로 갱신했다. 새 영상은 e-bow-motion-study-gold.webm(4.8초,144프레임)이며 사용자 채택 대기, UE 코드·에셋·빌드 미변경이다.

- **개방·파문 보강 / 날개 제거:** 사용자는 활 강조 방향을 수용했으나 밋밋함과 요청하지 않은 앞쪽 날개를 지적했다. 같은 QA 페이지에서 깃 장식을 제거하고 활 곡선 개방 잔광·이동 발광·입자와 전방 파문의 응축→팽창·회전 발광·분절 잔광을 보강했다. e-bow-bloom-study-gold.webm(4.8초/144프레임)과 comparison-proof-bloom.png가 최신이다. 게임 적용 없음, 시안 최종 채택은 대기다.

## 42. 10-24 Sparrow E 큰 황금 활 시안의 실제 게임 적용

- **승인/범위:** 사용자가 최신 활 개방·전방 파문 시안의 2번 E 적용을 명시 요청했다. 장식은 넣더라도 활 끝에 자연스럽게라는 조건이며, 이번에는 별도 날개/깃을 생성하지 않는다. §41의 게임 미적용/채택 대기는 이번 승인으로 대체한다. 다른 캐릭터와 다른 스킬의 시각 변경은 없다.
- **적용:** SparrowHolyBow 전용 cosmetic actor가 캐릭터만 한 곡선 활/시위 당김·반동, 양끝 개방 잔광·입자, 전방 3단 파문 팽창·회전 발광을 담당한다. 기존 6발 실제 SpawnArrow 성공 시점에 pulse를 동기화한다. 기존 W 계열 준비 입자를 E에서 제거하고 muzzle을 줄여 큰 활을 읽히게 했다. 원본 에너지 텍스처와 M_NoxGlowStrip은 읽기 전용으로 재사용하고, 새 소유 재질 M_SparrowHolyBow만 저장했다.
- **타이밍/기능:** 첫 준비 .12→.32초, 전체 시전 1.20→1.40초로 변경. 실제 6발/비관통/피해/사거리/쿨다운 유지. FinishSkill에서 .18초 fade 후 정리하며 owner 소멸도 처리한다. 새 mesh는 충돌/nav 영향을 끈다. Blueprint의 이전 .12/1.20(.84 legacy) 값만 BeginPlay에서 이행하며 별도 조정값은 유지한다.
- **검증:** review30의108검사(E/취소/실제 우클릭 이동취소/전환/쿨다운/V변신→E→Space→평타→이동) 통과. 파문이 가는 선으로 읽혀 두께와 발광만 추가 보강한 final60의44검사(E/우클릭취소/전환)도 통과. 첫 화살 관찰은30fps .3667초/60fps .35초, 정상6발과 실제 이동복귀 확인. visual30 첫 실행은 QA 들여쓰기 오류로 실패했으며 재질 저작만 성공; 실패 기록 보존. 수정 후 재사용 author 없이 실제 재질 로드와 화면을 확인했다.
- **실제 화면/빌드:** quarterview 개방 .18초/파문 .28초/연속 타격 .75초 및 최종 실제 영상 확인. 이것은 이번 적용본의 시각 확인이며 사용자 미적 승인을 대신하지 않는다. 최종 DebugGameEditor5.39초/DevelopmentEditor28.77초/DevelopmentGame37.20초 성공. Play-CurrentSkills.cmd의 DebugGame DLL 갱신. [게임 적용 영상](../../Saved/QA/CharacterPipeline/sparrow-e-holy-bow-20261024/preview.html), [결과](../../Saved/QA/CharacterPipeline/sparrow-e-holy-bow-20261024/result.json).
- **전달/정리:** 실제 PIE 연속102프레임/60fps/1.7초/1280×720를 MP4와 WebM으로 인코딩·전체 디코딩했다. IAB readyState4/시간진행/오류없음/반속·확대·시점조절을 확인했다. 번호형 임시PNG153개/289,249,365bytes 삭제, 최종미디어 hash변경0·예정잔여0. 대표 이미지와 source/log/json/실패기록 보존. 배포패키징·성능계측·커밋/push 없음. 다음: 사용자 실제 E 피드백.
## 43. 10-24 Sparrow E 활 조형 보강 · 단발 충격

- **요청/범위:** 사용자는 §42의 방향을 수용하고 원본처럼 더 화려한 활, 여러 발 대신 단발로 파박하고 꽂히는 연출을 요청했다. 현재 운영 E는 이번 단발본이다. 다른 스킬/캐릭터의 시각·피해는 보존했다.
- **What/Why/How:** 활 본체에 3겹 장식선·음각 광맥·마름모 광점과 활 양끝에 연결된 불꽃형 장식을 넣었다. 별도 앞쪽 날개는 없다. 첫 화면에서 평행선만 남는 문제, 다음 화면에서 백색 겹침을 확인해 끝부분 간격과 밝기를 한 번 더 정리했다. 개방·전방 3단 파문을 유지하고 발사 순간 짧은 전방 광선을 더했다. 시위는 한 번 반동하고 파문은 앞으로 퍼지며 .28초 내 소멸한다.
- **단발/피해:** 6연사 타이머를 제거하고 FireHolyArrow/CreateHolyShotMontage로 단발 처리. 준비 .32초, 발사동작 .16초, 마무리 .12초로 전체 .60초(기존1.40초). 속도3000→6000, 기본60피해 한 번, 첫 표적 비관통, 사거리1800/쿨다운8 유지. 기존 누적 피해 패시브는 실제1타로 기록하므로 신규 표적에 기존6연사의62.625 대신60이 들어간다. HUD도 Holy Arrow/1 arrow/60 damage로 변경. 기존 RapidShot 이름과1.40/1.20/.84 legacy 회복값만 이행한다.
- **접촉:** E 화살의 실제 target/world 접촉에만 SparrowHolyBow의 impact 모드를 생성한다. .055초 간격 두 겹 섬광/방사 파편/분절 파문은 순수 cosmetic이며 추가 피해가 없다. 벽은.55규모다. E 비행 표면은 길고 좁게 정리하고, 충돌/nav 비활성화를 mesh 설정 전으로 옮겼다. shared arrow의 다른 모드는 HolyArrowFlight가 없어 새 접촉 연출에 진입하지 않는다.
- **검증:** review30 126검사(E/취소/실제 우클릭 취소/캐릭터 전환/벽/쿨다운/변신 후 E→Space→평타→이동) 통과. final60 45검사(E/우클릭 취소/전환) 통과. 마지막 재질 간격·밝기 수정은 detail60 E19검사와 실제 화면으로 확인했다. 신규 표적에 실제화살1/피해60/피해이벤트1/접촉연출액터1, 취소 후피해0, 벽뒤피해0, 액터정리·이동복귀 확인. 기능 통과를 사용자 미적 승인으로 보지 않는다.
- **빌드/전달:** 최종 DebugGameEditor5.54초/DevelopmentEditor25.12초/DevelopmentGame31.33초 성공. Play-CurrentSkills.cmd 사용 DLL 갱신. [현재 단발 E 실제 영상](../../Saved/QA/CharacterPipeline/sparrow-e-radiant-single-20261024/preview.html), [결과](../../Saved/QA/CharacterPipeline/sparrow-e-radiant-single-20261024/result.json). 실제102프레임/60fps/1.7초/1280×720 MP4+WebM 전체 디코딩, IAB readyState4·시간진행·확대·반속·시점조절 확인. 이전6연사 영상 비교 링크 유지.
- **정리:** 번호형 임시PNG255개/480,419,562bytes 삭제. 미디어 hash변경0/예정잔여0이며 대표18장과 소스/재질/로그/JSON/최종영상 보존. 배포패키징·성능계측·커밋/push 없음. 다음은 사용자 실제 단발 E 피드백이다.
## 44. 10-24 Sparrow E 큰 활 · 연결된 깃 · 전방 원형 파문 교체

- **요청/의도:** 사용자는 §43이 이전보다 훨씬 낫고 방향이 잡혔다고 평가했다. 더 큰 화려한 활, 어색하지 않게 붙은 날개, 원형 이펙트 교체를 요청했다. 중심 형상과 개방→응축→단발→타격의 연결을 다음 스킬 작업 기준으로 설명했다. 다른 스킬을 이번에 자동 변경하지 않았다.
- **What/Why/How:** 활 본체 높이 약1.35배, 양쪽 limb에 뿌리가 연결된5갈래 깃/광맥/장식선. UV 여백을 늘려 끝 잘림을 피했다. 앞3원 대신 열린 곡선 쐐기/움직이는 발광/수렴 파편을 구성했다. 최초 각진 꺾임을 곡선으로 다듬었고, 발사 뒤3문양이 여러 화살처럼 보이지 않도록 .07초 안에 소멸한다. 실제 단발60피해/.32준비/.60시전/6000속도/1800사거리/8초쿨다운/접촉2pulse는 보존.
- **저장 경계:** 첫 visual60은 실행 중 사용자 Development 에디터가 M_SparrowHolyBow를 잠가 저장 실패했다. 실패로그를 보존했고 강제 종료하지 않았다. 새 소유 M_SparrowHolyBowFeather에 저작하고 C++ 참조를 교체했다. 이전 재질·원본팩은 보존. 이후 사용자 에디터가 종료된 것을 확인해 일반 에디터DLL도 갱신했다.
- **검증:** final60/ refined60는 각19검사 통과했으나 위 시각 수정 전 단계다. 최종 release60의19검사와 실제 .18/.28/.43 화면만 최종 근거로 쓴다. 실제 화살1/60피해/접촉액터1/후속 이동246.8cm, shader compile/usage/Python 오류없음. 이번은 cosmetic 변경으로 직전 타이밍·취소·벽·전환·변신 연계 전체 suite는 반복하지 않았다.
- **빌드/전달:** DebugGameEditor6.10초/DevelopmentEditor6.47초/DevelopmentGame23.33초 성공. [실제 게임 영상](../../Saved/QA/CharacterPipeline/sparrow-e-winged-bow-20261024/preview.html), [결과](../../Saved/QA/CharacterPipeline/sparrow-e-winged-bow-20261024/result.json). 실제102프레임/60fps/1.7초/1280×720 MP4+WebM 전체디코딩, IAB 실제출력/재생진행/확대/반속/시점.28초 확인. 직전 단발본 비교링크 유지. 직접 HTTP 소스는 seekable[0,0]으로 이동이0초에 머물러, 이번 짧은 로컬WebM을 Blob으로 버퍼링한 뒤 seekable[0,1.7]과 실제.28초를 확인했다.
- **정리:** 최종 영상 검증 뒤 번호형PNG306개/576,647,214bytes 삭제, 미디어hash변경0/잔여0. 이름있는18캡처/최종영상/소스/로그/실패기록 보존. 기능·실제화면 확인은 이번 미적 최종 승인과 구분한다. 커밋/push/배포패키징/성능계측 없음.

## 45. 10-24 Sparrow E 활 형태 4종 — 선택용 실제 게임 시안

- **요청:** 사용자는 §44 방향이 대강 잡혔지만 형태·효과가 아쉽다며 레퍼런스를 참고한 활과 다른 여러 시안을 요청했다. 이번에는 운영 E를 바꾸지 않고 비교만 제공한다.
- **레퍼런스:** F5biy-QGGIw를 브라우저에서 재생/정지/프레임 전진해15.155/15.322초를 다시 봤다. 굵은 곡선 몸체, 말린 끝, 몸체에 연결된 깃, 전방의 강한 응축광을 참고했다. 앞 원형 파문은 직전 피드백대로 제외. 원본 영상 다운로드 없음. 브라우저 캡처1장/기존15.2초 이미지/원본 링크를 보존했다.
- **시안:** B1성익 장궁=굵은 활+곡선 끝+연결된6깃, B2왕관 문장궁=쌍곡선/말린 문양/보석/왕관끝, B3결정 대궁=두꺼운분절면/모서리/결합, B4태양 화염궁=실제Serath화염텍스처가 흐르는 활 표면. 몸체·앞 응축광을 각기 다르게 구성한다. 모두 실제 단발/60피해/기존타격/몽타주/시전 유지. 부모 판단은 B1형상이 원본에 가장 가깝고 B4표면이 움직임을 보강하는 후보이며 사용자 미적채택을 대신하지 않는다.
- **범위:** sparrow_e_bow_design_studies.py에서 Previews/EBowForms20261024/M_B1~M_B4만저장. 실제E활actor를PIE에서만숨기고충돌/nav없는비교plane을겹쳐그린다. 실제화살/타격actor는유지. 각케이스후가시성복원/임시plane정리. 소스4개+운영Feather재질+DebugGameDLL해시전후같음. C++수정/빌드/운영에셋수정없음.
- **검토/검증:** 첫designs30은author반환누락으로검사시작전실패(재질저장은완료),수정후review30의38검사통과. 그러나per-segmentrim이몸체에반복선을남겨시각반려했다. union된몸체외곽에서rim을한번계산하도록고치고B3폭/B4실제불꽃을보강한refined30의38검사와4실제화면/브라우저영상만최종근거다. 재저작중ComponentMask입력미연결경고는최종저장전이며PIE중재질오류없음. 실제발수1/피해이벤트1/60/복귀/정리/운영해시보존확인.
- **전달:** [4종비교페이지](../../Saved/QA/CharacterPipeline/sparrow-e-bow-designs-20261024/preview.html), [결과](../../Saved/QA/CharacterPipeline/sparrow-e-bow-designs-20261024/result.json). 각41연속프레임/30fps/1.3667초/1280×720 MP4+WebM전체디코딩.4영상모두readyState4/시간진행/실제출력/동일.28초seek/확대복귀확인. 기본0.5배속/1.75배확대,원래시야전환가능.원격전달용four-bows-half-speed.mp4는같은crop(320,150,640,360)의4분할/0.5배속이며자막과대표프레임확인.
- **정리:** 번호형PNG328개/618,503,327bytes삭제,최종미디어hash변경0/잔여0.32이름있는프레임/최종영상/비교재질/소스/로그/실패기록보존. 다음은사용자선택이며승인전운영E에설치하지않는다.


## 46. 10-24 Sparrow 액션 조사 · Q 후딜 · A 복원 · E/W/R/A/S/D 시안

- **범위/상태:** 사용자의 추가 요청을 한 묶음으로 처리했다. 게임에 적용한 것은 Q 장전 후딜 제거, A 직전 리포지 이전 형태 복원, 기존 S Sharp Shooter 비우기다. E3/W2/R2/A2/S3/D2=14개 효과는 선택용 PIE 시안이며 사용자 선택 전 운영 설치하지 않는다. D 기반은 사용자가 현재 한 발 관통 사격이라고 명시적으로 확인했다. 사용자 미적 채택은 아직 대기이며 품질 동등성을 확정하지 않는다.
- **Q:** SparrowSkillComponent.cpp의 HailRecovery를1.60→0.36초로 변경하고 기본 HailOfArrows에 저장된 구값만 마이그레이션한다. 발사0.24초/기존 몽타주/0.12초 블렌드/지속피해는 유지하고 후반 재장전 구간을 끊는다. 30/60fps의 실제 시전해제0.40/0.3833초, 이후 이동293/288.9cm와 표적피해40/40/0을 확인했다. 발사 전 취소·S 빈칸·F 기존 시전/복귀 검사도 통과했다.
- **A:** SparrowAscension.cpp/.h에서 별도 감사한 pre-reforge 원문으로 복원했다. 3개TsunamiBlade+3개Wake를 제거하고 FeatherRings2장/1.6·1.08크기/-24cm/1.05·0.46envelope를 되살렸다. 속도160/관통피해90/회전540/짧은화살/0.16빠직거림/접촉3파열 보존. 감사 원문·patch·적용근거는 sparrow-a-rollback-audit-20261024에 있다. AT1 좁은나선과 AT2 넓은찢어진바람은 롤백한 본체 위에 겹친 시안이다. 초기 스프링 같은 공간 주기를 줄이고 넓은 바람 면을 추가한 refined30을 전달한다. 회오리는 아직 운영 선택 적용 전이다.
- **S/F:** SparrowSkillComponentSanctuary.cpp는 Slot11(F)만 받도록 바꿔 S의 SharpVolley 생성 분기를 제거했다. S 이름/상태/쿨다운은 빈값/0이며 F Counter Ward는 유지한다. 기존 클래스와 cleanup은 보존한다. 최종 S4 좁은나선4묶음/S5 넓은돌풍3묶음/S6 좌우수렴3묶음은 원본 사격 자세를 쓰는 피해 없는 시안이다. 처음의 단단한 금색고리/C자외곽은 실제 화면에서 반려했고, 최종 s-wind30은 T_Smoke_Tiled_D와 T_Wind_Blur의 농도 자체로 외곽이 변하는 흰·금빛 방향성 바람이다.
- **E/W/R/D:** C1천익개방/C2광휘현궁/C3뇌광성궁은 활이 펼쳐지는 순서와 재질, 한발에 이어지는 두 짧은 접촉파열을 달리했다. 실제 E한발/60피해 유지. W4분절대궁/W5백금레일, R4큰장궁/R5분리된세활, D4저격선/D5분절바람창은 실제 native 발사/피해 위의 비교연출이다. 각 시안 전용 Previews 재질만 저장하며 원본팩과 운영 선택재질을 교체하지 않았다.
- **액션 조사:** registry2,582개(몽타주/블렌드스페이스 포함), 실제 AnimSequence463개 로드, Sparrow원본152개. 14원본동작 영상과 대표42장+추가16장을 검토했다. 가로활사격/발차기/물구나무진입/후방공중회피/검격/공중공격/기존Quaternius Roll이 확인된다. M06/M07은 방향전환 발놀림·몸비틀기이며 실제360도 회전이나 사격이 포함되지 않는다. 완성 회전사격/후퇴사격/구르기사격은 미확인·미제작, 전용 활근접타격/슬라이딩도 확인 안 됐다. M08은 활을 다루는 이모트이고 Bow_M1은 인사다. 타 스켈레톤 원본은 같은 Sparrow에 바로 적용한 것이 아니며 리타게팅 또는 원래몸체대역이 필요하다. 정확한 경로·관찰·조건은 action-inventory-summary.json/.md 참조.
- **검증/실패 보존:** review30 전체127검사 중 최종 C1/C3/W4/W5/R4와 Q행동 근거만 재사용. C2는 e-release/review60, AT1/AT2는 refined30의29검사, Q60은23검사, A실제복원+14동작은 actions30의49검사, R5/D4/D5는 s-d-final30의42검사 중 해당부분, 최종S는 s-wind30을 근거로 한다. 각전체 passed이나 시각반려된 중간 결과를 최종으로 간주하지 않는다. 첫E저작은 HLSL 예약어 line 문제로 실패했고 spine으로 교정했다. 중간R5/S/D의VRAM경고영상은 제외했다. 사용자 일반에디터 PID30012를 유지한 채 최종QA프로세스만 StreamingPool384/VirtualShadowPages512로 줄여 재촬영했으며 경고숨김명령·프로젝트설정변경은 없다.
- **빌드/실행:** DebugGameEditor15.90초/DevelopmentGame46.97초 성공. Play-CurrentSkills.cmd가 사용하는 DebugGame DLL로 실제PIE를 검증했다. 사용자의 기존 DevelopmentEditor가 실행 중이어서 그 DLL은 이번에 갱신하지 않았고 해당 세션에 변경을 로드하지 않았다. 새 실제 실행은 프로젝트 루트 Play-CurrentSkills.cmd 사용. 패키징·커밋·push·성능계측 없음.
- **전달/정리:** [비교페이지](../../Saved/QA/CharacterPipeline/sparrow-action-arsenal-20261024/preview.html), [결과](../../Saved/QA/CharacterPipeline/sparrow-action-arsenal-20261024/result.json). 효과14+액션14+적용확인Q/A2=30MP4 전체디코딩, 브라우저30개 readyState4·시간진행·오류0, 확대/반속/.28초seek/확대카드/가로넘침없음 확인. 두 이번작업폴더의 번호형PNG3,220개/6,046,885,692bytes만 삭제했다. 대표이미지·영상252개 해시변경0/누락0/삭제잔여0. 소스/로그/JSON/실패기록/시안재질은 보존한다.

## 47. 10-24 Sparrow D 결합 · 새 레퍼런스 기반 E/W 다섯 방향

- **요청/범위:** D4 저격선과 D5 분절 바람을 D6으로 합치고 D7 압축 나선/D8 사풍 파열을 추가했다. E/W는 사용자가 새로 준 zAkT93h6o8k를 실제 브라우저에서 확인하고 G1 성익대궁/G2 삼중광익궁/G3 결정파쇄궁/G4 불사조화염궁/G5 백금뇌광궁을 각각 E와 W에 연결했다. 총13개 실제 PIE 영상이며 선택용 시안이다. 운영 C++/선택 재질/스킬키/피해/빌드 변경 없음. 사용자 미적 채택은 대기다.
- **레퍼런스/소재:** 약26.507초 활 개방,26.660초 방출,34.295초 반복구간을 관찰했다. 겹친 깃 몸체/내부 명암/짧은 전방 방출을 황금·흰색으로 해석하고 큰 전방 고리는 제외했다. 원본 동영상 다운로드 없음. 첫 수학적 윤곽은 너무 흰 반복선이라 반려했다. 내장 이미지 생성으로 투명 깃활/결정활2장을 만들고 Previews/EWReference20261024의 T_GoldBow/T_CrystalBow로 가져왔다. 원본 소재와 정확한 프롬프트는 QA폴더 art/에 보존. UV 개방/시위/반동/불꽃흐름/전류/소멸은 게임 재질에서 처리한다.
- **D/수정:** D6은 D5 원래 몸체·크기·.40초 잔상을 유지하고 D4 레일/눈금을 결합했다. 실제 화살 이동거리/속도로 발사시점을 보정했다. D7은 화살 머리를 추적하는 짧은 축방향 바람이다. D8은4날 개방→전방 접힘이며 불투명 흰 덩어리와 과한 감쇠를 각각 반려한 뒤 폭25%축소/낮은 흰핵/반투명 농도를 가진 d-wind-readable30을 선택 후보로 남겼다. 다른 두 후보는 이 수정에서 보존했다.
- **최종 근거:** D6=d-refined30, D7=d30, D8=d-wind-readable30. E_G1/E_G4=ew-art-pilot30, 나머지 E/W=ew-art-final30, 단 E_G3/W_G3는 평평한 판 형태를 반려한 뒤 ew-crystal-final30으로 교체했다. 해당 실행의19/28/10/20/74/20검사가 통과했으나 중간 반려 후보는 최종으로 간주하지 않는다. 실제 화살각1/피해이벤트각1, E60/W35/D65, 복귀/임시효과정리 확인. 운영 E소스4개+선택Feather재질+DebugGameDLL 해시가 전후 및 최종과 같다. 최종HLSL오류 없음; 기존 시작에셋경고/그래프 재연결 중 ComponentMask 경고는 로그에 남아있다.
- **전달:** Saved/QA/CharacterPipeline/sparrow-ew-reference-20261024/preview.html. G1~G5는 E/W를 나란히 보고 D탭에서3개를 비교한다. 13MP4(각1.4초/42프레임/30fps/1280×720) 전체디코딩, 브라우저13개readyState4/시간진행/오류0, .28초seek, 1/0.5배, 확대/원래시야, 가로넘침없음을 확인했다. 첫 플레이어의 video.loading 속성명 충돌은 WeakMap으로 수정했다. browser-proof.png/browser-verified.json/result.json에 근거 보존. 페이지에 원본 링크와 이미지생성 소재·프롬프트가 있다.
- **정리:** 이번 QA폴더 안의 번호형 임시PNG1,218개/2,298,106,483bytes만 삭제했다. 대표프레임/최종영상/소재/스크립트/JSON 등265개 보호파일의 변경·누락0, 삭제잔여0을 재검증했다. 생성 원본/시안 재질/소스/실패·반려 로그는 보존. 사용자 기존 에디터는 종료하지 않았고, 격리QA GPU 작업만 순차 실행했다. 커밋/push/패키징/성능계측 없음.
## 48. 10-24 Sparrow 활 2D 형태·톤 선택 / D 통과 후 깃 잔광

- **요청:** 사용자는 §47 D를 모두 반려하고, 화살이 지나간 자리에 나중에 깃털 효과가 남기를 요청했다. 활은 기존 이펙트 톤·디자인과 맞지 않는다며 2D 디자인을 먼저 고르는 방식을 제안했다. 이번은 선택용 시안이며 운영 스킬에 설치하지 않았다.
- **활 2D:** 기존 W 타격·V 날개 실제 화면을 톤 기준으로 내장 이미지 생성 도구로 B1 빛깃/B2 겹빛/B3 분절 깃/B4 불꽃 4장을 제작했다. 불투명 금속·결정 표면 대신 황금·상아색 반투명 빛결을 비교한다. 오른쪽 캐릭터/배경도 생성된 설명 그림이고 실제 게임 캡처가 아님을 페이지에 명시했다. 원본을 art/B1~B4.png에 복사하고 정확한 프롬프트·참고 경로는 art/prompts.json에 보존한다. 선택 후 몸체·깃·광핵을 나누어 개방→응축→단발 움직임을 맞추는 단계가 남아 있다. 부모 제안은 B1 형태 또는 B4 질감이며 사용자 선택은 아니다.
- **D9 What/Why/How:** 기존 sparrow_d_combined_studies.py에 D9만 추가했다. 실제 SparrowArrow의 이동거리/속도로 발사시점·출발점을 복원하고, 지나간 경로의 7개 고정 지점에서 35~55ms 뒤 작은 깃이 나타나 0.50~0.60초 동안 흩어져 사라진다. HeadDistance로 화살 앞 깃 출현을 막는다. 기존 D 한 발/65피해/원래 타격은 유지하고 별도 준비장식·레일·추가 폭발은 넣지 않았다. Previews/DCombined20261024/M_D9만 저작하고 기존 후보는 보존한다.
- **검증:** d-feather30의 11검사 통과/실패0, 실제 화살1·65피해·통과 후 깃7개를 확인했다. .38초 발사 전/.60초 초기깃/.75초 잔광 실제 화면을 검토했다. 42프레임/30fps/1.4초 H264 MP4 전체디코딩 통과, 브라우저 네 이미지 로딩·영상 시간진행·.75초 탐색·오류없음 확인. 이 검증은 사용자 미적 승인을 의미하지 않는다. 운영 C++ 수정·빌드·스킬 설치 없음.
- **전달/정리:** Saved/QA/CharacterPipeline/sparrow-feather-direction-20261024/preview.html. browser-proof.png/d-browser-proof.png/browser-verified.json/result.json에 근거를 남겼다. 영상 검증 뒤 이번 촬영의 번호형 PNG42개/78,921,792bytes만 삭제했고 보호 미디어13개 변경0/삭제잔여0을 확인했다. 대표 화면·영상·생성 원본·프롬프트·재질·소스·로그는 보존. 다음 단계는 사용자의 활 형태/질감 선택과 D 잔광 피드백 반영이다.

## 49. 10-24 Sparrow 쇼츠 원본 재관찰 · 활 2D 4안

- **요청:** 사용자가 §48 B1~B4가 첫 쇼츠 zAkT93h6o8k와 느낌이 너무 다르다고 반려했다. 첫 링크를 자세히 다시 보고 그 활 이펙트를 기준으로 2D 시안 여러 장을 요청했다. 이번은 활 그림만 제작하며 D·운영스킬·C++·에셋·빌드는 변경하지 않는다.
- **원본 관찰:** 일반 YouTube 플레이어에서 정지/period 프레임 전진으로 26.448/26.514/26.681초를 직접 봤다. 겹쳐 벌어지는 폭넓은 곡선 몸체, 청록색 잎 모양 면, 금색 연결선/빈 공간, 흰 갈고리 끝, 발사 때 함께 방출되는 빛을 확인했다. 이전 시안은 가느다란 깃·불꽃으로 지나치게 해석했음을 인정했다. 원본 두 전체 화면을 보존했다. 영상 다운로드 없음. 전체화면에서 별도 clip 캡처는 검게 나와 반려하고 getScreenshot 전체 캡처로 교체했다.
- **시안/범위:** 원본 26.514초 실제 캡처를 내장 이미지 생성의 직접 reference로 넣었다. C1 기본 구조/C2 넓은 끝 장식/C3 열린 몸체·연결선/C4 겹침·작은 광핵. 같은 원본 구조 안에서 변형하고, 청록색 면을 황금·상아색으로 바꿨다. 모두 캐릭터·배경 없는 2D 활 그림이며 실제 게임 효과/애니메이션이 아니다. art/C1~C4.png와 정확한 프롬프트 art/prompts.json을 보존한다. 생성 원본은 원래 위치에 남겼다.
- **전달/검증:** Saved/QA/CharacterPipeline/sparrow-short-bow-study-20261024/preview.html. 좌측에 실제 원본 활을 CSS로 확대하고 우측에 선택안을 두었다. C1~C4 이미지 로딩·전환·가로넘침없음 확인, 원본/시안 비교 화면을 직접 검토했다. browser-proof.png/browser-verified.json/result.json 참조. 실제 원본 장면 기준으로 구조를 다시 잡았지만 사용자 미적 승인은 대기다.
- **정리:** 실패한 임시 clip PNG4장만 경로 검사 후 제거했다. 원본 전체 캡처2장·생성원본4장·workspace시안4장·프롬프트·결과는 보존. 추가 게임 검사나 빌드는 하지 않았다.

## 50. 10-24 쇼츠 내 다른 활 형태 누락 교정

- **교정:** 사용자가 쇼츠에 §49의 활만 있는 게 아니라고 지적했다. 이전 26초대 일반 VI만으로 시안을 만든 범위 누락을 인정했다. 전체 타임라인 0/5/10/15/20/25/30/35/40초와 10.833초 세부 프레임을 직접 확인했다.
- **구분:** 2013 초기/2020 구간은 작고 독립된 여러 문양 활 배치, 2022 리마스터는 곡선 문양 몸체+직선 부채꼴 광선, 2024 일반 VI는 겹친 긴 몸체, 별도 강화 공격은 넓고 굵은 앞몸체와 큰 중앙 촉이다. 후반 딜사이클은 일반/강화 반복이며 별도 새 계열로 만들지 않았다. 2020이 동일 에셋이라는 코드상 단정은 하지 않는다.
- **산출물:** sparrow-short-bow-family-20261024의 R1 초기 다중 소환궁/R2 문양과 부채꼴 광선궁/R4 강화 대궁을 각 원본 캡처를 직접 참고해 내장 이미지 생성으로 새로 만들었다. R3은 §49 C1 재사용임을 명시한다. 황금·흰색 2D 형태 시안이며 운영 설치·C++·게임 에셋·빌드 변경 없음. 강화형 첫 그림의 상단 여백을 별도 편집으로 보강한 R4-v2가 최종이며 실패 프레이밍의 workspace 임시 복사본만 제거했다. 생성 원본은 보존.
- **전달/검증:** Saved/QA/CharacterPipeline/sparrow-short-bow-family-20261024/preview.html. 탭마다 해당 원본 캡처/원본시점/시안이 함께 바뀐다. 원본 이미지5장(일반형은 이전 경로 재사용), 새시안3장/재사용1장 표시, 전환/가로넘침없음/실제 비교화면 확인. art/prompts.json/result.json/browser-verified.json/browser-proof.png에 근거를 남긴다. 사용자 선택 대기.


## 51. 10-24 쇼츠 네 활의 실제 게임 비교 · 과한 톤 재검토

- **요청/범위:** 사용자가 §50 R1~R4를 게임에 적용한 시안을 요청했다. `sparrow_ew_reference_studies.py`에 `SPARROW_EW_FAMILY=1` 분기를 추가해 실제 Sparrow E에 연결한 비교 영상4개를 만들었다. 현재 운영 E의 선택 재질·C++·피해·입력·DLL은 보존했고, 기본 후보를 고정 설치하지 않았다.
- **구현:** Previews/BowFamily20261024의 T_R1~R4/M_R1~R4만 저작. 원본2D 파일은 유지하고 게임 재질에서 남색 배경/정적 화살을 제거, 좌우반전·개방·시위 응축·반동·소멸을 처리한다. R1은 세 부분을 분리해 순차 개방, R2는 문양/부채광, R3는 겹친 층, R4는 큰 몸체를 강조했다. 화살 제거가 활 중앙까지 끊는 문제는 축 위·아래 몸체 샘플로 좁게 연결했고 R3/R4의 남은 정적 시위도 정리했다. 실제 접촉에 기존 .055초 간격 두 pulse/42 작은 파편을 연결한다. 그림 기반 평면 시안이며 완성된 3D 활 에셋으로 주장하지 않는다.
- **검증:** 첫 pilot30은 HLSL 닫는 괄호 누락으로 재질 실패, 반려 기록 보존. 수정한 pilot-fixed30 기능20체크 뒤 중앙 끊김을 확인해 재촬영했다. 최종 R1/R2는 review30(전체38체크), R3/R4는 join34-final30(20체크) 실제 화면을 사용한다. 모두 한 화살/.333초 발사/60피해 한 번/복귀·임시효과정리. 최종 HLSL 오류 없음. 운영 E 소스4/Feather재질/DebugGameDLL 전후와 최종 해시 일치. 기능 확인은 미적 품질 승인을 뜻하지 않는다.
- **전달/정리:** `Saved/QA/CharacterPipeline/sparrow-bow-family-game-20261024/preview.html`. 4MP4 각30fps/42프레임/1.4초/1280×720 전체 디코딩. 최종 브라우저 네 영상 readyState4/시간진행/오류0/이미지4장/가로넘침없음/.28초 동시 탐색 확인. 기존 사용자 탭23은 유지, 임시 검토 탭28은 닫았다. 번호형 임시PNG420개/784,357,619bytes만 삭제, 최종9미디어 변경0·삭제잔여0. 대표 캡처/소스/재질/로그/JSON/그림/영상 보존. 빌드·커밋·push·사용자 프로세스 종료 없음.
- **최신 사용자 피드백/다음 방향:** 실제 게임에 넣으니 어색하고 과하다고 평가했으며, 레퍼런스 느낌만 살려 톤을 맞추는 방법을 질문했다. 부모 제안은 R3의 긴 곡선을 한 겹 중심으로 단순화, 크기·넓은 금색 면·불투명도를 줄이고 황금/상아색 빛결과 개방 동작을 남기며 발사 순간에 밝기를 집중하는 것. 새 톤 작업은 아직 적용하지 않았다. 기존 4안은 선택용 근거이며 사용자 채택으로 보지 않는다.


## 52. 10-24~25 Sparrow S 샤프 슈터 실제 적용

- **요청/범위:** 사용자는 대형 활 R1~R4가 과하다고 판단해 다른 용도로 쓸 수 있도록 보관을 요청하고, 이전 샤프 슈터 적용을 요청했다. 이번 운영 변경은 2번 캐릭터 S다. R1~R4 원본·시안·게임 비교는 보존했으며 운영 E에 설치하지 않았다. 사용자 요청에 따른 보관 메모도 남겼다.
- **원본/What·Why·How:** J2JoIe01BEI의 07:10 샤프 슈터를 브라우저에서 정지·프레임 전진하며 431.22~431.75초를 직접 관찰했다. 활 앞에 여러 작은 빈 타원 윤곽이 생기고 짧은 화살을 방출하는 구조를 황금·상아색으로 적용했다. 큰 활 대신 한 평면 재질 M_SparrowSharpMuzzle의 다섯 개 분절 발사구가 .17초에 펼쳐지고 3회 사격과 동기화한 뒤 .64초까지 소멸한다. 원본과 동일한 화살 수/완성도를 주장하지 않는다.
- **기능:** 기존 dormant ASparrowSharpVolley를 슬롯9/S의 sanctuary 경로에 연결했다. 0.68초 시전, .20초 첫 발사/간격 .12초, 3회×9발, 회당 대상별18피해/최대54, 1200cm, 8초 쿨다운. 기존 F 분기와 취소·종료 처리를 유지한다. HUD Sharp Shooter/3 volleys/54 damage/1200cm. Q 회복 QA의 과거 S 빈칸 기대값도 새 S 시전/복귀 기대값으로 맞췄으며 Q 게임 코드는 변경하지 않았다.
- **수정 파일:** SparrowSkillComponentSanctuary.cpp, SparrowSharpVolley.cpp/.h, sparrow_sharp_surface.py, sparrow_q_recovery_review.py 및 소유 재질 M_SparrowSharpMuzzle. before의 SharpVolley 소스는 첫 읽기에서 재구성한 참고본으로 byte-exact 백업은 아니다. 다른 운영 스킬은 이번 편집 대상 밖이며 전체 파일 해시 불변을 주장하지 않는다.
- **검증/시각 반복:** DebugGameEditor18.50초/DevelopmentEditor14.96초/DevelopmentGame24.05초 성공. final30의101검사(S/취소/벽/전환/쿨다운/변신→S→Space→평타→이동/F) 통과. 첫 visual30의 HLSL 예약어 point 오류를 rimPoint로 수정했고 실패 기록은 보존했다. v1은 두꺼운 도넛처럼 보여 반려, v2는 너무 희미해 반려했다. 최종 v3 balanced30의14검사와 실제 .20/.40초 화면을 확인했다. 최종 재질 오류 없음. 실제 27발/대상별 최대54/벽 차단/취소 후 피해0/상태정리/시전 후 실제 이동 복귀 확인. 이는 사용자 미적 승인을 대신하지 않는다.
- **전달:** Saved/QA/CharacterPipeline/sparrow-sharp-shooter-20261024/preview.html 및 result.json. 최종 영상은 balanced30 실제 PIE38프레임/30fps/1.2667초/1280×720 H264이며 전체 디코딩 통과. 10-25 로컬 서버가 중단돼 같은 QA 루트의 127.0.0.1:55811 서버를 다시 열었다. 브라우저 readyState4/재생/오류없음/반속/.40초 탐색/확대/가로넘침없음과 실제 프레임 표시 확인, 최종 탭을 열어뒀다. browser-proof.png/browser-verified.json 보존.
- **정리/상태:** 재생 확인 후 visual-fixed30/final30/balanced30의 번호형 PNG114개/214,694,207bytes만 삭제했다. S.mp4/포스터/HTML 해시 불변, 삭제 잔여0. 이름 있는 대표 캡처·참고 원본·소스·재질·실패 로그·JSON 보존. 배포 패키징/성능계측/커밋/push 없음. 이번 S 적용·빌드·기능/화면 검증·전달 완료이며 사용자 실제 피드백은 대기다. 전체 과거 1·2번 스킬 품질 완료를 의미하지 않는다.

- **10-25 S 발사 방식 반려/재검토:** 사용자는 이펙트만이 아니라 화살 출발·진행을 다시 보라고 지적했고 근거리 스킬 느낌을 명시했다. 원본430.887~431.787초를 60fps 프레임 전진으로 재관찰했다. 431.09~.49의 다층 발사구 응축 뒤 .59~.62에 서로 떨어진 위치의 짧은 화살이 보이고 .64 부근 방출·표적 타격이 함께 강해진다. 현재 ReleaseWave는 같은 Origin의 ±20도/1200cm/3×9발/.12초 원거리 파동이며, 여러 고리 위치와 실제 화살 출발이 연결되지 않는다. 앞 단계는 모양을 중심으로 재현하고 발사 구조를 충분히 확인하지 못했다. 수정 방향은 다층 발사구별 출발→짧은 응축→근거리 밀집 방출·접촉을 한 리듬으로 묶는 것. 원본 정확 발수/실제 사거리 수치는 영상만으로 확정하지 않는다. 이번은 재검토이며 runtime/빌드 변경 없음. reference-recheck-20261025의 원본3장/현재1장/review.json을 보존했고 result.json의 미적 상태를 rejected로 정정했다. §52의 구현·기능 완료와 사용자 의도 충족은 구분한다.


## 53. 10-25 Sparrow S 발사 방식 재구현 · 근거리 밀집 사격

- **승인/범위:** §52 재검토 뒤 사용자가 방향을 잡았다면 작업하라고 승인했다. 운영 2번 S를 변경했다. 원본의 다층 출발점/응축/짧은 방출·타격 흐름을 기준으로 하며 정확한 원본 발수·사거리 수치 복제는 아니다. 보관된 대형 활 R1~R4는 설치하지 않는다.
- **What/Why/How:** 기존 한 지점 ±20도/12m/3×9발을 제거했다. 다섯 독립 발사구와 준비 화살을 만들고 표시 좌표에서 실제 3발씩 총15발을 한 번 방출한다. 준비 .38초, 속도6000cm/s, 발사구에서 사거리450cm, 전체 시전 .68초/쿨타임8초. 위아래·좌우로 분산된 출발점과 작은 각도 차로 가까운 앞 공간을 채운다. 모든 화살이 공유하는 피격 집합으로 대상별54피해 한 번을 유지한다. 발사구가 벽 너머에서 시작하지 않도록 본체→발사구 WorldStatic/WorldDynamic 선검사를 하고 실제 비행은 기존 sweep/벽 차단/owner 정리를 재사용한다.
- **동작/외형:** 당김→한 번의 반동→복귀 몽타주로 바꿨다. 발사 후 발사구는 출발 위치에 고정하고 짧게 반동/소멸한다. S 전용 M_SparrowSharpMuzzle(v5), M_SparrowSharpTip, M_SparrowSharpStreak을 저작해 흰 광핵·금빛 가장자리로 준비 화살과 비행을 맞췄다. 공용 SparrowArrow에는 S가 명시 호출하는 EnableSharpBurstPresentation만 추가했다. 이동거리에 맞춰12~105cm 꼬리가 자라므로 발사구 뒤로 긴 꼬리가 뻗지 않는다. 실제 명중의 기존 파열은 S에서만 .90배로 사용한다. R 등의 원래 재질/피해 경로는 바꾸지 않았다.
- **검증:** pilot30의18검사 통과 뒤 금속선처럼 보이는 화살 재질을 전용 광핵으로 보강했다. final30은 S/S_spread/S_cancel까지 통과했으나 새 S_move_cancel 검사에서 실패했다. 실제 KwangPlayerController::MoveToCursor는 궁수 공격을 취소하지 않고 이동 한 건을 예약하는 정상 설계였으므로 게임 코드는 바꾸지 않고 S_queued_move로 검사 기대값을 바로잡았다. 회복 관련 recovery30 103검사(S_queued_move/벽/전환/쿨다운/변신→S→Space→평타→이동/F)와 최종 final60 66검사(S/S_spread/S_cancel/S_queued_move) 모두 통과했다. 실패 run은 성공으로 덮어쓰지 않았다.
- **실측:** 가까운 표적54/멀리650cm 표적0/측면 범위 밖0, 가까운 좌우 두 표적 각각54. 실제15발/단일방출/다섯 발사구와 모든 화살 시작점 일치/각450cm. 발사 로그 age30fps .400,60fps .383. 명시 취소와 전환은 후속 피해0, 벽뒤0, 예약 이동246cm 및 후속 이동 복귀. 최종 재사용 로드에서는 재질 컴파일 실패 없음. author 중 그래프 연결 전 UV 입력 경고는 마지막 컴파일·실제 화면·다음 재사용 로드와 구분한다.
- **빌드/전달:** 최종 DebugGameEditor6.48초/DevelopmentEditor15.06초/DevelopmentGame24.33초 성공. Play-CurrentSkills.cmd와 일반 실행 모듈 갱신. Saved/QA/CharacterPipeline/sparrow-sharp-close-20261025/preview.html의 최종 실제 영상은 final60의75프레임/60fps/1.25초/1280×720 MP4다. 전체 디코딩/브라우저 readyState4/실제 프레임/재생/반속/.417초 탐색/확대/원본 이미지 로딩/가로넘침없음을 확인하고 사용자 탭을 새 영상으로 이동했다. 이전 S 비교 링크 유지.
- **정리/한계:** 이번 번호형 PNG151장/284,302,537bytes만 삭제, 최종 MP4/포스터/HTML 해시 불변·잔여0. 대표 프레임·이전본·소스/원본재질 백업·새 재질·로그/JSON 보존. 배포 패키징/성능계측/커밋/push 없음. 실제 발사 구조·기능·화면을 확인한 적용본이며 사용자 미적 승인은 대기다.

- **10-25 S 이펙트 재검토:** 사용자는 근거리 발사 방향은 가까워졌으나 이펙트를 원본과 다시 비교하라고 요청했다. 원본430.947~432.031초를 전체화면/60fps 프레임 전진으로 재관찰하고 현재 final60의 .20/.36/.40/.47초와 비교했다. 원본은 큰 겹친 타원 윤곽이 작은 발사구로 응축되고, 방출광·가는 빛줄기·표적의 집중 타격광이 짧게 겹친다. 현재는 작은 고리가 커져 머물고, 실체 윤곽이 강한 흰 화살 묶음/금색 테두리/기존 금색 파열이 분리되어 보인다. 발사 위치·사거리 변경만으로 이 질감과 강약까지 맞췄다고 볼 수 없다. 다음 수정 범위는 S 전용 전개→응축 곡선, 발사부 짧은 방출광, 가는 광핵/잔상, 집중 타격광이며 황금·흰색과 근거리 판정은 유지하는 방향이다. 이번 요청에서는 게임 코드/에셋/빌드 변경 없이 재검토만 수행했다. 근거와 4단계 비교는 sparrow-sharp-close-20261025/effect-recheck/index.html 및 review.json에 보존한다.

## 54. 10-25 Sparrow S 겹친 타원·응축·두 번째 파동 / 화살 형상 통일

- **요청/What·Why:** 사용자가 원본의 큰 겹친 타원→축소→다시 원형 이펙트가 나오며 파팍 방출되는 순서를 명확히 지정하고, 불규칙한 화살 형상과 빈약한 효과를 보강하라고 요청했다. 이번 적용 범위는 2번 S의 외형이다.
- **How:** 다섯 발사구 좌표는 유지하고 각 표시 평면을54→180cm로 확대했다. M_SparrowSharpMuzzle은 .08초까지 명목 지름133cm의 겹친 타원을 펼친 뒤 .14~.34초에36cm로 압축한다. 별도 M_SparrowSharpRelease/230cm 평면은 발사에 맞춰 두 번(.05초 간격) 밝아지며 큰 원형 파동을 퍼뜨린다. 시작 응축광·테두리 밝기 변화·잔광을 추가했다. 초기 v6은 선으로 그린 듯 보여 v7에서 질감/중심광을 보강했고, v8에서 작은 발사구 소멸과 두 번째 파동의 확대를 앞당겨 방출에 맞췄다.
- **화살/영향:** S만 부르는 EnableSharpBurstPresentation에서 실물 ArrowMesh를 숨기고, M_SparrowSharpStreak의 대칭 촉·곧은 흰 광핵·금빛 외곽을 교차 평면 두 개로 사용한다. 준비 화살에도 같은 표면을 쓴다. 같은 길이/폭과 이동거리 기반 꼬리(16~135cm)로 랜덤 실물 윤곽을 없앴다. ReleaseWave 본문은 before와 텍스트 일치하며15발/54피해/450cm/6000cm/s/.38발사/.68시전/8초쿨타임 및 실제 사격 방향을 유지한다. R 등 다른 스킬은 이 opt-in 표면을 사용하지 않는다.
- **검증:** visual60의 S/명시취소30검사 통과, 최종 polished60의 S18검사 통과. 실제 피해[54,0,0], 단일방출/15발/다섯 실제 출발점 일치, 시전 후 이동246.8cm 확인. 최종 DebugGameEditor6.23초/DevelopmentEditor11.80초/DevelopmentGame24.67초 성공. 최종75프레임/60fps/1.25초/1280×720 실제 영상 전체 디코딩과 브라우저 재생/반속/단계 탐색을 확인했다. 질감·광량에 대한 사용자 미적 승인은 별도다.
- **전달/정리:** Saved/QA/CharacterPipeline/sparrow-sharp-pressure-20261025/preview.html 및 result.json. 페이지에서 전개·응축·화살·두 번째 파동으로 탐색하고 수정 전 영상/원본 비교에 접근할 수 있다. 번호형 임시 촬영 PNG만 raw-cleanup.json의 범위에서 삭제했고 MP4/포스터/HTML 해시 불변을 확인했다. 대표 캡처·소스/에셋 before·로그/결과는 보존. 원본 에셋 저장, 배포 패키징, 커밋/push, 사용자 프로세스 강제 종료 없음.

## 55. 10-25 Sparrow S 평행 화살 / 불규칙한 겹침 4개 선택 시안

- **What/Why:** 사용자가 화살이 바깥으로 퍼지지 않고 평행하게 나가야 하며 처음 고리들이 서로 겹치고 불규칙해야 한다고 지정했다. 실제 화살의 각도 분산을 제거하고, 고리 외형은 C1~C4 선택용 시안으로 제작했다. 기본 효과는 이전 스타일0을 유지하며 미적 채택은 대기다.
- **How/영향:** SparrowSharpVolley::ReleaseWave에서 15발 모두 동일 Direction을 사용한다. 발사구 안의 3개 시작점만 좌우8cm씩 나누며 각 시작점까지 벽 검사를 한다. 대상별54피해/발사구 기준450cm/6000cm/s/.38발사/.68시전/8초쿨타임은 유지한다. 사거리가 멀어질수록 좌우로 넓어지던 사격 범위는 줄어든다. R 등 다른 스킬 화살은 변경하지 않았다.
- **시안:** Sparrow.Sharp.Preview=1~4는 C1 크기·위치·각도가 다른 겹친 타원, C2 기울어진 얇은 교차층, C3 끊어지고 흔들리는 빛의 윤곽, C4 회전하며 감기는 나선이다. 각 고리는 다른 전개 형태에서 .35초까지 공통 발사구로 모이며 .38초 단일 방출/두 번째 파동으로 이어진다. sparrow_sharp_concepts.py가 SharpConcepts 폴더의 전용 재질8개만 저장한다. 운영 M_SparrowSharpMuzzle/Release/Streak은 before와 해시가 같다. 기본값0이며 QA 종료 시0으로 복구한다.
- **검증:** field60 실제 입력 S/C1/C2/C3/C4/좁아진 범위/벽/명시취소 총134검사 통과. 15발 평행 방향 일치, 가까운 표적54/먼·측면0, 가까운 두 표적 각각54, 벽·취소0, 시전 후 이동246cm 이상 확인. DebugGameEditor6.27초/DevelopmentEditor8.44초/DevelopmentGame17.41초 성공. 첫 DebugGame 빌드의 Layers 이름 충돌은 LayerScales로 고쳤으며 실패 로그를 보존한다.
- **전달:** Saved/QA/CharacterPipeline/sparrow-sharp-concepts-20261025/preview.html. 기본1+시안4개는 각75프레임/60fps/1.25초/1280×720 실제 영상이다. comparison.mp4는 네 영상의 동일 영역을 자른4분할 비교다. 전체 디코딩, 브라우저4개 readyState4/오류0/동시 재생/반속/.10·.43초 탐색/개별 확대/가로넘침없음을 확인했다. 초기 비교영상의 기본폰트 탐색 오류는 Windows Arial 명시로 해결했다. result.json/media-manifest.json/browser-verified.json에 근거가 있다.
- **정리:** 이번 field60/screenshots의 번호형 PNG375개/707,126,410bytes만 삭제했다. 영상·포스터·HTML·브라우저대표화면13개 해시불변, 삭제잔여0. 대표 타이밍 캡처·백업·소스·로그·JSON·시안 재질은 보존했다. 사용자 프로세스 종료, 배포 패키징, 성능계측, 커밋/push 없음.

## 56. 10-25 S 시안 해석 정정: 원 윤곽은 깨끗하게, 크기와 배치만 불규칙

- **사용자 정정:** §55의 찌그러진 윤곽·기울기·끊김·나선은 오해였다. 사용자가 말한 불규칙은 원마다 크고 작은 크기 차이이며 원 자체는 깔끔한 원이어야 한다. 이전 시안 result.json은 rejected로 기록했다. 향후 이 문장을 우선한다.
- **What/How:** 시안 전용 재질v2는 반지름을 시간에만 의존하게 하고 각도에 따른 왜곡/끊김을 제거했다. 각 원은 로컬X/Y 동일 배율·공통 방향을 사용하며, 크기와 배치만 C1 대중소 혼합/C2 큰 원 두 개/C3 큰 원 하나 중심/C4 비대칭 겹침으로 바꿨다. 게임 시점의 원근에 의해 타원으로 보이는 투영은 유지한다. 평행15발/단발 방출/응축/두 번째 원형 파동은 유지하며 이번 정정은 opt-in 시각 시안만 바꾼다. 기본값0과 운영 재질3개 해시는 그대로다.
- **검증:** field60 네 시안73검사 통과. 첫 C1은 초기 카메라 위치가 달라 전달에서 제외하고, S로 준비한 뒤 C1만 다시 촬영한 aligned60의37검사 통과본으로 대체했다. C2~C4는 field60을 사용한다. 각 가까운 표적54/멀리·측면0, 15발 평행, 시전 후246cm 이동 확인. DebugGameEditor6.24초/DevelopmentEditor6.68초/DevelopmentGame14.74초 성공.
- **전달/정리:** Saved/QA/CharacterPipeline/sparrow-sharp-circles-20261025/preview.html 및 comparison.mp4. 실제4개 영상75프레임/60fps/1.25초 및4분할 영상 전체 디코딩, 브라우저4개 로딩·재생·.10초 정지·가로넘침없음 확인. 사용자 선택 전 기본 효과 교체 없음. field60/aligned60 번호형PNG450개/848,479,817bytes만 삭제, 최종영상/포스터/HTML/대표화면11개 해시 불변·잔여0. 대표 캡처/반려 원본/로그/소스/재질 보존. result.json에 현재 상태 기록.


## 57. 10-26 Sparrow S 발광·잔상·타격 리듬 보완 완료

- **승인/범위:** 사용자가 §56 원형 시안의 모양은 비슷하지만 원본 느낌이 다르다고 지적한 뒤 개선 진행을 승인했다. C1의 깨끗한 대중소 원 배치를 기본 S에 적용하고, 외형·광량·시간 흐름만 보완했다. 2번 S 외 기존 작업은 유지한다. 원본과 동일한 미적 완성도를 달성했다는 뜻은 아니며 사용자 평가는 대기다.
- **What/Why/How:** M_SparrowSharpMuzzle v10에서 원의 각도별 찌그러짐을 제거하고 얇은 윤곽·부드러운 발광층을 분리했다. 응축 구간을 .105~.265초로 앞당겨 작은 발사구에서 힘을 모으고 .38초에 방출한다. Release는 .16초 내 두 파동과 흰 중심광으로 강약을 만든다. 준비·비행 화살은 같은 가늘고 짧은 표면을 쓰며 비행 꼬리는12~86cm로 줄였다. 모든15발의 평행 방향·450cm·54피해·.68초 시전·8초 쿨타임은 유지한다.
- **명중 표현/영향:** 기존 P_Sparrow_UltHit의 런타임 복제본에서 Flare/Main Flames/Line Burst/Sparks/SparkTrailHeads만 짧게 방출하고 Light 모듈은 제거한다. 원본 에셋은 저장하지 않는다. 실제 피해가 승인된 대상에만 .20초 수명의 SparrowSharpImpact 시각 액터를1개 생성해 흰 중심광과 짧은 잔광을 추가했다. 충돌·피해·이동 판정은 소유하지 않는다. 다른 스킬은 이 S 전용 경로를 사용하지 않는다.
- **검증:** pilot60은44체크 통과했으나 명중 중심광이 약해 최종 영상에서 제외했다. final60 실제 S/S_spread/S_cancel/S_wall 총66체크 통과. 단일15발·평행·다섯 발사구와 시작점·거리 확인, 가까운 표적54/멀리·측면0, 가까운 두 표적 각각54, 대상당 중심광1개 및 소멸, 취소·벽뒤 피해0, 시전 후246cm 이동을 확인했다. 최종 .10/.43/.47초 실제 화면에서 전개·방출·접촉광을 검토했다. author 도중 그래프 연결 전 ComponentMask 입력 경고는 최종 연결·저장 후 실제 렌더와 구분한다.
- **빌드/전달:** DebugGameEditor 최종 빌드 성공. 재개 후10-26 DevelopmentEditor7.95초/DevelopmentGame72.51초 성공. Saved/QA/CharacterPipeline/sparrow-sharp-radiance-20261025/preview.html에 실제 적용 S 및 이전 C1 전후 비교, 원본 단계별 캡처를 함께 제공한다. 최종 S.mp4는 final60의75프레임/60fps/1.25초/1280×720. comparison.mp4는 동일 영역을 자른 전후 비교다. 두 MP4 전체 디코딩, 브라우저 동시 재생·반속·.43초 탐색·이미지 로딩·가로넘침없음·오류없음을 확인하고 정상 속도 수정본을 열어두었다. 오래된 로컬 서버가 종료되어127.0.0.1:55811에 다시 시작했다.
- **정리:** pilot60/final60 번호형 임시PNG150장/282,778,201bytes만 사전 경로 검사 후 삭제했다. 보호한 최종미디어5개 해시불변·삭제잔여0. 대표 캡처·소스와 재질 백업·로그·JSON·MP4·HTML은 보존한다. result.json/browser-verified.json/media-manifest.json/raw-cleanup.json에 근거가 있다. 패키징·성능계측·커밋/push는 수행하지 않았다.

## 58. 10-26 Sparrow S 디테일·화려함 4개 실제 게임 시안

- **최신 기준:** 사용자는 큰 방향은 어느 정도 맞고 디테일·화려함이 부족하다고 정정했다. 이어 “반드시 레퍼런스를 따라갈 필요는 없고 사람이 보기에도 화려해 보이는 것이 목적”이라고 명시했다. 원본 유사성이나 입자 수 자체를 품질 목표로 삼지 않는다. 이번 요청은 여러 시안이며 기본 S 채택은 별도다.
- **What/Why/How:** T1 백금 겹빛/T2 황금 성진/T3 광사 흐름/T4 집중 파열을 준비·방출·화살·명중의 네 재질로 각각 저작했다. 프로젝트 Perlin 노이즈로 내부 발광과 흐르는 빛결을 넣었다. 첫 촬영은 가는 도형처럼 읽혀 반려했고, v2에서 넓은 발광층·입자 밀도를 보강하고 규칙적인 바퀴살/점무늬를 줄였다. T1은 면 발광이 강하고 T2는 금빛 광점, T3는 흐르는 결, T4는 짧은 파열을 강조한다. 사용자 미적 승인은 대기다.
- **범위/영향:** Sparrow.Sharp.DetailPreview=1~4의 선택용 분기이며 기본값0. 새로운 SharpDetails20261026 폴더의16개 재질만 저장한다. ASparrowSharpVolley가 선택을 Arrow→SharpImpact까지 전달하며 준비부터 실제 접촉까지 같은 스타일을 쓴다. 원 배치·15발 평행·.38초 발사·.68초 시전·450cm·54피해는 보존했다. 운영 Sharp 재질5개 해시 불변. 기존 C1~C4 시안은 덮어쓰지 않았다.
- **검증:** DebugGameEditor 빌드66.18초 성공. field60은113체크, 최종 refined60은93체크 통과. 시안 각각 단일 평행 사격/표적 피해/명중광 정리/이동 복귀 확인, 최종 재질·Python 오류 없음. 초기 엔진 구동의 AutomationTest Condition failed 로그는 두 촬영에 공통으로 존재하며 전체 엔진 로그 무오류라고 주장하지 않는다. 실제 .10초 전개 및 방출 화면을 검토했다. 선택용 시안이므로 일반 DevelopmentEditor/Game을 다시 빌드하지 않았다.
- **전달:** Saved/QA/CharacterPipeline/sparrow-sharp-details-20261026/preview.html. 기본 S는 field60, 최종 T1~T4는 refined60의75프레임/60fps/1.25초 실제 PIE 영상이다. comparison.mp4는 네 시안 동일 영역4분할. 전체 디코딩/브라우저5영상 readyState4·시간진행·오류0·반속·전개/응축/타격 탐색·선택 전환·가로넘침없음 확인. 기본 S/T2 정상속도 비교로 열어두었다. result.json/media-manifest.json/browser-four-studies.png 및 소스 before 보존.
- **정리:** 두 촬영의 번호형 임시PNG675장/1,272,547,617bytes만 사전 경로 검사 후 삭제. 최종미디어/HTML/대표화면13개 해시 불변, 삭제잔여0. 이름 있는 대표 캡처·소스·로그·재질·최종 영상은 보존했다. 기본 효과 채택·배포 패키징·성능계측·커밋·push·사용자 프로세스 종료 없음.

## 59. 10-26 Sparrow S 광류 응축·전방 파열 M1 시안

- **사용자 피드백/승인:** §58 네 시안 모두 밋밋하다는 평가. 원 내부의 작은 무늬·입자·광량 변화에만 치우쳤고 정상 시야에서 디테일이 안 읽히며 응축 때 하얗게 뭉친다는 분석 뒤, 사용자가 새 연출 시도를 승인했다. 이번도 선택용 시안이며 기본 S 채택은 아니다.
- **What/Why/How:** DetailPreview=5(M1)를 추가했다. Muzzle은 완전한 원형 윤곽에 밝기가 다른 이동 광호와 안으로 감기는 빛을 두고 중심은 작은 광핵만 남긴다. 다섯 발사구마다 별도 Flow 평면을 추가해 뒤쪽에서 들어오는 금빛 흐름과 발사 후 전방 잔광을 표현한다. Release의 두 파동·짧은 광편, 실제 명중의 전방 파편까지 연결했다. 기존 T1~T4 및 운영 재질은 보존했다.
- **영향/기능:** S 시각 전용 분기이며 기본값0. 새 평면은 충돌/피해를 갖지 않는다. 실제15발 평행·54피해·450cm·.38초 발사·.68초 시전은 유지한다. 발사 후 잔광 길이는 발사구부터 월드 장애물 선검사로 제한하고 소유 Volley 종료/취소 때 함께 정리한다. Impact는 M1에서만 사격축 방향으로 펼친200×170cm 평면을 사용하며 .20초 수명은 유지한다.
- **반복/실패:** pilot60의 Flow HLSL 변수명 line이 예약어라 회색 기본 재질로 렌더됐다. beamCore로 수정했고 pilot 후보 영상은 제외했다. final60에서 실제 흐름은 확인했으나 유입 선이 철사처럼 보이고 직선 잔광이 길어, 최종 polished60에서 유입 가닥을 줄이고 금빛 가장자리·짧은 잔광으로 조정했다. 그래프 재작성 중 Missing ComponentMask input 경고는 최종 연결/저장 이전의 것이며 최종 PIE 구간에는 재질 컴파일 오류가 없다.
- **검증:** DebugGameEditor26.67초 성공. pilot60 기능85체크에서 기본 S/M1/취소/벽을 확인했고 벽 전면과 잔광 끝 사이 약3cm 확보, 취소·벽뒤 피해0, 정상54피해/평행15발, 이동246cm 복귀를 확인했다. native 변경 없이 재질만 고친 final60·polished60 각각35체크 통과. 최종 .10/.20/.43/.47초 게임 시야를 직접 검토했다. 운영 Sharp 재질5개 해시 불변. 기능 통과는 사용자 미적 승인과 구분한다.
- **전달:** Saved/QA/CharacterPipeline/sparrow-sharp-flow-20261026/preview.html. M1은 polished60의75프레임/60fps/1.25초 실제 PIE 영상. 기본 S는 pilot60의 정상 기본분기 영상, 이전 T2는 §58 최종 MP4를 그대로 재사용한다. comparison.mp4는 이전 T2와 M1 동일 영역 비교.4개 MP4 전체 디코딩, 브라우저 재생/반속/단계 탐색/기본 S·이전 T2 전환/원래 게임 시야/가로넘침없음 확인. T2/M1 정상 속도 비교로 열어두었다.
- **정리:** 세 촬영의 번호형 PNG300장/565,450,181bytes만 사전 경로 검사 후 삭제, 보호한 최종 영상·포스터·HTML8개 불변·삭제잔여0. before/대표 캡처/실패 로그/JSON/소스/재질/영상 보존. 일반 Game/DevelopmentEditor 빌드·기본 채택·커밋·push·배포·사용자 프로세스 종료 없음. 다음 판단은 사용자 시안 피드백이다.

## 60. 10-26 Sparrow S 디자인 우선 탐색 · 2D 원화 6안

- **요청/범위:** 사용자는 기존 시안들이 밋밋하다며 더 다양하고 화려한 결과를 만드는 요청 방식을 다시 논의했고, 기존 방향 발전 2안과 새 발상 4안을 먼저 2D로 비교하는 방식을 승인했다. 이번 산출물은 AI 이미지 생성 원화이며 실제 게임 영상이나 구현된 애니메이션이 아니다. 게임 코드·재질·빌드는 변경하지 않았다.
- **디자인:** A 겹광륜 파열(겹친 원과 이동 광호), B 광류 매듭(뒤에서 감겨드는 빛줄기), C 빛의 장막(겹친 반투명 면), D 압축 폭풍(짧은 수평 회오리), E 황금 결정 파열(조립되는 결정과 파편), F 별빛 일제점화(입체 별빛 군집). A/B는 기존 방향 발전, C~F는 새 발상이다. 황금·흰색, 근거리 밀집 사격, 평행 화살을 공통 기준으로 두고 형태·움직임·질감을 달리했다. 각 원화는 전개→발사→명중 3행이다. A/C는 화살이 벌어지는 인상을 줄이도록 이미지 편집을 추가했다.
- **전달/검증:** Saved/QA/CharacterPipeline/sparrow-sharp-art-directions-20261026/preview.html에 6안 카드, 전개/발사/명중 동기 비교, 선택 원화 확대를 구성했다. art/A.png~F.png는 각1254×1254. 실제 브라우저에서 이미지7개 로딩, 단계 전환, D 상세 선택, 가로넘침없음과 화면 표시를 확인했다. browser-overview.png/browser-verified.json/result.json 보존. generation-manifest.json에 전체 프롬프트·수정·원본경로를 기록했다. 이미지 생성 원본은 기본 generated_images 위치에 보존했다.
- **다음 단계:** 사용자 선택 또는 부분 조합을 받은 뒤 움직이는 시안으로 확장한다. 이번 6안은 미적 승인이나 게임 채택을 의미하지 않는다. 런타임 화면의 밀도·시간축·타격감 검증은 이후 단계다.
- **이전 M1 페이지 표시 보완:** 사용자에게 검게 보인 MP4는 브라우저 재생 시간이 진행해도 픽셀이 검은 증상을 확인했다. sparrow-sharp-flow-20261026의 기존 비디오 페이지를 preview-video.html로 보존하고, preview.html에 M1/비교 animated WebP 정상속도·반속 및 정지 프레임 보기를 제공했다. 브라우저에서 실제 이미지 표시를 확인했다. 과거의 모든 영상 문제가 해결됐다는 뜻은 아니다.

## 61. 10-26 Sparrow S 원화 6안 실제 게임 구현 · B/F 전개 수정

- **요청/범위:** 사용자가 2번째 B와 마지막 F의 첫 전개만 수정하고 여섯 시안을 스킬로 만들어 확인하겠다고 요청했다. 2번 S의 A–F 비교 구현이며 기본 S 채택은 별도다. 기존 2D B/F 원화는 수정 전 기록으로 보존하고 변경된 전개는 게임 시안에 적용했다.
- **What/Why/How:** `Sparrow.Sharp.ArtPreview 1..6`을 시전 시작에 읽어 A 광륜/B 짧은 광류/C 접히는 장막/D 빈 중심 회오리/E 결정/F 광편 점화로 선택한다. B는 뒤까지 길게 감긴 매듭을 줄여 활 가까운 빛결로, F는 별자리 연결선 없이 작은 광편이 모여 점화되는 형태로 바꿨다. `SparrowSharpVolleyArt.cpp`의 소유 평면을 사용하고 모든 컴포넌트는 메시 지정 전 충돌·내비를 끈다. 새 `SharpArt20261026` 폴더의 준비/몸체/방출/화살/명중 30재질만 저작한다. 기본값0이며 기존 운영 재질 해시는 author 전후 동일하다.
- **실제 화면 반복:** pilot의 흰 윤곽이 과하게 뭉치고 D가 철사 코일처럼 보여 반려했다. refined에서 금빛 중간톤/투명한 면/국소 밝기 대비를 보강하고 D를 나선형 면으로 수정했다. F의 듬성한 전개에는 작은 광편 주변 잔광을 추가했다. 최종 새 시안 화살 폭만 .14→.24로 조정해 가는 중심축을 유지하며 촉을 읽기 쉽게 했다. 다른 스킬/기본 S 화살 폭은 유지한다.
- **검증:** pilot60 182체크(기본 S/6안/취소/벽), refined60 153, final60 153 통과. 각 안 실제15발 평행/대상당54/450cm/.38초 방출/.68초 시전/이동246.6cm 이상 복귀 확인. 취소·벽뒤 피해0은 gameplay 변경 전후 동일 경로인 pilot 근거를 재사용한다. DebugGameEditor 최종6.56초, DevelopmentEditor16.31초, DevelopmentGame34.50초 성공. 최초 sandbox 빌드가 dotnet 시작에서 멈춰 이번 작업 소유로 확인한 빌드 트리만 종료한 뒤 재시도했다. 사용자 에디터 종료 없음.
- **전달:** `Saved/QA/CharacterPipeline/sparrow-sharp-art-game-20261026/preview.html`. final60의 각75프레임/60fps/1.25초/1280×720 실제 PIE 영상6개. MP4 전체 디코딩 및 WebP12개 전체 프레임 디코딩 확인. 기본 표시는 움직이는 WebP이며 정상/반속/전개/응축/발사/명중/확대·일반 시야/개별 상세를 제공한다. 반속은 동일38프레임의 표시 시간을 두 배로 해 중복 프레임을 저장하지 않는다. 기본 S 교체/패키징/성능계측/미적 승인/커밋/push는 하지 않았다.
- **정리/근거:** `result.json`, `media-manifest.json`, `animation-decoded.json`, `browser-verified.json`, 빌드/PIE 로그와 before를 보존한다. 교체된 pilot/refined 번호형 캡처1050장1,980,687,756bytes를 경로·파일별 검사 후 삭제하고 잔여0 확인. 최종 캡처 정리는 `cleanup-final-result.json`을 확인한다. 이름 있는 대표 캡처/최종 영상/원화/저작 재질은 보존한다. 기능 완료와 사용자 외형 평가를 구분한다.

## 62. 10-26 Sparrow 시안 채택과 이동 복귀 수정

- 사용자 확정: 실제 S=문서A, D=빛 응축 B 재설계+F 광편, A=기존 톱니+D 회오리, F=E 결정질감의 단발. 문서 C/F는 독립안 폐기. `SparrowGatherShot`은 D/F 준비와 실제 발사 성공 후 방출만 담당하고 피해·벽·쿨다운은 원래 화살 경로를 사용한다. F가 구 counter ward로 우회하던 분기를 제거해 extra slot11로 연결했다.
- 반복 이동 이상은 사용자가 “스킬 뒤 잠깐 멈췄다가 움직임”이라고 확정했다. 실제 측정에서 pathAllowed=false는 없었고 발사 후 IsCasting 잠금이 원인이었다. 유효한 이동 목적지가 대기 중일 때 마지막 실탄 방출+.035초 이후 몽타주를 .035초에 블렌드 종료한다. R은 마지막 파동 뒤, S는 별도 volley recovery만 해제한다. 이미 방출한 화살·화살비는 계속한다.
- 60fps 실제 마지막 발사→이동은 A .367→.067초, S .317→.067초, Q/W/D/F도 .067초. E/R 기존 이동취소 정책 유지. Space는 착지(.267초)/변신 blink(.065초)에 제어를 돌려주고 잔상만 자체 수명까지 유지한다. 잔상 종료가 후속 A의 상태를 덮어쓰지 않는 것도 검사했다.
- pilot60/refined60/회복 전후60/회복30 모두 통과. 8키 실탄·피해, R186발6파동, 16연속입력, F벽/쿨다운/DF취소 확인. native DebugGameEditor 빌드 완료. 일반 DevelopmentEditor/Game은 이어지는 변신 강화 통합 후 빌드한다.
- 실제 영상: `Saved/QA/CharacterPipeline/sparrow-arsenal-adoption-20261026/preview.html`. S/D/A/F/Space/Blink 정상·반속 WebP와 MP4, 단계별 정지화면. 원본 번호형 PNG552장 1,045,076,162bytes 삭제, 최종미디어19개 해시 보존. before/보고서/재질/이름 있는 캡처 보존. 기능 통과와 사용자 미적 승인을 구분한다.

## 63. 10-26 Sparrow V 변신 8스킬 강화 · 날개 길이 축소

- 사용자 추가 지시: 날개를 조금 더 짧게, QWERASDF 모든 스킬을 변신 상태에서 강화. 일반 상태 보존, 피해/사거리/발사 수/쿨다운/시전 속도 변경 없이 표현만 분리했다. root는 E/S/D/F와 통합, ascended_qwer는 Q/W/R FX, saw_vortex는 A/날개, mobility_repair는 실제 입력 비교/이동 검사 담당. GPU PIE는 직렬 실행했다.
- 날개: 실제 펼침 본 좌표로 native component X가 길이 축임을 확인했다. scale(.8,.8,.8)→(.72,.8,.8), spine_03 기준점을 재고정. .8/1.2/1.7/2.3초 본 포즈 동일, 길이 축 span321.98→289.78cm, 다른축 동일, 부착점 최대차이0.31mm. 불꽃질감/WPO 유지. 전체3D 끝본거리는8.75% 줄었고 화면픽셀길이 정확히10%를 뜻하지 않는다. wing-length-comparison.json와 실제 전후 이미지 보존.
- What/Why/How: Q 상향광맥+낙하빛/국소파편, W 얇은 실탄 유지+활 응축/적접촉파편, E 내부광맥+개방불티/6개 끝장식, R 매파동 작은 광편(큰섬광 없음), A 역회전 외피/광맥/빠직임, S 겹광륜 깊이+불티, D14빛줄기/20광편, F18결정의 면/능선/방출. 새 AscendedArsenal20261026 및 ArsenalAscended20261026 재질20개 사용. 일반재질 경로는 그대로, 강화재질은 실제 변신일 때만 선택. QWR전용actor는 변신 만료/owner 소멸 정리; R 접촉강화는 적타격만, 벽에는 생성하지 않는다. 종료된 weak FX참조는 다음 변신QWR시전에서 정리한다.
- 화면 반복: 비교에서 E 차이가 약해 추가로 금빛 중간면/음각 대비를 보강했다. E의 단발 판정과 기존 활 형태는 유지했다. 다른7개는 처음 촬영한 적용본이며 일반/변신 실제 전개·방출·명중 화면을 검토했다. 미적 승인은 사용자 판단으로 남긴다.
- 검증: pilot 첫실행은 초기 Countess를 전환실패로 오판한 검사코드 오류로 중지(게임문제 아님). 수정한 pilot-fixed60은563체크, 16시전/8쌍 비교, 변신 이동8키, 자기발밑Q 통과. 모든쌍 피해/발사시점/실탄수 보존, 일반에 변신재질 유입 없음. 마지막 발사→이동 Q/W/A/S/D/F .0667초 E/R .0833초. refined-e60은 보완E와자기발밑Q 통과. 신규머티리얼/Python컴파일오류 없음. 기존엔진 startup AutomationTest 오류·Countess LevelStart 누락로그는 별개이며 전체로그 무오류를 주장하지 않는다.
- 빌드: 최종 DebugGameEditor7.10초, DevelopmentEditor64.99초, DevelopmentGame48.18초 성공. Play-CurrentSkills.cmd가 새 DebugGame DLL을 사용하며 게임을 새로 실행하면 적용된다. 패키징/실기성능벤치/커밋/push/사용자프로세스 종료 없음.
- 전달: `Saved/QA/CharacterPipeline/sparrow-ascended-arsenal-20261026/preview.html#A`. 8키 일반/변신16영상(MP4+정상/반속 WebP), 단계별PNG, 날개전후. 16MP4전체디코딩,32WebP전체프레임디코딩, CUA실제이미지표시/8키전환/반속/확대·일반시야/가로넘침없음 확인. 기본A정상재생으로열어두고 deliverable표시. result.json/media-manifest.json/browser-verified.json/browser-comparison.png 보존.
- 정리: 번호형 임시PNG2496장 4,724,815,261bytes 삭제, 당시보호미디어121개 해시보존, 잔여0. §62와 합해 약5.77GB 정리. 최종영상/이름있는근거캡처/소스before/로그/재질은 보존한다. 새 차이가 필요하면 이 페이지와 `sparrow_ascended_arsenal_materials.py`부터 확인하고 정상 상태에 강화분기를 무조건 설치하지 않는다.


## 64. 10-26 Sparrow 연사·금빛 궤적·화염 시안 및 근거리 이동 수정

- 사용자 추가 지시와 실제 방향 이동 문제를 통합 처리했다. root는 W/R 및 통합, mobility_repair는 입력·내비 재현, ascended_qwer는 Q/F, saw_vortex는 D/V 비교안 담당. GPU 촬영·빌드는 직렬 실행했다.
- 이동 원인: KwangPlayerController의 Idle 재진입 조건이 새 클릭에도 약75.4cm를 요구했다. 유효한74cm 목적지에8방향×대기/연속스킬×클릭/누름32건 모두0cm 이동을 재현했다. 새 클릭의 추가 제한을 제거하고 누름 재진입은 ExactLocation 정지거리31.5cm+25cm로 맞췄다. 같은32건 수정 후 전부 통과. 공용 컨트롤러의 Countess도 실제74cm, 투영변위0 조건으로 이동 확인. 일부 먼 목적지의 내비 우회는 원인 미확정이며 임의의 충돌 수정은 하지 않았다.
- Q는 원본 파티클을 저장하지 않고 런타임 복제에서 보라 Shockwave 제거, Trails 커브/최종 메시 발광/세 StartColor 층을 금빛으로 변경했다. 변신 Q는 바닥→위 황금 기둥8개. 피해40/8펄스/4초/범위300 유지. F는 실제 화살70cm 간격으로 깃털 잔광을 남기며 충돌·내비를 소유하지 않는다. 피해80/단발 유지.
- W는 얇은 화살4발/.18초, 총35 유지. 몽타주 자동 블렌드 종료가4번째를 자르던 문제와30fps 상대 타이머 누적 지연을 각각 수정했다. 절대 발사 시각+generation 검사, 취소/종료 타이머 해제. R은10×31=310발/.13초, 총60 유지. 화살·타격의 시각 크기만 절반; 활 발광/범위/충돌은 유지한다.
- D1 깃털창/D2 나선 화염/D3 광편 압력, V1 화염 외투/V2 공전 광염/V3 어깨·팔 화염깃을 실제 게임 비교안으로 제작했다. Sparrow.FlameStudy.D/V=1..3, 기본0. 기존 D/날개는 유지. D는 실제 관통 화살 추적/접촉 위치, V는 실제 변신 본체와 지속시간 사용. 표면 개선 촬영1회 추가, 새9재질 최종 컴파일 오류0. 미적 승인은 사용자 대기다.
- 최종30·60fps W/R 일반·변신 실탄수/피해/이동복귀, W/R 중단 후 추가발사0 및 재시전, Countess 근거리 이동, Sparrow 먼 목적지4방향 통과.60fps 마지막 발사→이동 W.0667/R.0833초,30fps W.10/R.1333초(입력 시점 포함). DebugGameEditor/DevelopmentEditor/DevelopmentGame 성공. Play-CurrentSkills.cmd --check 통과; 새 실행 필요.
- 전달: Saved/QA/CharacterPipeline/sparrow-salvo-flame-20261026/preview.html. Q/W/R/F 일반·변신8영상+D/V6안=14 실제 촬영. 최종 Q/W/D/V는 final60, R/F는 변경 없는 refined60 사용. MP4전체/28WebP 전체프레임 디코딩 통과. result.json/media-manifest.json/browser-verified.json 및 before/로그/검사JSON 보존. 임시 번호PNG 4722장/8934844920bytes 삭제, 보호미디어 해시 불변. 패키징/성능벤치/커밋/push 없음.


## 65. 10-26~27 Sparrow 하강광·날개 연사·결정 화살 및 R/S 비교안

- 완료 기록: 2026-10-27T00:55:24+09:00. 사용자 승인 범위는 Q일반 유지/Q변신 하강광, W 전방 원·약한 흔들림·변신 마무리 한 발, F 조립 화살/변신 삼각3발, A 외피 제거·톱니질감, D 깃털, V3 채택+진입광. R/S는 여러 선택용 시안이다. root 통합/W/검증, ascended_qwer Q/R/S, saw_vortex D/V/W보조, mobility_repair F/A/이동분석으로 나눴고 GPU 촬영/빌드는 직렬 진행했다.
- 적용: Q변신 가는 빛줄기가 하늘→바닥으로 빠르게 꽂힌다. W 원을65cm 전진, 흔들림 scale0.4. 일반4발, 변신4발 뒤 .42초 당김/전방 날개 접힘/5번째 한 발; 총35피해 유지. 상태를 시전 시작에 고정해 도중 변신 만료에도 발사 수가 변하지 않는다. F는 작은 결정이210cm 긴 화살로 합쳐지고, 변신은 같은 방향의3발/끝점 삼각형(약56cm 변)으로 발사. 공유 타격집합으로 대상당80피해 유지. A 외피별도평면을 없애고 실제2톱니테두리에 회오리질감을 적용. D는 실제 화살 통과 뒤 황금 깃털을 남긴다. V3 기본채택, 진입광은 초반에만 나오고 기존 V3잔광으로 복귀한다.
- R/S 시안: R1 삼중성궁/R2 광편수렴/R3 교대검광, S1 반월파쇄/S2 압축파열/S3 월광삼단. 각 일반/변신 실제게임영상. Sparrow.ArsenalStudy.R/S 기본0이며 기존R/S 실제기본효과 유지. R310발/10파동/60피해, S15평행발/54피해 보존. 최초 R2 닫힌상자 인상을 분리광편으로 수정, R3는 R1과 구별되는 검광면으로 보완. D는 흰채움을 줄이고 금빛깃대/깃결을 보강한 refined60이 최종이다. 사용자 미적 승인은 별도.
- 이동 문제: recovery60에서 변신F발사후 원래발위치 경로가 실패했다. nav-diagnostic60으로 최초발사 직후 내비 시작점 투영73.54cm 이탈을 재현. SparrowArrow::InitArrow의 runtime MultishotTrail0가 SetStaticMesh를 먼저 호출해 내비영역을 잘라 남기는 것이 원인이었다. NoCollision/Overlapfalse/Navfalse 설정3줄을 SetStaticMesh 앞으로 이동한 새프로세스 A/B에서 투영오차0/경로정상/432.43cm이동, 마지막발사후66.67ms 이동복귀를 확인했다. 컨트롤러/강제nav재빌드는 변경하지 않았다. 이 재현 범위를 모든지도의 이동문제해결로 일반화하지 않는다. 근거 nav-order-ab-result.json; 엔진 StaticMeshComponent.cpp2429와 ActorComponent.cpp3277의 등록순서 조건.
- 검증: visual60 649체크/refined60 172체크, 최종recovery-fixed60/30 각76체크 통과. W/F 일반·변신 발사수/피해/이동복귀, W4발후취소→5번째없음/F발사전취소→0발 및 재시전/상태복귀/날개FX정리 확인. 마지막발사→이동60fps .0667초/30fps .100초. 초기pilot는 legacy검사경로, pilot-fixed는 피해 float정확동일 비교오류(35 vs35.0000076)로 중단했고 검사경로/허용오차.0001 수정. 실제F NoPath실패와 함께 실패로그보존.
- 빌드: 최종DebugGameEditor16.77초/DevelopmentEditor47.82초/DevelopmentGame53.06초 성공. Play-CurrentSkills.cmd --check 통과, 새 게임 실행 필요. 미디어는 내비순서수정 전 촬영이며 해당수정은 시각/발사/피해를 바꾸지 않는다. 패키징/장시간성능벤치/커밋/push/사용자프로세스종료 없음.
- 전달: Saved/QA/CharacterPipeline/sparrow-celestial-refine-20261026/preview.html. 적용Q/W/F/A/D/V 및R/S6쌍 총23클립(일반Q만 이전승인본 재사용). 새22MP4전체디코딩/44WebP전체프레임디코딩, 브라우저12선택/일반·변신/반속/정지프레임/전체시야/가로넘침없음 확인. result.json/media-manifest.json/browser-checks.json/browser-proof.png 보존.
- 정리: 이번4촬영폴더의 번호형 임시PNG3732장/7,051,365,930bytes만 경로/reparse사전검사후 삭제. 최종미디어/HTML/대표화면 해시불변, 삭제잔여0. before/이름있는캡처/실패로그/JSON/재질/소스 보존. 다음은 R/S선택과 실제미적피드백이다.


## 66. 10-27 Sparrow 성광·접힘·결정 재설계 및 R/S 교체

- 완료 기록: 2026-10-27T09:58:33+09:00. 사용자 요청에 따라 root는 Q/W 통합·빌드·촬영·검증, ascended_qwer는 R/S, mobility_repair는 F/A, saw_vortex는 D/V와 기존 V3 접힘을 담당했다. GPU 에디터는 직렬 실행했고 사용자 에디터는 종료하지 않았다.
- Q: 일반은 유지. 변신은 RuntimeHailEffect와 기존 낙하 화살·장판 파티클을 생성하지 않고, 24개 하강광/접촉광으로 전면 대체. 시전 시 form 상태·반경을 HailZone에 고정, 표시·실제 판정 반경 300→750cm(2.5배). 총40피해/8펄스/4초 유지. 참고 쇼츠 RjDh5nfXvTQ를 브라우저에서1.43/1.83/2.33초 확인해 하늘→바닥의 넓은 성광 느낌만 참고했다.
- W: 일반·변신 타격 시각크기 .75. 원형 시작점을 뒤로135cm 당기고 전진속도740→420으로 변경. 일반4발/변신4+1발/총35 유지. 기존 V3의6개 화염깃 면을 .42초 동안 실제 발사축 앞으로 접고 마지막 발사 후 .24초 복귀. 별도 장식 날개 액터 제거. FinishSkill은 CancelFormFold+약참조 해제만 하며 지속 중인 변신을 파괴하지 않는다.
- F: 파편다발을 3접힘면·5작은광맥·중앙결정·방출층으로 재설계. 응축은 활 앞130cm에서 읽히고 실제 화살은 .045초에 시각오프셋을 해제해 비행을 이어간다. 결정 내부 균열·명암·반투명 틈과 전용 타격재질 추가. 일반1/변신 삼각배치의 평행3발/대상당80/5200속도/1100사거리 보존. A는 비행 ArrowMesh와 기존 화살 Trail을 숨겨 실제 원형톱니만 남기고 변신 내부 번개광맥·균열을 보강했다.
- D: 활 앞 깃털바람 응축 Design4 기본채택. 기존 관통탄65피해/6500속도/1500사거리 유지. 경로 깃털은 기존 금빛결을 유지하고 .07초 뒤 부드러운 흔들림·낙하(약40~50cm) 후1.38초 소멸, 바닥높이로 clamp. V: V3 유지 + 지름200~220cm/높이1000cm 원형 하강광. .08초 하강/.15초 정점/.35초 기둥소멸/.43초 진입광종료. 불투명 파이프를 반려하고 캐릭터가 비치는 수직 광선으로 보완했다.
- R/S: 기존1~3 시안은 채택에서 폐기하고 기본 CVar4로 교체. R은 프로젝트 ShieldLightRays/FireNoise 질감으로 발사 전 불티응축→짧고 세 갈래로 찢긴 전진광막. 작은 고리/평평한 파면을 실제 촬영 후 두 번 보완. 310발/10파동/.13초/60피해 보존. S는 크기가 다른 큰 겹광륜→압축→.04초 간격 두 광면파열/평행 화살. 15발/54피해/450사거리 유지. 관련 원본 에셋 자체 수정 없음.
- 실제 검증: pilot60 260, refined60 378, final60 157, recovery60/30 각77 체크 통과. Q의 거리0/650/800cm 표적 피해 일반[40,0,0]/변신[40,40,0] 확인. applied60은 원거리 표적이 벽 위 Z711cm에 놓인 검사장치 문제로 실패했고 평지 표적으로 바꾼 뒤 통과; 실패로그 보존. W4발후취소→추가발사0/변신유지, F발사전취소→0발, 재시전과 실제마우스이동 복귀 통과. 마지막발사→이동60fps .0667초/30fps .100초. 기존 내비컴포넌트 등록순서 수정 보존. 이 검증을 모든 지도의 이동 문제 해결로 일반화하지 않는다.
- 빌드: 최종 DebugGameEditor6.39초/DevelopmentGame47.73초 성공. DevelopmentEditor는 사용자가 열어 둔 DLL을 보존하기 위해 이번에 재빌드하지 않았다. Play-CurrentSkills.cmd --check 통과. 새 실행→숫자2가 현재 적용본이다. 패키징/장시간성능벤치/커밋/push 없음.
- 전달: Saved/QA/CharacterPipeline/sparrow-impact-recraft-20261027/preview.html. Q/W/A/D/V는 refined60, F/R는 final60, 이후 변경 없는 S는 pilot60. 15MP4 전체디코딩/30WebP 전체프레임디코딩, 8스킬 전환·일반/변신·반속·전개/방출·확대/전체시야·가로넘침없음 브라우저 확인. browser-proof.png/result.json/media-manifest.json/clip-selection.json 보존. 최종 화면을 실제로 검토했으며 사용자 미적 만족도는 아직 별도다.
- 정리: 이번4촬영 폴더의 번호형 PNG3984장/7,539,928,097bytes를 경로·reparse사전검사 후 삭제. 최종 미디어/HTML/대표 캡처 해시 불변과 삭제잔여0 확인. 소스·재질·before·로그·검사JSON·이름있는캡처 보존.

## 67. 10-27 Sparrow 실제 세라프 날개 동작 · 성광 질감 보완 · S 네 시안

- 완료 기록: 2026-10-27T11:25:41+09:00. Q는 사용자가 원하는 방향을 ‘천천히 눌러 꽂히는 빛줄기와 묵직한 접촉’으로 확정했다. root는 Q/V 통합·빌드·촬영·정리, saw_vortex는 원본 날개 애니메이션과 독립 화면 검토, mobility_repair는 F/A 표면, ascended_qwer는 S5–S8 네 스타일을 담당했다. GPU 빌드·촬영은 직렬이며 사용자 에디터 종료 없음.
- W/V 핵심 변경: SparrowAscension의 실제 Serath 날개 메시·동일 스켈레톤에서 Wings_Unfold, E_Ability_Wing_Flap_Holy, Wings_Fold, Idle_Pose_Wings를 직접 재생한다. §66의 화염깃 평면 접힘 대신 W 마지막 당김/발사에 실제 원본 날개 관절이 움직인다. 원본 애니메이션 notify/root motion은 발생시키지 않고 spine03 기준을 맞춰 본체 이동과 분리한다. W .42초 당김→원본 .267–1.0초 구간 발사 동작→Idle. V 진입은 Unfold 1.4배, 종료는 Fold .55초. V 상태·몸체 외형은 만료 즉시 복구하고 남은 날개 시각만 접힌 뒤 소멸한다. 재시전·이동 잠금 연장 없음. 날개 표면의 기존 불꽃 질감과 프로젝트 Sparrow Burst/UltHit 보조 파티클을 사용하며, 세라프 원본의 모든 notify VFX까지 복제한 것은 아니다.
- Q변신: .36초에 걸쳐 천천히 하강하는 가는 밝은 중심과 5갈래 보조광, 실제 ShieldLightRays 질감과 접촉 불꽃을 추가했다. 최초 균일한 꽃잎 접촉광을 반려하고 짧은 비정형 금빛 파열·잔광으로 보완했다. 72평면(24×빛줄기/접점/수직 불꽃), 반경750cm/40피해/8펄스/4초는 §66 유지. 일반Q는 변경하지 않았다.
- F/A: F의 좁은 실탄 중심 폭을 유지한 채 더 넓고 불규칙하게 침식되는 후류·파편과 3접힘 결정면을 보강했다. 변신 삼각3발/피해80/속도5200/거리1100 유지. A변신은 3개의 넓은 곡면 회오리와 내부 역회전으로 바꾸고 중앙 파티클을 줄여 흐름이 보이게 했다. 화살 축은 숨김 유지, 일반A/톱니속도 유지. 최종 실제 화면 재촬영 후 두 담당자가 비교했다.
- D/R/V: D깃털 수명1.38→.78초, 낙하·응축을 빠르게 하면서 바닥 clamp 유지. 활 앞 깃털에 흐르는 광맥/깃살 질감을 보완했다. R추가 광막은 기본 CVar0으로 제거, 실제 기존 화살 시각 scale .5→1(길이·굵기·전체 ×2), 작은 타격 scale .5와310발/10파동/.13초/60피해 유지. V3는 유지하고 진입 하강광을2.15초로 늘렸다. 가는 수직선만 남던 중간본을 넓은 반투명 광막으로 수정, 몸/날개가 드러나며 소멸한다. 상태시간이나 조작 잠금은 늘리지 않았다.
- S5–S8: 폭풍흡입/결정파쇄/깃털전개/빛의부채 파열의 실제 게임 시안. S6 종이판·S7 흰 스티커 인상을 실제 촬영에서 반려한 뒤 침식/빈틈/깃살/불티를 수정했다. 현재 기본S는 기존4, 새 후보는 미선택. 15평행발/54피해/450cm 경로는 그대로다. 최종 검토에서 S6 전개 존재감은 상대적으로 약하고, S7은 일부 금빛 잎맥 인상, .43초 착탄에서는 공통 섬광이 우세해 후보 차이가 줄어든다. 기능 통과를 미적 완성도 보증으로 표현하지 않는다.
- 검사: pilot60 271/applied60 429/recovery30 80/refined60 217/s-final60 287체크 각각 통과. 각 단계는 일부 이전 시각본을 포함하므로 전체를 하나의 최종 회귀검사 수로 합산하지 않는다. 실제 W/F 취소·재시전·마우스 이동/날개 복귀, Q자기발밑, 최종F/A/Q/V와최종S8쌍 확인. NativeV는 키 입력부터40.550002초 자연만료·Fold동안108.888897cm 이동·상태0/몸체복구·재시전 확인. 검사 당시 새V시작과 구날개 생존은 겹치지 않아 동시구/신날개 중첩 검증을 주장하지 않는다. 최종 새프로세스 S촬영의 재질/Python컴파일 오류 없음. 재질 저작 중 연결을 재구성하며 발생한 임시 Missing ComponentMask 경고와 이후 성공 기록, s-pilot의 도구 import 실패/수정 재실행 기록은 보존했다.
- 빌드: 최종 DebugGameEditor6.91초, DevelopmentGame104.07초 성공. DevelopmentEditor는 사용자 열린 DLL을 보존. Play-CurrentSkills.cmd --check 통과, 새게임→숫자2. 이전 자동승인 검토의 사용량한계로 빌드가 중단됐으나 사용자 재개 후 같은 승인경로 재시도 성공(우회 없음). 패키징/성능벤치/커밋/push 없음.
- 전달: Saved/QA/CharacterPipeline/sparrow-seraph-polish-20261027/preview.html#W. 일반/변신 및V진입/자연종료 총22클립. W는pilot60, D/R/A일반/V종료는applied60, 최종Q/F/A변신/V진입은refined60, S5일반은변경없는pilot60/S나머지는s-final60. 일반Q만이전승인본재사용. 모든MP4/정상·반속WebP디코딩, 브라우저11선택의22이미지로딩·반속·전개·방출·전체시야·가로넘침없음·콘솔오류0 확인. 원래localhost서버가꺼져127.0.0.1:55811로재시작(PID42476). W실제비교탭 deliverable표시. result.json/clip-selection.json/media-manifest.json/browser-checks.json/browser-proof.png 보존.
- 정리: 이번 pilot60/applied60/refined60/s-final60의 번호형촬영PNG4603장 8,730,602,486bytes를 경로·reparse 사전검사 후 삭제했다. 최종영상·WebP·포스터·HTML·화면증거 해시 불변, 삭제대상잔여0. before/이름있는대표캡처/로그/검사JSON/재질/소스 보존. 다음은 실제화면 피드백과S후보선택이다.
## 68. 10-27 Sparrow 느린 변신 Q · W 마지막 타격 · F 재구성 · V 두 단계 강림

- 완료 기록: 2026-10-27T12:32:32+09:00. 최신 요청 범위 Q변신/W/F/A변신/D/V진입/S후보를 처리했다. root는 W/실제 명중연결/V날개 지연/빌드/촬영/전달, saw_vortex는 Q/D/V 표면, mobility_repair는 F/A, ascended_qwer는 S9/10을 담당했다. 독립 소스별 병행 후 GPU 빌드·촬영은 직렬, 사용자 에디터 종료 없음.
- Q변신: 광체 하강 .36→.92초, 큰 지면 압착광과 짧은 질감 파열. 사각 막대 끝을 완화하고 옆으로 흐르는 광맥 추가. 일반Q/반경750/40피해/8펄스/4초 유지. 빛줄기 시각 시간과 기존 피해 펄스는 독립이다.
- W: 실제 날개 공격 호출과 추가 접힘 FX를 제거했다. 원본 Idle 날개와 V상태는 유지, 기존4발+.42초당김후추가1발을 보존한다. 마지막 발의 실제 명중에만 새 SharpImpact12를 사용한다. 초기 별모양 판을 반려하고 흐르는 3개 플라스마 파열층/짧은 불티/두 펄스로 수정. 중복 일반변신contact는 final태그에서 제외. W 취소/재시전/입력 시점은 변경하지 않았다.
- F/A: F 준비를 넓은 3개 광류→급압축→긴 방출축으로 재구성했다. 변신은 마지막에 삼각3축으로 분리. 종이판처럼 보이던 pilot과 너무 가늘어진 refined를 반려 후 광면 밀도/내부 광맥/침식을 조정. f-final60은 normal author만 적용된 통합 누락을 발견해 변신 author 재저작 및 f-form60만 재촬영했고 최종미디어를 교체했다. 1/3발·80피해·5200속도·1100거리·시전시간 유지. A변신은9개 비대칭 날카로운 회전날, 일반A와 느린 속도 유지.
- D/V: D깃털 길이·폭2/3, 활쪽 광깃 몸체와 정렬·응축 강화. V는 FX기준0~.28초가는빛/.28~.40끊김/.40~.50빠른큰기둥/1.0초황금섬광+원본날개펼침. 키입력기준FX는약.55초뒤시작한다. 중앙밀도를유지하고하단경계를완화. 몸체금색상태는기존대로진입즉시, 날개/입자만지연. V지속/이동잠금/종료.55초Fold변경없음. 이번종료영상은직전검증본재사용이며새종료검증으로표현하지않는다.
- S: 기본4유지, 선택용S9(S5계열압축광풍)/S10(S8계열상하광면+시차파열) 추가. cast snapshot태그가 실제15평행화살과명중13/14까지전달, 공통큰contact는후보에서만축소.15발/54피해/450거리유지. 밝은면의합침과 .52초잔류가림개선. S9깃털/붓결인상·S10빛부채인상·변신날개중첩으로차이약화는남아있다. 기능통과가사용자미적만족의보증은아니다.
- 검사: pilot60 446/refined60 401/f-final60 70/f-form60 56/recovery60 80 각각통과, 합산한최종회귀수로표현하지않음. W4발후취소→추가0/V유지/재시전5, F발사전취소→0/재시전3. W/F일반·변신마지막발사→실제마우스이동 .0667초. Q/D피해유지, V원본Unfold→Idle/부착오차미미. 최종촬영구간재질컴파일/Python오류0. 저작중그래프연결전Missing입력경고는보존. 별도S/F/QDV시각검토JSON과native명중분기읽기전용검토보존.
- 빌드: DebugGameEditor40.27초/DevelopmentGame54.09초성공. 이후재질만변경. DevelopmentEditor재빌드없음. Play-CurrentSkills.cmd --check통과, 새게임→숫자2. 패키징/성능벤치/커밋/push없음.
- 전달: Saved/QA/CharacterPipeline/sparrow-impact-revision-20261027/preview.html#Q.16클립전체MP4및정상/반속WebP디코딩, 브라우저8스킬16이미지·반속/전개/방출/전체시야/실제프레임진행/콘솔오류0확인. Q일반/V종료는이전변경없는영상, A와W일반은pilot, Q/W변신/D/V진입/S9/10은refined, F일반f-final/변신f-form. result.json/selection/manifest/browser증거보존. 화면을열어deliverable표시했다.
- 정리: 이번pilot60/refined60/f-final60/f-form60번호형임시PNG4017장7,607,936,653bytes만경로·reparse사전검사후삭제. 최종영상/HTML/대표화면해시불변·삭제대상잔여0. before/이름있는캡처/로그/검사JSON/재질/소스보존. 다음은실제미적피드백과S후보선택이다.

## 69. 10-27 Sparrow 전체 반려 후 실제 전후 비교 재작업

- 완료 기록: 2026-10-27T13:36:20+09:00. 최신 Q변신/W최종타격/F/A변신/D/V진입/S후보 재작업. 이전 기능 통과를 미적 수용 근거로 쓰지 않았다. root Q타격연결/W/D/V/통합, mobility_repair F/A, ascended_qwer S, saw_vortex Q표면/독립검토. 사용자 에디터 종료 없이 GPU 직렬.
- 진단: 반복된 평면 도형, 밝은 중심의 겹침, 전개·응축·타격 대비 부족. F/A Plasma sRGB 선형 샘플에 높은 밀도 임계값을 적용해 질감이 사라지는 원인을 원본 채널 export로 확인했다. 원본 텍스처는 보존하고 전용 shader 밀도 범위를 복원했다.
- Q변신: 24반복막대 대신8광체/4층32평면, 접근→마지막140cm압입→지면파열. 수평십자 광두/마름모 색종이 중간본 반려. 원본 Main Flames/Wisps 착탄은 SpawnActorDeferred→Initialize→FinishSpawning 사용. 일반Spawn 뒤 Initialize하면 기존 BeginPlay가 빈템플릿을 파괴하는 중간본 문제를 고쳤다. StartHail 변신만 첫 .82초/간격 .37초로8피해를 접촉에 연결. 40피해/750반경/4초/일반Q 유지. 첫 피해가 늦어지는 실제 플레이 변화다.
- W/D/V: W4+1 마지막 실제명중만 원본 입체불꽃/불티/짧은압력파, 날개공격 없음. D활8잎판을 발사축으로 감겨모이는 광류로 교체, 경로깃털2/3크기/.78초낙하 보존. V전조0~.28→공백.28~.40→대형기둥.40~.50→1.0섬광/원본Unfold 유지, 내부수직흐름/낙하실선/실제착탄 추가. 상태40초/이동잠금/종료Fold 유지.
- F/A: F는 원본 SM_ShockwaveFlame 곡면과 SM_Sparrow_Arrow 핵. 점화→응축→방출, 일반1/변신삼각3평행발/80피해/5200속도/1100거리 유지. 단단한껍질과질감소실 중간본 반려 후 밀도복원. A변신9절삭날/내부역회전/중앙광핵축소, 일반A/느린속도 유지. F둥근타원껍질과 A중앙흰빛은 남는다.
- S: S9/10 준비면과방출면 분리, sand같은끊김을연속밀도로복원. 전개→응축→상하파열이 더분명한 S10을 실제S기본(CVar10)으로 적용, S9대안. 15평행발/54피해/450거리/태그13·14 유지. QA복원값도10. 중심발광겹침·변신날개중첩은남으며 미적완성보증없음.
- 최종근거: qwdv-pilot60 164중W영상만유효, refined60 340(Q/D/V/S), fa-final60 92(F/A), recovery30 171(W/F취소·재시전·실제이동/Q첫접촉전피해0·전환시예약취소/Q일반변신/새S기본10) 각각통과. 합산한전체회귀수로표현하지않음. Q8피해/8live착탄,60fps최대1프레임차이,30fps동일순서. 저작후실행구간Python/재질컴파일오류0. 저작중그래프재연결경고보존.
- 빌드: DebugGameEditor5.91초/DevelopmentGame36.88초성공, Play-CurrentSkills.cmd --check통과. DevelopmentEditor/사용자프로세스보존. 새게임→숫자2. 패키징/성능벤치/커밋/push없음.
- 전달: sparrow-reart-20261027/preview.html, 직전impact-revision과16클립전후비교. Q/W/A일반/V종료는변경없는영상재사용. MP4/정속·반속WebP디코딩,16쌍브라우저표시/확대/프레임/재생/가로넘침0/오류0. Q두화면표본의실제프레임진행확인. S10방출비교browser-proof.png, result/selection/manifest/진단/3독립리뷰보존.
- 정리: 번호형PNG4668개/8837348648bytes만 경로·reparse사전검사후삭제. 최종미디어·HTML·대표화면해시불변/삭제잔여0. 소스/재질/이름있는대표캡처/로그/JSON/채널audit보존. 다음은사용자의실제전후평가이며자동으로미적수용완료라하지않는다.

## 70. 10-27 Sparrow 설계 방식 전환 · 18개 원화와 선택적 게임 수정

- 완료 기록: 2026-10-27T14:41:30+09:00. 사용자 최신 요청은 변신Q 이전 표현/여러 시안, W 앞날개 장식 삭제, E/F 제로베이스 시안, A 이전 복원+작은 태양 화살, D 활쪽 시안, V 이전 복원+높이별 분절 전조/반투명 큰 기둥이다. root는 이미지 생성/통합/빌드/촬영/전달, ascended_qwer는 Q/W와 F 시험, mobility_repair는 A, saw_vortex는 V/갤러리를 담당했다. GPU 저작·촬영은 직렬, 사용자 에디터 보존.
- 새 설계 자료: imagegen으로 Q3/E3/A2/F4/D3/V3 총18개, 각 준비→발사→타격 3단계 원화. 게임 카메라/캐릭터 캡처를 장면 기준으로 사용했다. 2D 그림을 실제 게임으로 표현하지 않는다. E3의 초기 평행3발은 F와 유사해 곡사수렴으로 교체, D1의 떨어진 깃 장식도 활 표면결로 수정했다. F4는 조각을 운반하는 열린 회오리→가는 화살 조립. 원화와 프롬프트/source 경로는 concepts/와 concept-prompts.json에 보존한다.
- 실제 기본 적용 Q/W: Q는 impact-revision의24×3 빛줄기/접촉광/불꽃 표현으로 복원했다. 최신 .82초부터 .37초간격8회 피해(40/750반경/4초)는 유지하고, 각 피해에3줄기씩 접촉을 맞췄다. 원본과 시간까지 동일한 롤백은 아니다. W 앞에 별도로 생성하던6 BowFlow 평면을 제외,2 BowPulse/4+1발/마지막 명중/본체 날개 유지. native 날개 공격을 다시 추가하지 않았다.
- A 기본은 impact-revision의 톱니/내핵으로 복원. SunArrow.Style1의60/66cm 태양·화살축·홍염/후류 시험과 재질 재수정까지 했지만 실제 화면은 검은 공+주황 철사 인상이 강해 추천 제외. 기본값0. FDesign.Style1(결정)/2(입체 열린 나선)도 새 RGBA 광류 원화를 실제 import하여 재질 재수정했으나 잎판·매끈한 철사처럼 읽혀 둘 다 추천 제외. 기본0이며 기존 F 유지. 해당 CVar는 시전 시 snapshot→실탄 태그 전달, 실제 피해/벽/취소 경로 유지. 저품질 게임 후보를 2D 원화와 동급으로 전달하지 않는다.
- V 기본: impact-revision 블록 복원 후 전조0~.5초, 큰 기둥 .54~.66초 하강/접촉,1.16초 황금 섬광+원본 Unfold. 전조는 world-height15구간의 서로 다른 소멸시점(.25~.49)으로 위/중간/아래가 나뉘어 사라진다. 초기 크림색 통을 반려해 기둥 emissive 약1/3/alpha .12~.24로 낮췄고 실제 화면에서 바닥줄눈과 캐릭터가 비친다. 반듯한 선분/원통 경계는 남는다. 상태40초/입력/종료Fold 유지. 사용자 미적 수용과 별개다.
- 검증: DebugGameEditor21.17초/DevelopmentGame31.89초 성공, Play-CurrentSkills.cmd --check 통과. DevelopmentEditor는 열린 사용자 DLL 보호로 재빌드하지 않았다. pilot60 253체크(Q/W/V/A/F), refined60 106체크(최종 V/A/F 재질) 각각 통과. 서로 다른 실행의 수치를 하나의 최종 회귀검사로 합산하지 않는다. startup LogAutomationTest Condition failed 기존 로그는 보존되어 전체로그 오류0을 주장하지 않는다. A/F 기본0 복원 확인. 실제 최종 A/F 독립검토는 반려, V는 요청 구조 개선 확인과 잔여 한계 기록.
- 전달: Saved/QA/CharacterPipeline/sparrow-design-reset-20261027/preview.html#F4. 18개 원화/2개 비교/확대, 별도 실제게임 탭에는 Q복원/W장식제거/V진입3클립만 표시한다. A/F 시험5클립은 prototype-evidence/에 비교기록으로만 보존. 총8MP4 전체디코딩, 브라우저18이미지 로딩/가로넘침0/비교/확대/3영상 실제 완주/콘솔오류0. result.json/media-manifest.json/browser-checks.json/browser-proof.png/3독립리뷰/저작프롬프트 보존.
- 정리: pilot60/refined60 번호형PNG2331개4,410,141,810bytes만 경로·reparse사전검사 뒤 삭제. 최종 미디어/대표캡처/HTML 등157파일 해시 불변/삭제잔여0. 소스/재질/원화/before/로그 보존. 다음은 새2D 설계의 사용자 평가이며 A/F 원화 수준의 게임 구현은 아직 달성하지 못했다. E/D 새 방향은 원화만 있고 기본 스킬에는 미적용이다.

## 71. 10-27 Sparrow 원화 18안의 실제 게임 구현·촬영 비교

- 사용자 요청: 2D만으로 판단하기 어려우니 실제 게임 시안으로 제시하고 원화와 큰 품질 차이를 줄일 것. Q3/E3/A2/F4/D3/V3 총18개를 선택 가능한 native/material 후보로 구현했다. 기본 스킬 채택은 별개이며 6개 selector 기본값은 모두0이다. root F/실탄/통합/촬영/브라우저, mobility_repair A/E, ascended_qwer Q/V, saw_vortex D/갤러리 담당. 사용자 에디터 종료 없이 프로젝트 소유 실행만 사용했다.
- 선택: `Sparrow.DesignIngame.Q` 1~3, `.V` 1~3, `Sparrow.SunArrow.Style` 1~2, `Sparrow.EDesign.Style` 1~3, `Sparrow.FDesign.Style` 1~4, `Sparrow.BowMuzzle.Style` 1~3. 각 시전에서 값을 고정한다. Q는 변신 상태 후보, V는 변신 진입, E/A/F/D 영상은 일반 상태다. W 및 기본값0의 표현은 이번 후보와 분리했다.
- F/A/D: F는 실제 결정/열린 나선/깃결/결정+나선 메시, 응축→실제 투사체→실제 명중 분열. 재질 광류 RGBA와 면 명암을 재조정했다. F1/F4 마지막 결정은3링 다면체로 단순화했다. A1/2 실제85/90cm 태양 표면 대류와 열린 홍염/붙어도는 화염날. D1/2/3은 실제 활 본에 붙는 불꽃 깃/광류/빛시위이며 관통 실탄과 경로 깃털 유지. F 일반1/변신3평행발, 기존피해/속도/범위 유지.
- E: E1 큰 깃활 단발. E2 실제520cm/전방90도/높이180cm 근접1회 피해와 세계가림 검사, 원거리 실탄0; 캐릭터 모션은 기존 사격이므로 새 활 휘두르기 애니메이션은 아니다. E3 실제5곡사, 각 정의피해1/5, .30초 수렴. 64구간으로 실제 곡선길이 예산을 잡아 외곽 화살의 최대사거리 조기소멸을 수정하고 최종점에서 정리한다. 실제 샘플 궤적의 검은 이음매/3선 레일을 단일 부드러운 core로 보정했다. 피해·벽·취소는 시각 대역이 아닌 실제 실탄 경로다.
- Q/V: Q1 가는 창/Q2 유동광/Q3 결정면,16지점이8실제피해와 연결된다. 긴 바닥 가지는 작은 단절균열/접촉불티로 줄였다. V1기둥/V2다층장막/V3외곽흐름. 공통 전조0~.5→.66접촉→1.16섬광/원본날개. 떨어져 남는 추가 WingFlow4개 제거. 피해/변신상태40초/입력수명은 유지했다.
- 확인된 렌더 문제: 재import와 촬영을 같은 UE실행에서 한 refined60에 일부 회색 메시가 관측됐다. 이후 editor 섹션 슬롯20개가 모두0이어서 슬롯가설은 기각했고, 저장된 에셋을 새 실행에서 읽은 final60에서는 정상이다. 정확한 내부 원인은 단정하지 않는다. 별개로 M_EStrand의 실제 `missing usage flag InstancedStaticMeshes` 로그를 확인해 명시 저장·조회하고 재촬영했다. 최종 E3 실행에 usage/Python/material 실패 로그 없음. startup 기존 Condition failed와 저작 도중 임시 graph 경고는 보존한다.
- 기능검사: pilot60 356통과, refined60 371중 최대사거리 fixture가 방 벽에 막혀 전체false(나머지 후보별 검사통과). 고도 임시바닥에서 실제 Walking/충돌 유지한 final60 323통과, author-boundary30 19통과, polished60 85통과, e3-continuous60 17통과. E3 경계검사는30/60 각각14/14, 끝점오차0.000cm/중앙1800·외곽1955cm, 실제벽5발차단·뒤피해0/발사전취소0발/동일pawn재시전5발·총60피해. 서로 다른 실행 합산을 전체회귀수로 표현하지 않는다.
- 빌드: 마지막 DebugGameEditor16.41초, DevelopmentGame58.41초 성공, Play-CurrentSkills.cmd --check 통과. DevelopmentEditor 재빌드/패키징/성능벤치/커밋/push 없음.
- 전달: `Saved/QA/CharacterPipeline/sparrow-design-ingame-20261027/preview.html#F4`. 18개 실제 MP4, 같은 촬영의 정속/반속 WebP36개, 원화비교·1.6배/전체시야·대표장면. IAB에서 MP4 metadata는정상이나 화면검음이 관측돼 WebP를기본표시하고 원본MP4링크보존. 전파일/전프레임디코딩, 브라우저18움직임이미지로딩·표시·0.5배·비교·확대 확인. 최종출처는 clip-selection.json/game-manifest.json. D는 refined60, Q/V/A/F2/F3는 final60, F1/F4/E1/E2는 polished60, E3는 e3-continuous60.
- 미적판정: 실제 비교 후보 전달 가능. 원화 동등 또는 작은 품질차 달성을 선언하지 않는다. Q2/Q1·V2/V1이 상대적으로 잘 읽힘. Q3 결정 입체감, V3 빈 중심 차별성, A홍염의 리본감, E1장식감/E2기존자세, F/D잔광과표면세부 부족을 후보별 JSON과페이지에 명시했다. 사용자 수용 미확정. 원화 그림을 게임 장면으로 대체하지 않았다.
- 정리: 검증된 최종/이전 MP4와 명명된 스틸을 보존한 뒤 pilot2994장5,697,094,002bytes 및 후속6348장12,030,362,362bytes 번호형임시PNG만 경로·reparse사전검사/삭제후잔여0검증. 합계9342장17,727,456,364bytes. 소스/원화/기존후보/로그/보고서 보존. 다음은 실제게임 후보에 대한 사용자 선택·피드백이며 기본0을 임의채택하지 않는다.

## 72. 10-27 Sparrow 제네시스 Q · 새 E 질감 · F4 채택과 세분화 비교

- 완료 기록: 2026-10-27T19:35:25+09:00. 사용자 요청은 변신Q의 제네시스 인상, 완전히 다른 화려한 E1 활과 E3 유도탄의 여러 질감, 중앙 화살을 원형 FX가 감싸는 A, F4 채택/작은 다수 조각 비교, D2+D3 결합, 끊기지 않는 얇은 선 다음 큰 거친 기둥의 V다. root F/통합/실제촬영/전달, mobility_repair E/A, ascended_qwer Q/V, saw_vortex D/갤러리를 파일별로 분담했다. 중단 후 사용자 재개 때 저장된 마지막 재질 보정을 실제 에셋에 반영·재촬영했다. 사용자 에디터 강제 종료 없음.
- Q4/Q5: 제네시스 쇼츠 RjDh5nfXvTQ의 2.40/2.654/3.005초를 브라우저에서 직접 봤다. 공중의 넓은 광륜에서 연속된 빛이 지면으로 내려오는 부분을 반영. Q4 16줄기/2개씩, Q5 8개 넓은 줄기/1개씩. .82초부터 .37초 간격의 8회 피해40/반경750은 유지한다. 실제 화면에서 평면 끝 쐐기→노란 통→넓은 흰 통을 차례로 반려하고, 열린 원통 메시/작은 지면 광류/가는 흰 중심/외곽 금빛 흐름으로 수정했다. 광륜과 접촉은 읽히지만 밝은 축은 여전히 매끄럽고 포화돼 보일 수 있다. 원본 동등 품질을 선언하지 않는다.
- V4: 연속된 가는 6.5cm 선이 먼저 내리꽂히고, FX age .20초에 큰320cm기둥 시작/.34초 접촉. 가는 선은 .29~.36초 자연 소멸하며 분절 마스크 없음. 기존1.16초 몸체섬광/원본날개 전개/40초 상태 유지. 키입력과 FX시작 사이 기존 지연이 있어 영상 .65초가 가는선,1.05초가 큰기둥이다. 흰 축의 폭을 줄여 세로 금빛 결이 읽히게 했지만 최고광량 순간에는 몸체가 가려진다.
- E1: 새 비대칭 반곡궁의 틀/빛막/장식·보석/끝 곡광, 단발 실제 화살. 얇은 곡선만 남던 문제는 막·장식 구분 UV의 2~3/4~5 범위가 UE5.8 FbxStaticMeshImport.cpp의 V=1-V에 의해 음수로 뒤집혀 opacity0 분기로 들어가던 실제 오류였다. E1 전용 OBJ UV만 사전 역변환했으며 공용 importer/다른 E는 보존. author-uv-contrast의 실제 mesh UV 조회에서 모두 통과, E1 마지막 촬영에 빛막과 끝장식 표시 확인. 미세 조각 디테일은 게임 배율에서 제한적이다.
- E3/E4/E5: 동일한5실제 곡사 유도 화살에 순광/플라스마/뇌광 질감. 누적 실제 경로 거리로 UV를 이어 이음매를 막고, E5 화살촉/코어/분기밀도 보강. 실제 총피해/곡선종점/벽/취소 경로 유지. A3는 태양 구체를 없애고 원래 중앙화살+160/108cm 열린 원형 흐름으로 복원한 비교 후보다.
- F4는 사용자 선택대로 `Sparrow.FDesign.Style` 기본4로 채택. F5 비교는 결정16→40, 각각 길이/폭/두께58%, 등장 타이밍 정규화. 회오리2줄/시전/피해80/속도5200/사거리1100/일반1발·변신삼각3발 유지. 기존 F4 일반·변신을 직접 촬영했고 F5는 일반 비교. D4는 D2의2광류와 D3의8빛시위를 단계적으로 결합, 기존 관통 실탄과 낙하 깃털 유지. Q/V/A/E/D 새 selector 기본0, F만4. 영상에 있는 후보를 전부 기본 스킬로 채택한 것은 아니다.
- 검증: DebugGameEditor49.00초/DevelopmentGame42.21초 성공, Play-CurrentSkills.cmd --check 통과. 마지막 표면 보정 후11개 native 파일 해시가 두 빌드 당시와 동일하다. fd60 68/pilot60 172/refined60 120/final60 103/polished60 103체크 각각 통과하며 서로 다른 단계 검사이므로 합산을 최종 회귀검사 수로 표현하지 않는다. 최종 E1 UV3메시 실제조회 통과, polished Python/material/missing-usage 실패 없음. 기존 startup Condition failed 로그는 보존. 패키징/성능벤치/커밋/push 없음.
- 전달: `Saved/QA/CharacterPipeline/sparrow-celestial-rebuild-20261027/preview.html#Q4` 총11실제게임후보. F4/F5/D4=fd60, E3/E4/A3=pilot60, E5=refined60, Q4/Q5/E1/V4=polished60. 원본MP411개·정속/반속WebP22개 전체디코딩 및 해시확인. 브라우저11후보 로딩/정속·반속/재시작/확대·전체시야/동일시점비교/대표장면/가로넘침0/콘솔오류0. F4↔F5 같은 목표.32초와 실제.317초 비교 가능. UI확인 f-comparison-proof.png, q-motion-browser.png 및 result/selection/manifest/browser-checks/final-visual-review 보존. 꺼진 로컬서버는127.0.0.1:55811 PID7664로 재시작했고 최종탭2 deliverable표시. open_in_codex는queued반환이어서 사용자 전면표시 성공을 단정하지 않는다.
- 정리: 해당 작업의 번호형 임시PNG4548장8,575,103,470bytes를 영상 보존·해시·경로/reparse 사전검사 후 삭제하고 잔여0 확인. 최종/중간 MP4, WebP, 이름있는 스틸, 소스·에셋·참고화면·로그 보존. 소유UE/ffmpeg는 최종조회에서 없음. 다음은 실제후보에 대한 사용자 평가이며 심미적 수용은 아직 미확정이다.

## 73. 10-27 Sparrow D/F/V 보강 · 나머지 표현 재구성과 기본 채택

- 완료 기록: 2026-10-27T21:43:43+09:00. 사용자 요청에 따라 D/F/V 방향을 유지해 보강하고 Q/W/E/R/A/S 표현을 재구성했다. root D/F·통합·빌드·촬영·전달, ea_rebuild E/A, qv_rebuild Q/V, wrs_rebuild W/R/S를 분담했다. GPU 저작·촬영은 직렬 실행했으며 사용자 프로세스 강제 종료 없이 소유 실행만 종료했다. 같은 도형의 밝기만 높이는 시안을 여러 차례 자체 반려하고 실제 게임 화면에서 재료·형태·타이밍을 수정했다.

- 기본 채택: Sparrow.DesignIngame.Q=6, .V=5, Sparrow.SunArrow.Style=4, Sparrow.EDesign.Style=6, Sparrow.FDesign.Style=6, Sparrow.BowMuzzle.Style=5, Sparrow.Renaissance.W=1, Sparrow.ArsenalStudy.R=5, .S=11. 옛 selector 구현은 비교용으로 보존했다. normal DevelopmentEditor와 전용 DebugGameEditor 실행 모두 새 빌드이며 이번 결과는 시안 페이지에만 존재하는 것이 아니다.

- D5/F6/V5: D는 실제 활 표면의 결/빛시위와 발사 방향으로 휘는 6광류, 기존 관통·낙하 깃털 유지. F는 F4 기반 24개 작은 8면 결정과 굵은 2나선/얇은 2흐름, 실제 일반1발·변신3평행발/80피해 유지. V는 가는 연속 선→큰 기둥→황금 막→원본 날개 전개를 유지하고 흰 중심의 소멸/커튼의 흐름/접점 크기를 조정했다. 상태40초·기존 이동 잠금·종료 Fold는 유지하며 W 날개 공격을 되살리지 않았다.

- E6/A4: E는 날개처럼 읽히던 중간본을 반려해 연결된 반곡궁/시위/좁은 빛막/짧은 끝 흐름으로 다시 만들고 실제 단발60피해를 연결했다. A는 3갈래 7톱니 절삭날/변신 내부 역회전과 중앙 황금 플라스마. 원본 Plasma의 Cylinder radial velocity가 입자를 핵 밖으로 밀고, alpha-.5*RelativeTime이 낮은 alpha 입자를 조기 소거하는 것을 실제 런타임/재질 조회로 확인했다. 원본 에셋은 보존하고 런타임 복제 속도·전용 Wisps 재질/72cm 플라스마 볼륨으로 보완했다. 실제 핵 입자 수13/12·평균반경6.16/7.13cm, 마지막 adopted60 화면에서 중앙 체적을 확인했다. 기존90피해/160속도 유지.

- Q6: 일반 평행4광체×8펄스, 변신 상부 광륜·긴 광막·마지막140cm 압입. 납작한 노란 바닥/철사 같은 선을 반복 반려하고 최종 접점은 원본 8×8 플라스마 알파를 쓰는 SM_RenSPlume 곡면3개로 교체해 .14초 부풀고 .46초 소멸한다. 바닥 안개 없이 접촉 체적을 보강했다. 일반 즉시 시작/변신 .82+i*.37초의 기존 피해40·변신750반경 유지. 최종 접점은 임시 ParticleSystem 복제가 아니라 기존 actor가 소유하는 곡면 배열이다.

- W1/R5/S11: W는 4압력면의 .59초 준비→활 앞으로 수렴→기존4/변신5발, 기존 보라 준비 FX를 새 경로에서 제외했다. R은 정지한 방사형 레일을 짧은 광류/움직이는 광편으로 줄이고 실제 화살 재질·첨두·길이 분산을 재구성했다. 310발/10파동/.13간격/60피해와 다발 사격 구도는 유지하므로 완전히 새 동작이라고 표현하지 않는다. S는 반복 원을 실제 비틀린 플라스마 곡면/응축→전방 파열로 변경, 발사 원점을100cm 전진하고 실제15평행발/450거리/54피해 유지. 약한 S12는 전달 후보에서 제외했다.

- 검증: 최종 DebugGameEditor21.81초/DevelopmentGame45.39초/DevelopmentEditor62.94초 모두 성공. Play-CurrentSkills.cmd --check 통과. 최종 DevelopmentEditor adopted60 295체크 통과, 기본9selector를 미리 덮어쓰지 않고 조회했고 실제 마우스 클릭 후 QWERASDF 일반8·변신8 이동16건 통과. 마지막 발사→이동 .0667초(E/R .0833초). 기존 피해·발사수·상태 복귀 확인. 다른 단계 검사 수를 최종295에 합산하지 않는다. 모든 지도/방향/장시간 스트레스 해결로 일반화하지 않는다.

- 촬영 한계: 긴 third60 S 촬영에서 VRAM180MB 초과 표시가 관측돼 숨기지 않고 해당 중간본을 보존했다. 소유 비교 탭을 닫고 S만 새 실행에서 재촬영한 s-final60 일반·변신 영상에는 해당 경고가 없고 검사 통과. 성능 벤치나 메모리 문제의 근본 해결을 주장하지 않는다. 기존 startup Condition failed/retarget 경고도 보존. 패키징·cook·커밋·push 없음.

- 전달: Saved/QA/CharacterPipeline/sparrow-renaissance-20261027/preview.html#D5. 실제 신규17영상+이전9영상=26클립, 일반·변신/정속·반속/동일시점 비교. D/F/E/V=second60, W/R=third60, S=s-final60, A/Q=adopted60. clip-selection.json/game-manifest.json이 최종 출처다. MP4 디코딩 및 최종26클립 미디어 해시/존재 확인. 브라우저26선택/34이미지 로딩, 실제 프레임 진행·반속·동일시점·가로넘침0·콘솔경고/오류0 확인. W/R/S 과거영상은1024×576이므로 초기1280 판정만 false였고 실제 재조회 정상. browser-comparison.png/result.json/delivery-media-integrity.json/3독립검토 보존. tab4 deliverable, open_in_codex는queued 반환.

- 미적 판정: 중간본보다 실제 형태·체적·시간 대비가 개선되어 비교 가능한 적용본이다. 사용자의 미적 수용이나 레퍼런스 동등 퀄리티를 선언하지 않는다. A의 부드러운 황금 핵, Q 접점3갈래 반복, S 변신 날개와 광염 겹침, R의 기존 다발 구도는 남는 한계다. 페이지에도 A/R 범위를 표시했다.

- 정리: 이번 번호형 임시PNG8187개/15,509,774,970bytes만 경로·reparse 사전검사와 영상 디코딩/해시 보존 확인 후 삭제했다. 최종 잔여0,26클립 미디어 해시 불변. 소스·에셋·실패로그·명명된 스틸·중간MP4·원본 참조 보존. 최종 조회에서 소유UE/ffmpeg 프로세스 없음. 다음은 새 실제 게임 비교에 대한 사용자 평가다.


## 74. 10-27 Sparrow craft · D 잔광/F 충전/V 복원/E 수평 장식궁과 Q/R/A/S 재작업

- 적용·검증 완료 기록 2026-10-27T23:37:01+09:00. 이전 renaissance를 사용자가 반려했고 이번에는 D5만 수용했다. root 통합/D/F/촬영/검증, ea_rebuild E/A, qv_rebuild Q/V, wrs_rebuild R/S 분담. GPU/에셋 저작·빌드는 직렬, 사용자의 게임 프로세스를 종료하지 않았다. 기본값은 result.json과 adopted60/renaissance-defaults.json이 기준이다. W는 유지.

- D5는 발사 당시 활 자세를 고정한 잔광을 약1초 유지. F6은 Action1.05/Recovery1.23으로 조각응축→화살 유지→발사하며 일반1/변신3발과 피해80 유지. E7은 기존 동일 skeleton R_Ability_Fast_Fire 수평 모션과 480cm 단일 장식 활 표면을 실제 arrow_anchor에 연결했다. 원화는 image_gen으로 제작하고 실게임 재질에 사용; 투명 PNG와 정확한 prompt는 ArtSources/Craft20261027에 보존. 원화 자체를 게임 영상이라고 제시하지 않았다. 텍스처 상주/BC7과 명암 수정 후 실제 bow vertical fraction<.25, 단발60피해 확인. 작은 방향성 방출·접촉 면을 마지막 보강.

- V6은 최종 celestial-rebuild V4의 연결된 core72/가는 금색 필라멘트 재질과 원래 하단fade를 복원한다. 초기에 더 오래된 refined60/core12를 V4로 잘못 보고 흰 원통을 만든 시도는 반려했으며 실패author/캡처 로그 보존. source Custom 잔여노드와 연결노드를 구분해 복제본만 수정. 실제 V4/V6를 동일빌드에서 비교, FX Age=MID Age/동일MID, feetZ2.15/anchorZ.5/mesh하단중심Z.5 확인. 발밑 추적·외곽/중심/지면 순차소멸, 기존40초 상태·날개 unfold 유지.

- Q7은 변신에 원본 Gideon primary 유성 재료를 황금으로 복제해32광체/8파동으로 재구성. 원본 파일 불변. 분리된 spline mesh emitter만 제외하고 M_NoxSpark Color/Intensity를 황금으로 준 단일ISM 후류12cm/.18초/최대512점으로 연결. 실제 .82+n*.37 접촉/피해40/750범위 유지. 일반Q는 원래 금색 화살비로 복귀. A5는 A3 화살/160·108cm 링과 열린 곡면을 복원, A4 발톱/구체 제거. 반복 비행섬광이 중심을 가려 SparrowAnnularCraftArrow만 해당 섬광에서 제외; 실제 타격 파열과90피해/160속도 유지.

- S102는 v10 큰 대소 겹원형→수축→두번째 파동→15평행 근접화살을 복원하고 금빛 표면결 보강. S101 정확복원 비교도 제공. 기존 이동복귀 로직은 보존. R6은310발/10웨이브 유지, 실제 화살 표면과 원본 MuzzleGlow/Wisps/Sparks 3이미터 방출 및 작은 실제명중을 구성. Wisps 초기알파.10과 재질의-.5*RelativeTime/수명알파가 조기소거를 일으켜 transient StartAlpha만.85로 조정. 원본색/공간/수명/수량 불변. R 전방흐름은 정상시야에서 여전히 약하므로 시각 목표 달성을 선언하지 않는다.

- 검증: DebugGameEditor16.35초/DevelopmentGame44.9초/DevelopmentEditor44.58초 성공. normal DevelopmentEditor adopted60에서 selector10개 덮어쓰기 없이 확인, 최종210체크 및 QWERASDF 일반8·변신8 마우스 이동복귀 통과. Play-CurrentSkills.cmd --check 출력 확인. 기존 startup automation/retarget 경고는 그대로이며 장시간/모든지도 성능검증을 주장하지 않는다.

- 최종 촬영 출처: D/F=proof60, E/V=craft-erv60, S101/S102=craft-first60, Q/A/R=craft-final60. clip-selection.json/game-manifest.json 기준. 17신규+8이전=25영상, MP4/정속·반속WebP/동일시점스틸/전체시야 비교. 브라우저25선택의 로딩/넘침0/오류0, 실제프레임진행·반속·동일시점 확인. 탭7 deliverable. open_in_codex queued 후 CUA로 실제 페이지 확인.

- 정리: 검증된 중간·최종 영상을 보존한 뒤 번호PNG4920개/9306658342bytes만 경로/reparse 사전검사 및 삭제후 영상해시 재검증을 거쳐 삭제, 잔여0. 명명스틸/로그/원화/소스/에셋/비교영상 보존. R/S의 미적 한계는 sr-visual-review.json, Q/V 기준오판과 최종검증은 qv-craft-final-review.json, 전체visual-review.md에 기록. 다음작업은 사용자 평가이며 무조건 퀄리티 동일/전부만족이라고 보고하지 않는다.


## 75. 10-28 Sparrow plume · 첨부 깃활 형태 / D0 기반 / E 방향 / A 전이력

- 적용·검증 완료 2026-10-28T01:10:53+09:00. 사용자 첨부4장의 핵심은 흩날리는 입자 수가 아니라 활의 곡선에 붙은 겹깃 실루엣이다. D는 실제 활 위, E는 큰 수평 활이다. root 통합/F2안/A전이력/촬영/검증, ea_rebuild E/D, qv_rebuild Q/V, wrs_rebuild S/R로 파일을 분담했다. GPU 저작·촬영·빌드 직렬, 사용자 프로세스 강제종료 없음.

- D6: craft D0는 renaissance D5_r2였다. 현재 craft D5의 긴 정지잔광판을 쓰지 않고 이전 live .22/.72초 기반으로 복원. 실제 bow 본 6구간에 spline 깃을 붙이고 길이 유지/끝12·16·18cm/몸통 반폭약10.6cm/양쪽3~4절개. 원화 전체를 줄여 넣어 뭉친 초기본, 좁아 선처럼 보인 quill 중간본을 실제 촬영 후 보완했다. 원화 alpha의 이중 윤곽 절단을 제거하고 RGB는 내부결로만 사용. 카메라 보정 진단은 raw Up 내적이 아니라 UE Frenet 면법선의 6구간×3샘플로 교정했다. 최종 일반은 겹깃 외곽이 읽히며 변신은 원본 날개광과 겹쳐 덜 분리됨. d-visual-final.json 참조.

- E8: E7의 앞뒤가 바뀐 끝/시위 UV 세계배치를 수정. 끝X=-109.964cm, 시위=-122→-166cm, 실제 화살은+X. 480cm 수평 활/동일 R_Ability_Fast_Fire 모션과 단발60피해 유지. image_gen 내장 도구로 만든 투명 깃활 원화는 Tools/CharacterPipeline/ArtSources/Plume20261028/FeatherBow.png, 정확한 prompt는 generation.md. 실제게임0.25초에서 장식과 빈틈/지면분리/그립연결 확인. D/E 모두 이 원화를 전용 재질로 사용하며 원본 에셋은 보존.

- F7/F8: 기본 F6 유지. 1.05초 충전과 실제 F6 발사·명중은 같고, F7은18개 곧은 광편/3흐름, F8은36작은 광점/5나선 흐름으로 응축부만 다르게 만든 선택안. 실제 탄은 F6 tag를 사용하므로 새로운 flight/impact로 바뀌지 않는다.

- Q8/V7: 일반Q 유지. 변신Q40기둥/5개×8파동, 기존 .82+n*.37 접촉/피해40/750범위 보존. 20개 pool/120면 재사용. V는 원통 앞면 흰 중심 때문에 발 앞에서 끝나 보이는 문제를 실제 축 ribbon으로 분리. 중심광 .78~1.23→외피 .96~1.63→지면1.35~1.98초로 감쇠한다. 상태40초/날개전개/이동수명 유지. 첫 저작의 HLSL 예약어 line과 첫 촬영의 불투명 바닥판을 수정. Plasma_Wisps는8×8 flipbook이며 RGB B가빈영역에서도거의1이므로 Alpha·프레임12~62보간으로 실제광염접촉을 구성했다. 최종 Q갈래접촉 반복/V가벼운투명감은 잔여한계이며 qv-refined-visual-review.json에 실제프레임/런타임근거 기록.

- S103: S101 큰 대소 겹원→수축→15평행근접화살/450거리/54피해→.033차이 재점화 골격 유지. 전용 Plume 재질에 이동 광류/어두운틈/12개작은광편/짧은2차파열을 넣고 균일금색 바탕을 줄여 플라스틱고리 느낌을 완화했다. 기본 Sharp.Reference=3. S102 이전·S101 정확복원과 비교 가능. 원형구조 자체와 매끈함은 남는다.

- R0: sparrow-impact-revision-20261027/before/SparrowSkillComponent.cpp와 impact-recraft/before/SparrowArrow.cpp 이전 경로로 복구. 31×10/.13간격/준비.12/반각39/꼬리30~55cm·폭1.5~2 유지. R5/R6 actor·arrowoverride와 generic ascended R 추가접촉만 제외, 원래 BowGlow/ReleaseShards/RapidBow는 유지. Arrow원본블록 exact SHA 일치. 이동 복귀수정은 보존. r-rollback-evidence.json. root가 최종 변신 R0 .55초도 확인했다.

- A: 현재 A5 추가변경 없음. 남아 있는 실제 A영상50개를 파일 SHA 중복제거/시간순으로 정리했고 초기시안 원본링크4개도 보존. 문서A로 불린 실제S를 제외했다. 삭제된 자료를 복원한 것은 아니다. a-history.html/json,50개 실제 WebP는 전프레임 디코드, 브라우저 필터/26번 롤백 A0 재생 확인.

- 빌드: DebugGameEditor6.33초/DevelopmentGame47.80초/DevelopmentEditor41.78초 성공. normal DevelopmentEditor adopted60 기본10selector 덮어쓰기 없이 확인·241체크·QWERASDF 일반8/변신8 실제 마우스 이동복귀 통과. 이후 D소유 메시 폭/절개만 보완하고 d-final60 일반/변신 실제촬영·기능체크 통과, native/충돌/입력 변경없음으로16건을 다시 반복하지 않음. Play-CurrentSkills.cmd --check 통과. 기존 startup Condition failed/retarget 및 author의CPUaccess조회 경고 보존, 새로운 실행의 material/Python실패·VRAM초과는 발견되지 않음. 패키징/cook/장시간벤치/커밋/push 없음.

- 전달: sparrow-plume-20261028/preview.html#E8. 신규14+이전12=26실제클립. D=d-final60, E/F/R일반=first60, 그외=refined60. clip-selection/game-manifest가 최종출처. MP4/정속·반속WebP/동일시점 비교/1.6배 확대. 브라우저26선택 로딩·넘침0·오류0·실제프레임진행·반속·동일시점 확인, 최종D2클립교체 별도확인. browser-comparison.png, browser-final-d.json, delivery-media-integrity.json. 최종 tab10 deliverable, A이력 tab9.

- 정리: 번호형 임시PNG 3324개/6299078508bytes만 범위·reparse 사전검사 및 영상디코드/해시확인 후 삭제, 잔여0. MP4/명명스틸/로그/원화/소스/실패근거 보존. 기능 통과와 미적 수용은 구분하며 레퍼런스동등/전부만족을 선언하지 않는다. 다음은 실제 비교 피드백 및 F/A 선택이다.


## 76. 10-28 Sparrow 선택안 채택 · D 실제 활 장식궁 · A4 복원

- 사용자 채택: F7/V7/S103/R0. A는 async 답변으로 이력05 ‘A4 나선 파편 꼬리’ 확정. 실제 기본값 FDesign7, DesignIngame.V7, Sharp.Reference3, ArsenalStudy.S0/R0, SunArrow.Style6. D는7로 보완. Q8/E8/W1은 보류·분석 또는 변경요청 없음으로 유지.
- D7: 기존D6 작은 spline깃 대신 기존 E8 깃활 원화 메시/재질의 독립MID를 실제 bow grip/팁 span에 맞춰 사용. 장식범위 팁 span1.2배/깊이1.6배, 실제 활 길이 수준. 첫본은 너무 비스듬히 보여 반려; 최종 카메라 투영축과 실제 팁중간점 기준 곡률 방향으로 정렬. 예전 전방으로 늘어나는6가닥 release tail은 D7에서 제외. 피해65/6500속도/단발관통/경로 낙하깃털/입력 불변. 변신에서는 원본 날개광과 장식 세부가 여전히 겹친다.
- A 이력05: Python 시안이었던 원본을 native GearArrow로 이식. 원본 Flames2 transient복제/3파편/반경46/후방24·70·116/9rad/s/.11초방출/.44수명, 원본 작은깃털환·화살축·핵.36. 최근외피/태양핵/flight crackle 제외. 현재 피해90·속도160·모션/이동복귀 유지(옛 영상 속도220 전체롤백 아님). a-selection-evidence.json/a-visual-review.json. root와 A담당이 실제 일반/변신 프레임 확인.
- E 읽기전용: 장전은302cm 수평선, 실탄은190cm 별도탄/실제 약18.4도하향, 큰 잎형 방출광720cm/s와 실탄6000cm/s가 분리되어 보임. .30~.40초 실제영상·소스 근거 e-audit/analysis.md. 이번에 E 수정 없음.
- 검증: fresh DebugGame applied60 기본10값 덮어쓰기 없이 확인, A/D/F 일반3·변신3 실제 마우스 이동복귀6건 통과. A/D 영상 기능검사 통과. 이후 D 면방향/폭만 보정해 d-aligned60 일반·변신 재촬영; 입력/충돌변경 없어 이동6건 반복안함. 최종 DebugGame8.44초/Game35.94초/DevelopmentEditor28.46초 성공. Play-CurrentSkills.cmd --check 통과. 초기 A FVector_NetQuantize 삼항 컴파일오류 수정/실패로그 보존. 자동승인검토 timeout으로 마지막 D 빌드가 실행되지 않았고 사용자 계속 요청 후 동일빌드1회 재시도 성공. 사용자 프로세스 종료 없음.
- 전달: sparrow-plume-adoption-20261028/preview.html. D=d-aligned60, A=applied60. 신규4MP4 전체디코딩/8WebP 전체프레임 디코딩, 기존채택F7/V7/S103/R0와 D6/원본A4는 이전영상 참조. 브라우저10이미지 로딩/가로넘침없음/변신펼침 확인. 적용과 미적수용은 구분하며 E/Q 미수정 명시.
- 정리: 적용/중간/최종3촬영 폴더의 번호PNG1128장2128129193bytes를 동영상 보존/디코딩·해시/경로·reparse사전검사 후 삭제, 잔여0. 대표스틸/실제영상/원화/소스/로그 보존. 패키징/cook/성능벤치/커밋/push 없음. result.json에 정확한 완료시각 기록.


## 77. 10-28 W 사용자 지정 이전 영상으로 복원

- 사용자가 sparrow-reart-20261027/W_normal.mp4를 원래 W로 확인하고 복원을 요청했다. SparrowShotWave.cpp의 Sparrow.Renaissance.W 기본값1→0 한 줄만 변경. 새 준비압력면/갈라지는 광면을 비활성화하고 기존 준비입자/겹원형 파문/방출광 경로 복구. 나머지 네이티브 코드 불변, 새 기본값 검사 기대값만0으로 갱신.
- fresh DebugGame proof60에서 기본10값 확인(W0, 나머지 F7/V7/S103/R0/A6/D7/E8/Q8 유지), W 일반4발·변신5발/기존피해/다섯번째 타격/날개idle/일반·변신 실제마우스이동복귀 통과. 원본영상.70초와 실제.70초, 변신1.5초 화면 확인. 일회성입자랜덤/접촉프레임 완전동일을 주장하지 않음.
- 최종 DebugGame38.11초/Game25.60초/DevelopmentEditor18.82초 성공. Play-CurrentSkills.cmd --check 통과. 사용자 프로세스 종료/공유재질 저작/다른스킬 변경 없음.
- 결과: sparrow-w-restore-20261028/result.json. 신규 실제 W0_normal.mp4/W0V_form.mp4 전체디코드·해시 확인, 원본과 대표스틸 보존. 임시 번호PNG270장508350078bytes 안전경로·해시확인 뒤 삭제/잔여0. 패키징/cook/커밋/push 없음.


## 78. 10-28 Sparrow Q/E/S/D/F/Space 비교안 · W 원 반전 · A 흩날림 정돈

- 사용자 요청: 변신 Q는 빛줄기들이 한 번에 꽂히는 안, E 중앙 깃활 및 S/D/F는 현재 골격을 유지한 화려한 여러 안, V Space는 출발/도착 양쪽 효과. W 원 크기 흐름 반전과 A 파편 정돈은 실제 반영 요청.
- 기본 변경은 네이티브 2파일만: SparrowShotWave.cpp의 W0 원은 캐릭터 쪽 큰 원에서 전진하며 축소, SparrowSawVortex.cpp의 A6은 3갈래/반경46/.44수명에서 2갈래/반경25/.28수명 및 작은 파편으로 정돈. A160속도/90피해, W일반4/변신5와 기존 판정·입력·이동은 유지.
- 선택용: Q1 일제낙광, E1 중앙겹깃/E2 이중깃맥+플라즈마/E3 불사조심장, S1 분절광륜/S2 나선수렴/S3 깃날파열, D1 깃결점화/D2 쌍깃수렴/D3 별광세공, F1 균열광/F2 삼중흐름/F3 백금파쇄, B1 출발수축·도착개방/B2 쌍점깃잔광. Q는 변신만, 다른 4스킬은 일반·변신 각각 비교. 원래 E8/Q8/S103/D7/F7/V7 등 선택값과 원본 에셋은 보존. Q1의 시각만 한 번이며 원래 8피해 펄스는 유지한 시안이다.
- 도구: Tools/CharacterPipeline/sparrow_polish_studies.py, 기존 new_skills_probe/editor_task 재사용. Python 시각 관측은 최대 한 프레임 늦을 수 있다. 새 재질/에셋 저장 없이 기존 깃활 원화와 원본 Flames2 등을 런타임에서만 사용. 시안이 기본 키에 설치된 것으로 보고하지 않는다.
- 검증: final-first30/final-rest30/texture-final30 통과. W두 원의 실제 위치·크기에서 근처가 더 큼을 일반/변신 모두 확인, 4/5발 유지, A단발160, B1/B2 실제480cm와 native 조작복귀 확인. DebugGameEditor/Game/DevelopmentEditor 빌드 성공. 기존 전체8키 회귀를 재실행한 것은 아니며, 미적 선택은 사용자 대기.
- 전달: Saved/QA/CharacterPipeline/sparrow-polish-20261028/preview.html#E, 실제31클립/MP4·정속·반속WebP·같은시점·확대. E-comparison.png는 실제0.25초 화면의 부분확대 비교. 최종31개 MP4해시와 전체디코딩 확인, 브라우저8키/14상태/37이미지 로딩·가로넘침0·반속·동일시점 확인. 결과 result.json/native-verification.json/browser-verified.json. 마지막 E2/S2/D2/F2 영상 출처는 texture-final30.
- 실패도 보존: pilot30 미지원 Python getter, pilot-fixed30 Blink의 목표 허수아비 충돌, final-more30 일반/변신 임시 액터 이름 재사용 문제. 촬영 도구/fixture를 수정했고 게임 이동·충돌을 완화하지 않았다.
- 로컬 공유 서버55811은 중지 상태라 같은 Saved/QA/CharacterPipeline 루트로 복구했고 유지한다. 사용자 프로세스 강제 종료 없음. 패키징/cook/성능벤치/커밋/push 없음. 선택되지 않은 시안을 설치하지 않는다.


## 79. 10-28 Sparrow 에너지 방향 재설계 · E1 채택/A 타원 공전

- 사용자 평가: W 확인. E1 사전 문양→실제 사격→문양 소멸 선택, 활 중앙/양끝 첨두 강조와 나머지 몸통 가늘게 요청. A는 좁은 후류가 아니라 타원을 그리는 회전 흐름. S/D는 선·문양보다 불꽃·빛의 응축과 폭발감을 명시. F는 매우 긴 창형 화살, 촉/꼬리 강조와 조립 대신 흡수 허용. V Space는 짧고 강한 두 지점 효과. Q는 제로베이스 1안.
- 실제 설치: E8 기본 selector는 유지하되 M_E9FeatherBow 새 원화 사용. ERegaliaSeal은 기존 작은 겹깃+마름모 E1 문양이며 NotifyShot 후 .015~.12초 소멸. E8 장전 중 미리 그리던 화살 선은 생략하고 실제 단발을 유지. E9 전용 텍스처와 재질을 추가하여 D가 공유하는 기존 E8 원화/재질은 보존. A6는 FeatherRings를 타원 비율로 바꾸고 M_EllipseWisps의 두 회전 화염으로 교체, 주변으로 튀는 LegacySpiralShard 비행 방출은 제거. 중앙 화살/광핵/실제 명중은 유지.
- E 원화는 imagegen 편집, ArtSources/EnergyFeedback20261028/FeatherBow-sharp.png와 generation.md에 입력 출처/정확한 prompt 보존. 이번에는 기존 첨부에서 파생한 FeatherBow.png를 확인했으며 원본 첨부 네 장을 다시 본 것은 아님. 원화 자체를 게임 영상으로 제시하지 않는다.
- 새 방향 실제 PIE 시안만: Q2 광핵 응축→굵은 낙하→지면 화염 폭발, S4 압축→전방 화염 파열, D4 활 응축→분출, F4 빛/불꽃 흡수→마지막 3D 장창 화살 펼침→실제 탄 추종, B3 실제 출발/도착 .18초 파열. 이 다섯은 기본 스킬에 설치하지 않았다. F는 새 513cm 길이 3D 메시 SM_FLongLance에 8각 축/4면 촉/4꼬리깃. 피해/충돌은 원래 탄, Q 피해8회도 그대로다.
- 산출물 Saved/QA/CharacterPipeline/sparrow-energy-feedback-20261028/preview.html#Q, 신규 실제9클립. E/A 일반·변신, 나머지는 대표1조건. E=first30 두 클립, 나머지=refined30. first30 69체크/refined30 50체크는 단계별 결과로 최종 회귀 수에 합산하지 않는다. E 문양 선행/사후0·실제1발, A160, Space480cm, 각 조작복귀 확인. 실제 대표 스틸과 영상 검토.
- DebugGameEditor 최종7.23초, DevelopmentGame21.73초, DevelopmentEditor12.52초 빌드 성공. 전체 스킬 회귀/패키징/cook/commit/push 없음. W 소스 이전해시49e13d69a06dd80c32cd3637a865aebe39376ae4317dcde92f7dc1c0387db0a0와 동일. 두 native cpp의 BOM/CRLF 보존과 diff, before 백업, result.json 기록.
- 브라우저 7탭/신규9클립 로딩, 넘침0, 이전·수정본 양쪽 반속과 .25초 동일시점 확인. 단일 모드 후보로 이동하면 해당 상태 자동선택해 빈 화면 방지. CUA의 이전 연결 browser.user unavailable은 세션 초기화 뒤 기존 브라우저2의 탭2로 복구했고 최종 Q deliverable. 기존 비교 탭1/공유서버55811은 종료하지 않음. 원화/재질/3D 메시의 첫 중간본과 번호 캡처도 보존.
- 다음은 새 단일 방향의 사용자 평가. S/D는 응축과 폭발 구간을 분리해 맞추고, 형태가 맞은 뒤 밀도/밝기/잔광을 조절한다. 미적 수용·원본 레퍼런스 동등 퀄리티를 선언하지 않는다.


## 80. 10-28 Sparrow 전체 조화 재작업 적용본

- 사용자 지시: 3/4번의 색 복사가 아니라 주효과·보조효과·형태·타이밍의 완성도를 기준으로 재작업 승인. 원본 까마귀활 첨부4장을 다시 확인. W는 기존 확인본 유지. 후속으로 카운테스 QWERASDF/V/Space 전수 재창작까지 요청됨(기존 규칙 제약 해제, 쓸 만한 기반 재사용 가능).
- 새 native SparrowHarmonyFX는 충돌/피해/조작 상태를 소유하지 않는 효과 전용 배우. Q13개 동시 낙하+지면 접촉, A 두 타원 잔류광, S 응축 흐름→발사, D 실물 활팁 결속광, F 흡수→세공 화살/실제탄 추종, V Space 실제 출발/도착 짧은 접촉광. E는 원본 참조의 두 안쪽 갈고리/양끝 겹날/가는 연결부를 강조. E1 문양 선행→실제 발사→문양 제거 보존.
- 새 Harmony20261028 에셋9개. built-in imagegen 투명 원화2장, alpha/명암 기반 앞뒤 relief 메시와 경계 체적. 활480cm/화살320cm 기본. 완전한 production 3D 복제품 아님. 첫 절차형 단색 메시가 납작한 꽃잎으로 보여 자체 반려하고 최종 원화/relief로 교체. ArtSources/Harmony20261028/generation.md에 정확한 prompt/출처 보존. 원본 source pack 변경 없음.
- 적용은 E8/A6/D7/F7/Q8 selector 유지, Sparrow.Harmony1 기본으로 새 표현 사용. F 실제1/3발·속도5200·피해80, S15발, A160/90, Space480/.065, Q8회 피해 등 게임 판정 불변. F 새 표현도 CrystalArrow 태그/기존 ImpactScale.32 보존, 세 발 각각 실제 탄 방향 추종. W 해시49e13d69a06dd80c32cd3637a865aebe39376ae4317dcde92f7dc1c0387db0a0 일치.
- refined30 실제12조건 115체크 통과(각 실제 마우스 이동복귀/E 문양 전후/A속도/Space이동/F취소·캐릭터전환 정리). 마지막 F 보정 후 final-f30 일반/변신20체크 별도 통과. 수치를 합산해 전체 회귀로 보고하지 않음. DebugGameEditor18.32s/Game68.76s/DevelopmentEditor31.17s 성공. 사용자 에디터 강제종료 없음(최종 프로세스 조회에서 실행 중인 에디터 없었음). 기존 startup Condition failed/retarget/animation divide-by-zero 경고 보존; 로그무오류 주장 안 함.
- 전달 sparrow-harmony-rework-20261028/preview.html#E, 정상/반속 MP4·WebP, 동일시점·확대·이전본 비교. 신규12클립, F는 final-f30/나머지는 refined30. 전MP4/WebP 디코드와 최종영상 해시 확인. 브라우저7키/12조건 이미지 로딩, 양쪽 반속/동일시점 확인. 단일 변신 영상은 넓게 표시. 새 탭3 deliverable, 이전 탭/55811 서버 유지. 미적 수용은 사용자 피드백 대기.
- 선택된 영상의 번호형 PNG613장1158517193bytes만 경로/reparse/영상해시 사전검사 뒤 삭제, 잔여0. 명명 스틸/중간 반려본/실패로그/원화/에셋/소스 보존. 패키징/cook/commit/push/메모리 업데이트 없음. 다음 작업은 카운테스10스킬의 현재 모션·효과 확인 뒤 전수 재작업.


## 81. 10-28 Countess QWERASDF/V/Space 전수 재작업 적용본

- 사용자 후속 승인: 스패로우 완료 뒤 카운테스10개도 새로 만들기, 기존 스킬 규칙 유지 의무 없음, 쓸 만한 기반 재사용/제로베이스 모두 허용. 과거 카운테스 고정 설계 제한보다 이번 지시 우선. 새 task/agent/automation/goal 생성 없이 같은 작업에서 진행했다.
- 현재 Q35/복귀, E55/지면240, R90/공유hitset3지점, A6x10/이동하는 분신2개, S진입24/24초악마화/신규피해1.2, D3x18, F최대750/6초/안전착지, V12x7/3.8초, Space220/.16초/별도6초를 재사용. Q는 실제 명중 때 쌍곡면 검격으로 교체. E/R/D는 새 RebirthFX 입체 갈고리/3지점 관통/3연타 곡면 베기로 주효과 교체. A/V는 실제 무기·분신 애니메이션 재사용, 기존 넓은 Ink opacity.28배로 줄이고 주 궤적·타격·마무리 조형을 추가. S는 입체 어깨 혈갑/진입, F양지점 짧은 절단광, Space는 별도 후퇴 절개. 새 애니메이션10클립 제작이라고 주장하지 않는다.
- W가 비어 있어 실제 신규 공격 추가: slot1, Ability_RMB 기반 .22발동/.65복귀/8초쿨, 전방190중심/반경220/반폭160, 피해65(악마화78). GetSkillDisplayName/쿨다운/진입/HUD 연결. KwangPlayerController에 있던 Countess 전용 W 차단을 제거해 UseSkill1로 연결(타 직업은 원래도 같은 UseSkill1 경로). native 취소/예약피해/쿨다운/입력복구는 기존 Reforge 체계 사용.
- 새 CountessRebirthFX.cpp/h는 시각 전용. 전용 Rebirth20261028 4에셋(M_BloodCut/M_ObsidianVein/SM_TwistedCut/SM_HookedFang). 기존 Countess 원본 ink 읽기/소유 그래프·OBJ 경로 재사용, source pack 저장 없음. 첫 참격이 거의 안 읽히고 E가 막대로 보여 자체 반려, 면 UV/밝기/단면 폭·곡률·접촉 연무를 보완. V 악마화의 갑옷은 실제 mesh 상대 높이 변화를 따라가고 mesh 숨김 때 가린다. Countess.Rebirth1 기본. 0은 새 시각 효과 비활성화용이며 신규 W까지 원복하는 완전 롤백이 아니다. before 백업을 보존.
- 실제 입력 검증: normal30 일반10/99검사, form-fixed30 악마화9/91검사, safety60 W60fps+S만료재질/연계/V중Space/예약이동·거절평타/F안전착지·벽/8스킬전환 정리 등218검사 통과. 마지막 S장식 mesh 추종은 시각 변경뿐으로 v-follow30 V악마화1개/10검사 재촬영·검사, 기존 기능 통과 재사용. 단계별 수치를 합산해 전체회귀라고 보고하지 않는다.
- 실패 근거 보존: baseline30 F목적지 더미·순간캐스트busy가정으로 중단, 기존7유효기준+baseline-tail30 F/V/Space 사용. pilot30 W실제키 차단발견 후 controller 수정. pilot-w30 비노출 cooldown Python getter를 실제 재사용 거절/8초후 재허용으로 교체. form30 read-only Health직접설정을 기존 ResetDummy호출로 교체. 실패한 run 전체를 통과로 바꾸지 않음.
- 최종 DebugGameEditor7.37초/Game38.78초/DevelopmentEditor29.56초 성공. Play-CurrentSkills.cmd --check 통과. 초기 author의 그래프 재연결 중 Missing ComponentMask/compile경고가 남지만 fresh form/safety/v-follow의 material compile failure/Fatal/Python error는0. 기존 startup Condition failed/애니메이션 경고는 보존. 사용자 프로세스 강제종료/3·4번 편집/서버작업/패키징/cook/성능계측/commit/push/메모리업데이트 없음.
- 전달 countess-rebirth-20261028/preview.html#W. 신규19(일반10/악마화9)+이전10=29 실제 MP4와 정상/반속WebP. V악마화=v-follow30, 기타악마화=form-fixed30, 일반=normal30. 전부 디코드·최종영상 해시 확인, 브라우저10전후/9악마화 로딩, 양쪽 반속/동일시점/1.6확대/넘침0·콘솔오류0 확인. 대표 게임 시점 직접 확인과 전체 미디어 디코딩을 구분하며 미적 채택·3번 동등품질을 선언하지 않음.
- 영상이 보존된 선택 케이스의 번호PNG1713장3049556343bytes만 절대경로/reparse/크기/영상해시 사전검사 뒤 삭제, 잔여0. 명명스틸/중간·실패증거/원화/소스/에셋/실제영상은 보존. 신규 결과 tab5 보존; Sparrow는 도구중복tab3만 닫고 동일한 결과 app tab4 보존, 이전 user tab1/2와 서버55811 유지. 다음은 두 캐릭터 실제 재작업본에 대한 사용자 피드백.


## 82. 10-29 Sparrow S 롤백 · A 기존/신규 쌍화살

- 사용자: 2번 스패로우임을 재확인. S는 롤백, A는 비교적 괜찮으므로 기존 화살과 새 화살이 살짝 떨어져 동시에 나가도록 요청. 카운테스/다른 스킬은 이번 수정 대상 아님.
- S: SparrowSharpVolley.cpp/h를 sparrow-harmony-rework-20261028/before와 byte-for-byte 동일하게 복원. 새 Harmony S 생성/발사신호/기존 면 숨김 제거, 기존 S103 및 15발 유지. 비교용 S4 불꽃 시안은 원래 설치되지 않았으므로 그 시안으로 교체하지 않았음.
- A: SparrowSawVortex.cpp의 A6 기존 시각 부품(ArrowMesh/ArrowTrail/SawRotor/CondensedCore)을 살리고 로컬Y -80cm. 새 Harmony Orbit은 실제 탄 중심의 오른쪽 +80cm를 추종. 두 외형 중심160cm 간격, 기존 중앙 실제 탄1개/속도160/피해90/표적당1회 판정 유지. SparrowPairedA 태그와 APairHalfSpacing 상수 사용. 에셋/카운테스/W 변경 없음.
- 기존 sparrow_energy_feedback.py에 A4/S6 검사만 추가. verified30 일반/변신4조건48체크 통과: 실제입력/조작복귀/실마우스이동, A 두 외형+기존90단발피해+측면제외/160속도, S15발/새 Harmony S 없음, 소유자전환 정리. 첫 paired30은 QA가 ArrowTrail 대신 필드명 TrailParticle을 조회하여 실패; 코드명 대조 후 수정, 실패증거 그대로 보존.
- DebugGameEditor81.04초/DevelopmentGame71.66초 빌드성공, Play-CurrentSkills.cmd --check 통과. 사용자 DevelopmentEditor PID37656 실행 중이라 강제종료/해당DLL덮어쓰기 하지 않음. 현재 사용자 에디터에는 이전 모듈이 로드되어 있으며 새 실제 플레이는 Play-CurrentSkills.cmd 사용. DevelopmentEditor 재빌드는 종료 후 필요.
- 출력 Saved/QA/CharacterPipeline/sparrow-as-adjustment-20261029/preview.html#A. 실제4클립MP4/정속·반속WebP/동일시점 스틸. 전체디코드/영상해시, 브라우저4조건/양쪽반속·스틸/콘솔오류0 확인. 기존tab4를 이 결과로 이동해 보존, 다른탭/55811서버 유지. 미적채택은 사용자 피드백 대기. 번호PNG/실패증거 보존, 패키징/전체회귀/커밋/메모리업데이트 없음.


## 83. 10-29 Sparrow A 전체 이력 재정리 · 구버전 오선택 확인

- 사용자: 쌍화살에 들어간 이전 화살이 원하던 버전과 다르다고 확인, 지금까지 A를 모두 정리해 달라고 요청. 이번에는 게임 소스/에셋/설치를 추가 변경하지 않음.
- 기존 sparrow-plume-20261028/a-history.json/html의 실제50영상/초기4원본페이지를 확인하고 기존번호01~50 유지. 후속10영상 추가하여60영상. 일반/변신·중간보정 포함이며60개 최종설계를 뜻하지 않음. 전체 경로/MP4해시/포스터 디코드/움직임첫프레임 확인, 기존 전체 디코드 증거 재사용.
- 중요한번호: 05=A4 나선파편꼬리 원본(이전선택기록), 51/52=그원본 재적용 일반/변신, 53/54=파편정돈, 55/56=타원공전(이번 쌍화살에서 잘못고른 기존화살), 57/58=Harmony 새화살, 59/60=현재 쌍화살. 사용자에게 원하던 구버전으로05를 확정한다고 단정하지 말고 번호선택을 받음.
- URL http://127.0.0.1:55811/sparrow-plume-20261028/a-history.html . 기존tab4에 열어보존. 최근6단계썸네일/전체60카드/날짜·상태·번호검색/한개재생·확대/두개비교. 브라우저60카드,10/28필터8개,05검색,05+55움직임두개로딩,콘솔오류0 확인. 원래HTML/JSON은 .before-20261029로보존. a-history-key-frames.png는실제대표스틸확대모음이며동일시점비교아님.


## 84. 10-29 Sparrow A 왼쪽 53번 교체 · Claude 병행 규칙

- 사용자 확정: 현재 쌍화살 왼쪽을 이력53으로 교체, 오른쪽 Harmony 화살 유지. 53=sparrow-polish-20261028/A_normal.mp4의 작은 나선 파편 꼬리. energy-feedback/before/SparrowSawVortex.cpp SHA가 polish native-verification의 a9c9ac19bd0d0d915514b22c1275e215676cbf3ad121373a657c6438f7744498과 일치하여 정확한 기준 소스 확인.
- SparrowSawVortex.cpp만 native 수정. 타원 재질/늘어난 고리 제거하여 원래 깃털 고리 복구; 두 갈래 반경25/방출.14초/수명.28초/크기.24 나선 파편 복원. 월드 파편도 기존 왼쪽 -80cm 차선으로 이동. 오른쪽 Harmony/간격160/속도160/피해90/중앙 실제 탄1개 판정 유지. S롤백/W/상태부여 호출부 미변경.
- 기존 sparrow_energy_feedback.py에 A5 선택과 왼쪽 고리·파편 위치 검사 추가. 결과 경로 Saved/QA/CharacterPipeline/sparrow-a53-pair-20261029. DebugGameEditor31.08초 빌드 성공. 맵조사 에디터 PID11344가 계속 실행 중이므로 추가 에디터를 띄우지 않았음. 이 작업의 대기용 PowerShell PID46976만 식별·종료하여 자동 실행 예약 없음. 소스 수정/DebugGame 빌드 완료, 일반·변신 실제 화면 검증은 미실행. 새 preview 영상 없음. 다음 검증 시 다른 에디터와 UBT가 비었는지 다시 확인하고 A5 일반/변신만 수행할 것.
- Claude 병행: Source/LearnTopDown/Arena/ 및 Content/Arena/는 Claude 소유, 스킬 작업은 건드리지 않음. SetCombatStatus 공용 인터페이스 분리는 사전 통지하고 스킬 작업이 쉬는 시점에만. 빌드 직전 UBT(특히 dotnet 명령행) 확인/완료 대기/-WaitMutex 사용. 사용자·자동화·DebugGame 합쳐 에디터 하나, 기존 프로세스 종료 금지. AGENTS.md와 사용자 요청 메모리 노트 20261029-004200-learntopdown-claude-coordination.md에 기록. 기존 도구의 DebugGame 병행 가능 주석보다 새 규칙 우선.


## 85. 10-29 ue-vfx 스킬 설치 · Countess W 원본 칼바람 재구성

- 사용자 요청: 반복되는 품질 실패를 막을 제작 절차를 개인 스킬로 저장하고 그 스킬로 1번 Countess W 재작업. 설치 C:/Users/USER/.codex/skills/ue-vfx(Skill is valid!, UTF-8/UI YAML/참조 확인). 원본 전체 FX의 재질·동작·침식 보존, 실제 카메라 비교, 반려 형태 수치 변형 반복 금지, 사용자 채택/빌드/화면 확인 구분, 저비용 짧은 미리보기. 프로젝트 참고에 Claude 소유/단일 에디터/UBT 규칙 포함. 호출 `$ue-vfx 카운테스 W 재작업`으로 재사용.
- 최종 native: CountessRebirthFX.cpp/h의 W 분기만 별도 처리. 거절된 TwistedCut/HookedFang 로드·렌더를 W에서 제외. 원본 P_Countess_BladeSiphon_Trails의 메시/재질/곡선을 그대로 쓰며 전방190/발높이+8/scale.5. 양검의 실제 FX_WeaponBase/Tip 소켓에 원본 p_CountessMeleeTrail 연결, .20초 뒤 방출 종료. 배우 수명2.5초는 소멸 정리 상한이며 주효과는 .9초 프레임에 사라짐. 기존 피해65/쿨8/.22commit+.04pulse/.65복귀 유지. CountessSkillComponent/Reforge, KwangTrainingDummy, SparrowA53/Harmony 보호 파일 hash 불변. Arena 및 원본 에셋 저장/편집 없음.
- 초기 XSlash(source30/lod30/ink30/facing30)는 생성/재질 적용에도 게임 카메라에서 거의 보이지 않아 내부 반려. LOD 누락을 원인으로 먼저 단정했으나 보정만으로 해결되지 않아 정정함. 원본 칼바람으로 교체한 current30은 너무 커서 최종 .5크기로 축소; 실패·중간 증거는 보존. 완성도 백분율이나 3/4와 동등 품질 주장 없음.
- 최종 DebugGameEditor6.24초 빌드 성공. 대기 후 엔진 Fab.uplugin 외부 변경으로 FabToolset이 installed UE5Rules에 없다는 오류 발생. UBT의 정확한 단수 옵션 `-DisablePlugin=Fab`으로 이번 빌드만 제외하여 해결(복수 -DisablePlugins는 효과 없음). 엔진/프로젝트 설정 파일은 수정하지 않음. 이후 빌드도 해당 엔진 문제가 남아 있으면 이 옵션 필요. DevelopmentEditor/Game 재빌드·패키징 없음.
- 최종 final30 실제 W 일반 상태 24체크 통과: 실제65피해/측면제외/입력복귀/취소/8초쿨/소유자전환 정리. 연속 캡처 중 발생·최고점·소멸 프레임 직접 확인. 변신 상태 미촬영, 사용자 미적 채택 미결. 한 에디터만 사용했고 다른 작업 프로세스 종료 안 함. Sparrow A53 실제 검증은 사용자 요청대로 계속 미실행.
- 결과 Saved/QA/CharacterPipeline/countess-w-source-20261029/result.json, W_normal.mp4(41프레임/30fps), 단순 전후 preview.html. 영상 전체 디코드 통과. 사용자 비용 선호에 따라 짧은 영상 하나와 기존 전 버전만 비교. 서버55811 유지, 원본·실패 증거·번호PNG 미삭제.


## 86. 10-29 W 사용자 반려 · 완료 판단 정정

- 사용자가 W 결과에 실망을 표시하고, 원인 규명 요청 뒤에도 근거 없는 성공 확신을 반복했다고 지적. §85 W는 품질 목표 달성본이 아니며 result.json visual_acceptance를 rejected_by_user_quality_goal_not_met로 정정. 기능 통과24개는 그대로 사실이나 시각 품질 통과 근거가 아님.
- 확인된 반복 원인: 3/4 실제 성공 장면과의 비교 없이 원본 FX 재사용을 해결책으로 단정; 시인성 문제 해결로 목표를 축소; 원본 로드/기존 메시 제거/게임 판정 검사를 품질 증거처럼 보고; LOD 가설을 확인 전에 원인으로 단정. ue-vfx 문서의 절차가 실제 결과의 품질 향상을 입증하지 못했음.
- 놓친 구체적 장면: final30 t0333은 주효과가 거의 없는데 표적 HP35, t0450은 피해가 이미 적용된 뒤 회오리가 강조됨. 정확한 지연 시간의 계측은 아니지만 타격과 주효과 강조가 분리된 관찰을 완료 판단에서 놓침. native 코드/에셋/스킬 문서는 이번 원인 감사에서 수정하지 않음. 3/4 동등 품질 재현 능력이 입증됐다고 주장하지 말 것.


## 87. 10-30 혈액 B2 사용자 채택 · 플레이어 4종 기본 적용

- 사용자 확정: B2의 길게 뻗은 액체 조각·얇은 가장자리·늦게 떨어지는 굵은 방울을 채택하고 전 캐릭터 적용 요청. 이전 A/B는 보존하며 현재 기본값은 B2다.
- 공통 `UPlayerCombatComponent`가 `/Game/TopDown/Combat/FX/BloodStudy20261030/P_FleshHitB2.P_FleshHitB2`를 사용한다. 카운테스 전용 혈액 생성 조건을 제거해 1카운테스/2스패로우/3기드온/4오로라 모두 적용. 멤버는 `FleshHitEffect`로 정리하고 편집기 비교 명령의 반영 경로도 함께 수정했다.
- 피해·무적·명시적 CC는 불변. 카운테스 일반 피격의 무경직 상체 반응과 다른 3종의 기존 짧은 경직·복귀 유지. 기존 `spine_03`/물리 표면 trace와 scale .48 사용. B2 파티클·재질 4개는 사용자 채택 당시 해시와 일치하며 새로 변형하지 않았다.
- 실제 기본 설정으로 몬스터 공격 4종 각 1회 확인, 미리보기 override 없음. 각 50프레임 및 관련 69검사 통과: 한 번의 B2 생성·몸통 근처 발생·무적 중 중복 생성 방지·캐릭터별 반응/보행 복귀·이펙트 정리. 정상 상태 대표 조건이며 전체 스킬/변신 회귀는 수행하지 않았다.
- DevelopmentEditor 49.21초, Development Game 73.79초 성공. Editor에는 기존 Fab 우회 옵션을 사용했고 Game에서는 해당 옵션이 지원되지 않아 제외한 뒤 통과. 엔진·타깃 설정 변경 없음. 단일 에디터 종료 코드0, 배속/FPS/백그라운드 제한 복원. 패키징/cook/커밋/push 없음.
- 결과: `Saved/QA/TrialTower/blood-all-characters-20261030/review.json`, `all-characters.webp/png`, before/final-files. A 원본 보관은 `countess-blood-ab-20261030/A`, B 비교는 같은 폴더의 B, 선택 B2 제작/비교 기록은 `countess-blood-b2-20261030`. 기존 `CombatFX.PreviewFleshHit A/B/B2`는 현재 PIE 플레이어만 바꾸며 새 PIE의 기본값은 B2다.

## 88. 10-30 카운테스 연속 피격 재반응 · 1번만 적용

- 사용자 설명은 피격 도중 새 타격이 와도 첫 동작만 이어지는 문제다. 대기 자세 문제가 아니라 0.75초 피해 보호 중 후속 타격의 시각 반응을 원했다. 피해 보호와 반응 시간을 분리하는 방향을 승인받아 1번 카운테스만 수정했다. 공통 변경은 1번 검증·최종 확정 후 전체로 확대한다는 규칙은 AGENTS.md에 기록됐다.
- PlayerCombatComponent.cpp/h에 LastDamageReactionTime/GetDamageReactionAge 추가. CanShowDamageReaction이 허용하는 카운테스만 피해 보호 early return 전에 반응 시간·방향을 갱신한다. CountessDamageAnimInstance.cpp는 새 시간값을 사용하며 캐릭터 교체 시 새 시간을 초기화한다. HP/0.75초 보호 기한/HUD 피해 잔상/B2 피 이펙트/이동·공격·스킬·CC와 다른 3종의 처리는 유지. AnimBP와 B2 에셋 5개 해시 불변.
- 기존 directional_cc_qa.py에 재피격 그룹과 변경된 기대값을 반영. 실제 PIE 30/60fps 기능 검사 118개 통과: 재생 중 뒤·옆 방향 재반응, 보호 기한/HUD 보존, 기절 중 억제·복귀, 사망/리스폰, 이동/공격/스킬, 다른 3종 동작 보존.
- 탑 기본 몬스터 8마리의 실제 공격으로 포위 검증. 피해 주입/몬스터 배치 변경 없음. 30fps 촬영 8초/240프레임에서 보호 중 재반응 15회 관찰. HP70 유지 중 재생값 .30→다음 프레임 .03과 새 몸 반응을 직접 확인. 재확인은 최대 8마리 근접/재반응18회/8검사 통과. 카운테스는 정지 상태이며 일반 피격에 입력 잠금 없음.
- 최초 촬영의 마지막 검사만 실패: 보호 타격이 직전 피해보다 .05초 이상 뒤일 것이라는 가정이 실제 .033초 타격과 맞지 않았다. 실패 보고서를 보존하고 피해 나이>반응 나이+.005로 고친 뒤, 촬영 없이 실제 포위 관찰을 재실행해 통과했다. 게임 코드는 추가 변경하지 않았다.
- DevelopmentEditor72.21초/DebugGameEditor403.56초 성공. 실제 화면 검증은 DevelopmentEditor이며 Play-CurrentSkills.cmd용 DebugGame도 갱신. 이번 1번 시범 변경은 Development Game 재빌드·패키징/cook/commit/push 없음. 기존 단독 Game 실행 파일을 최신이라고 안내하지 말 것.
- 결과 Saved/QA/TrialTower/countess-repeat-fix-20261030/review.json, countess-surrounded.webp, protected-contact-proof.png, source.diff. 이전 잘못된 대기 자세 제안은 countess-repeat-diagnosis-20261030/diagnosis.json에 정정. 캡처/실패 근거 보존, 에디터 종료0/배속·FPS·백그라운드 제한 복원. 전체 캐릭터 확대와 미적 최종 채택은 아직 하지 않았다.