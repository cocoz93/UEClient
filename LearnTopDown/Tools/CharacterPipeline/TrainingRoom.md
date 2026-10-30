# 어두운 수련장

맵: `/Game/TopDown/TrainingRoom/Maps/Lvl_DarkTrainingRoom`

Medieval Dungeon의 석재 바닥·벽·기둥·아치·촛대·석상을 사용한 24m × 24m 공간이다. 중앙은 전투 공간으로 비우고 주변 조명과 건축물로 공간을 구분한다. 숫자 **1=암살자, 2=궁수**, 우클릭 이동, 좌클릭 평타, Q/W/E/R은 기존 컨트롤러와 캐릭터 구현을 사용한다. 궁수 E는 기존 패시브다. 세 석상 표적은 기존 피해·상태·체력 복구 기능을 사용한다.

## 보존과 영향 범위

- 기존 `/Game/TopDown/Lvl_TopDown`, 캐릭터 BP·애니메이션·모션·스킬·카메라 및 원본 Medieval Dungeon 팩은 수정하지 않는다.
- 새 콘텐츠는 `Content/TopDown/TrainingRoom`과 해당 맵의 `__ExternalActors__`, `__ExternalObjects__` 경로에 저장한다.
- 바닥은 원본 Albedo/Normal 텍스처를 사용하는 프로젝트 소유 재질을 사용한다. 원본 바닥의 파라락스 깊이 표현과 받침 슬래브의 깊이 충돌을 피한다. 원본 재질은 저장하지 않는다.
- 모듈 틈 아래의 연속 슬래브가 충돌을 제공한다. 금속 인레이와 장식물은 충돌을 끄고, 외벽·기둥에는 충돌을 유지한다.
- 기존 맵을 처음 복제할 때 World Partition 관리 액터와 NavMesh 브러시를 유지한다. 재생성 시에는 새 맵 자체를 로드해 이전 외부 액터를 정리한다.
- 카메라는 승인된 거리 2000cm, FOV 55를 유지한다. 조명·노출·재질은 새 맵에서만 설정한다.
- 수련장 환경에 쓰는 4K 텍스처는 프로젝트 소유 사본의 최대 크기를 2K로 제한한다. 원본 텍스처와 두 캐릭터의 텍스처 품질은 유지한다. 새 머티리얼 인스턴스에서 사본을 참조하며 비디오 메모리 경고가 있는 캡처는 시각 승인에서 제외한다.
- 사운드 설정과 스킬 효과 내용은 기존 설정을 유지한다. 배경 작업에 스킬트리 편집·새 스킬 제작은 포함하지 않는다.

## 재현

프로젝트 폴더에서 번들 Python으로 실행한다. 모든 오프스크린 에디터는 기존 `render_lock.py`를 공유한다. 사용자의 에디터 프로세스를 종료하거나 OS 입력을 점유하지 않는다.

```powershell
# 원본 409개 패키지와 데모 맵의 로드 및 메시 참조 조사
& $python Tools/CharacterPipeline/editor_task.py Tools/CharacterPipeline/training_room_inspect.py --output Saved/QA/CharacterPipeline/<run>/inspect

# 새 맵 생성/재생성. 정해진 기준선이 먼저 있어야 한다.
& $python Tools/CharacterPipeline/editor_task.py Tools/CharacterPipeline/training_room_build.py --output Saved/QA/CharacterPipeline/<run>/build

# 실제 새 맵 PIE에서 전환·이동·평타·스킬·회복·소유자 정리 검사
& $python Tools/CharacterPipeline/training_room_run.py --fps 30 --output Saved/QA/CharacterPipeline/<run>/verify-30
& $python Tools/CharacterPipeline/training_room_run.py --fps 60 --output Saved/QA/CharacterPipeline/<run>/verify-60
```

`$python`은 `C:/Users/USER/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/python.exe`다. 출력 폴더는 새 경로를 사용한다. `training_room_run.py`는 엔진 종료 코드뿐 아니라 실제 검사 JSON의 성공 여부도 확인한다.

사용자의 에디터와 동시에 실행하는 추가 검증 프로세스에는 512MB 텍스처 스트리밍 캐시와 1024페이지 가상 그림자 캐시를 적용한다. 이 제한은 해당 QA 프로세스에만 적용하며 프로젝트 설정이나 원본 캐릭터 에셋에 저장하지 않는다. 그림자 해상도 설정은 유지하고 캐시 용량만 제한한다. 실제 화면의 메모리 경고 유무와 재질 선명도는 별도로 확인한다.

## 완료 기준

두 FPS는 고정 시뮬레이션 검사이며 GPU 성능 보장 수치가 아니다. OS 물리 입력 대신 실제 컨트롤러 바인딩으로 PIE를 조작한다. 양 캐릭터의 모든 슬롯과 평타의 실제 피해, 궁수 E 패시브, R 강화 사격, 이동 목표·바닥 충돌·숫자 전환 카메라, 전환 후 이전 스킬 정리를 확인한다. 캐릭터 전체 원래 필드 회귀검사와는 별도 범위다.

스크린샷은 실제 플레이 카메라에서 저장하며 시각 검토와 SHA-256 확인을 별도로 수행한다. 기능 통과만으로 배경·이펙트 가독성을 완료 처리하지 않는다. 기존 콘텐츠 보존과 새 맵/재질/외부 액터 해시, 실행 도구 지문을 결과와 함께 보관한다.
