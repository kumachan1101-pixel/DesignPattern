# skills/cover-design.md — カバー画像デザインルール

## 仕様

| 項目 | 値 |
|:---|:---|
| フォーマット | SVG |
| 幅 × 高さ | 1280 × 670px（16:9） |

---

## テーマ別カラーパレット

| テーマ | 背景色 | アクセント |
|:---|:---|:---|
| 設計・アーキテクチャ | `#1a1a2e`（深紺） | `#4a9eff`（ライトブルー） |
| デザインパターン | `#16213e`（ネイビー） | `#e94560`（コーラルレッド） |
| チーム・コミュニケーション | `#0f3460`（ロイヤルブルー） | `#f5a623`（アンバー） |
| リファクタリング | `#1b2631`（チャコール） | `#2ecc71`（グリーン） |
| 思考・考え方 | `#2c2c54`（パープルグレー） | `#fd79a8`（ピンク） |

**テキストカラー**：タイトル `#ffffff`、サブ `#b0b8c8`、クレジット `#6c7a8d`

---

## SVG 雛形

```xml
<svg xmlns="http://www.w3.org/2000/svg" width="1280" height="670" viewBox="0 0 1280 670">
  <!-- 背景 -->
  <rect width="1280" height="670" fill="#1a1a2e"/>

  <!-- 装飾（半透明の円 1〜2個まで） -->
  <circle cx="100" cy="100" r="200" fill="#4a9eff" opacity="0.10"/>
  <circle cx="1200" cy="580" r="150" fill="#4a9eff" opacity="0.08"/>

  <!-- タイトル（1行の場合） -->
  <text x="640" y="310" text-anchor="middle"
    font-family="'Hiragino Kaku Gothic ProN','Hiragino Sans','BIZ UDPGothic',sans-serif"
    font-size="72" font-weight="700" fill="#ffffff">
    タイトルテキスト
  </text>

  <!-- タイトル（2行の場合は tspan で改行） -->
  <!--
  <text x="640" y="280" text-anchor="middle"
    font-family="'Hiragino Kaku Gothic ProN','Hiragino Sans','BIZ UDPGothic',sans-serif"
    font-size="72" font-weight="700" fill="#ffffff">
    <tspan x="640" dy="0">1行目テキスト</tspan>
    <tspan x="640" dy="90">2行目テキスト</tspan>
  </text>
  -->

  <!-- サブテキスト -->
  <text x="640" y="390" text-anchor="middle"
    font-family="'Hiragino Kaku Gothic ProN','Hiragino Sans','BIZ UDPGothic',sans-serif"
    font-size="36" font-weight="400" fill="#b0b8c8">
    ソフトウェア設計の考え方
  </text>

  <!-- 著者クレジット -->
  <text x="60" y="645"
    font-family="'Hiragino Kaku Gothic ProN','Hiragino Sans','BIZ UDPGothic',sans-serif"
    font-size="24" font-weight="400" fill="#6c7a8d">
    note.com/kumachan1101
  </text>
</svg>
```

---

## ルール

- 装飾図形は1〜2個まで（テキストを邪魔しない配置）
- 写真・アイコンフォント・外部参照は使わない
- タイトルは1行20文字が目安。超える場合は `<tspan>` で2行に分割
- 品質チェック：テキストがはみ出していないか、コントラスト十分か
