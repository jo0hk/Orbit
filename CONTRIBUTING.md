# 🤝 Contributing to Orbit

Orbit 프로젝트에 기여해주셔서 감사합니다! 아래 가이드를 참고해주세요.

## 브랜치 전략

| 브랜치 | 역할 |
| --- | --- |
| `main` | 배포/시연 가능한 안정 버전. 직접 푸시 불가 (보호 규칙) |
| `develop` | 통합 개발 브랜치. **기본 브랜치이며 모든 PR의 대상** |
| `feature/ai-pm` | AI/PM 파트 작업 |
| `feature/app` | 앱 파트 작업 |
| `feature/backend` | 백엔드 파트 작업 |
| `feature/hw` | 하드웨어 파트 작업 |

각자 **자기 파트 브랜치에서 작업**하고 `develop`으로 PR을 냅니다.
머지된 뒤에도 파트 브랜치는 그대로 두고 계속 씁니다.

한 파트 안에서 여러 기능을 동시에 진행하는 등 브랜치를 더 나눠야 할 때는
`feature/파트-기능명` 형식을 씁니다 (예: `feature/app-quest-ui`).

### 작업 시작 전 develop 맞추기

파트 브랜치가 `develop`보다 뒤처져 있으면 다른 파트의 최신 코드가 없는 상태로
작업하게 됩니다. 작업을 시작하기 전에 맞춰주세요.

```bash
git checkout feature/<내-파트>
git fetch origin
git merge origin/develop
git push origin feature/<내-파트>
```

`rebase`가 아니라 `merge`를 쓰세요. 이미 푸시한 커밋을 `rebase`하면 해시가
바뀌어 다른 사람이 받아둔 이력과 어긋납니다.

### 주의

- `main`과 `develop`에는 **force push를 쓰지 않습니다.** 자기 파트 브랜치에서만
  쓰고, 그때도 `--force` 대신 `--force-with-lease`를 씁니다.
- 이미 머지된 커밋의 메시지를 고치지 마세요. 그 위에 쌓인 모든 커밋의 해시가
  바뀌어 팀원들의 로컬 저장소가 전부 어긋납니다.

## 커밋 메시지 규칙

`타입: 내용` 형식을 권장합니다.

| 타입 | 설명 |
| --- | --- |
| `feat` | 새로운 기능 추가 |
| `fix` | 버그 수정 |
| `docs` | 문서 수정 |
| `design` | UI/디자인 변경 |
| `refactor` | 코드 리팩토링 |
| `test` | 테스트 코드 |
| `chore` | 기타 잡무 (빌드, 설정 등) |

예: `feat: 오빗 1단계 시스템 점검 대화 화면 구현`

## Pull Request

1. 작업 브랜치에서 개발 후 `develop`으로 PR을 생성해주세요.
2. PR 템플릿을 채워주세요.
3. 최소 1명 이상의 리뷰 후 머지합니다.

## 이슈

버그 제보나 기능 제안은 [Issues](../../issues)에 템플릿을 이용해 등록해주세요.
