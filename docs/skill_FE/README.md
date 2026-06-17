# Frontend Skill Setup

Thư mục này chứa bộ hướng dẫn thiết kế/frontend cho BurgerPrintsAgent UI.

## Files

| File/folder | Mục đích |
|---|---|
| `design.md` | Design mẫu/source of truth của project: token, màu, typography, component rules, accessibility. |
| `SKILL.md` | Wrapper skill riêng cho BurgerPrintsAgent FE. Luôn đọc file này khi làm UI. |
| `taste-skill/` | Repo gốc từ `https://github.com/Leonxlnx/taste-skill`, gồm nhiều Agent Skills frontend. |

## Skill chính nên dùng

Dùng file local:

```text
docs/skill_FE/SKILL.md
```

File này yêu cầu agent đọc:

```text
docs/skill_FE/design.md
docs/skill_FE/taste-skill/skills/taste-skill/SKILL.md
```

## Taste Skill repo đã setup

Repo được đặt tại:

```text
docs/skill_FE/taste-skill
```

Skill gốc quan trọng nhất:

```text
docs/skill_FE/taste-skill/skills/taste-skill/SKILL.md
```

Các skill phụ có thể dùng khi cần:

```text
docs/skill_FE/taste-skill/skills/image-to-code-skill/SKILL.md
docs/skill_FE/taste-skill/skills/redesign-skill/SKILL.md
docs/skill_FE/taste-skill/skills/soft-skill/SKILL.md
docs/skill_FE/taste-skill/skills/minimalist-skill/SKILL.md
```

## Cách dùng khi làm frontend

Khi bắt đầu task FE, prompt nên nói rõ:

```text
Dùng docs/skill_FE/SKILL.md và docs/skill_FE/design.md để implement UI.
```

Nếu làm từ ảnh/design mẫu:

```text
Dùng docs/skill_FE/SKILL.md, sau đó tham khảo image-to-code-skill nếu cần convert ảnh/design sang code.
```

## Lưu ý

- Đây không phải frontend app có `package.json`, nên không có `npm install` trong thư mục này.
- `taste-skill/` là bộ instruction/skill để nâng chất lượng UI, không phải package runtime.
- Khi implement frontend thật, build/test command sẽ phụ thuộc app frontend được tạo sau này.
- Không được bỏ qua token trong `design.md`: BurgerPrints orange, Gilroy font stack, spacing/radius/accessibility rules.
