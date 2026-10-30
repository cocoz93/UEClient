# 캐릭터 병렬 작업 운영

캐릭터 전용 소스·에셋 제작 도구·검사 코드는 서브에이전트가 병렬로 준비한다. 통합 담당이 네이티브 빌드, 에셋 저장 및 실제 수련장 PIE 검증을 순서대로 실행한다. 현재 구조에서는 프로젝트 전체를 한 담당자가 독점할 필요가 없다.

| 담당 | 수정 소유 영역 |
|---|---|
| 암살자 | `Source/LearnTopDown/CountessSkillComponent.*`, `Content/TopDown/Characters/Countess/`, `Content/TopDown/Blueprints/BP_CountessCharacter.uasset`, 전용 생성·검사 스크립트 |
| 궁수 | `Source/LearnTopDown/SparrowCharacter.*`, `SparrowSkillComponent.*`, `SparrowArrow.*`, `Content/TopDown/Characters/Sparrow/`, 전용 생성·검사 스크립트 |
| 통합 | `TopDownCombatCharacter.*`, `CharacterSkillComponent.*`, `KwangPlayerController.*`, 공통 HUD·천 설정, 맵·Config·프로필 기준선, `LearnTopDown.Build.cs`, 빌드·에디터 실행 |

작업 시작 때 수정 가능한 파일 목록을 명시한다. 담당 영역 밖 수정이 필요하면 통합 담당에게 요청한다. 여러 담당이 동일한 `.uasset`, 맵 또는 공통 파일을 저장하지 않는다. 캐릭터마다 다른 `Saved/QA/CharacterPipeline/<작업명>` 경로를 사용한다.

`editor_task.py`의 `render_lock.py`는 프로젝트당 오프스크린 에디터 하나만 허용한다. 이 잠금은 네이티브 소스 편집이나 UBT 빌드를 직렬화하지 않는다. 빌드는 통합 담당 한 명만 실행한다. 사용자 에디터를 강제 종료하지 않고, 별도 모듈 접미사를 사용한다.

현재 `countess_w_result.py`처럼 다른 소스 전체의 무변경을 확인하는 검사는 캐릭터별 단독 작업 기준이다. 이를 사용하는 묶음이 확정되기 전에는 다른 담당이 현재 소스를 수정하지 않고 읽기·설계·별도 새 스크립트 준비를 진행한다. 여러 캐릭터를 실제로 함께 수정할 때는 모든 담당의 시작 기준선과 명시적인 허용 변경 목록을 통합 검사에 반영한다. 검사 예외를 디렉터리 전체로 넓혀 무관한 변경을 숨기지 않는다.

통합 시 숫자 1·2 전환, 카메라, 이동·기본 공격, 해당 스킬의 피해·범위·쿨타임과 중단·소유자 종료 후 FX 정리를 두 캐릭터에서 확인한다. 기능 통과와 실제 화면 검토, 사용자의 미적 승인은 별도로 기록한다.
