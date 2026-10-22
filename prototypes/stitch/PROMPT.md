# 给 Google Stitch 的材料

打开 [stitch.withgoogle.com](https://stitch.withgoogle.com)，用 Google 账号登录，新建 Web 项目。先上传本目录的截图，再粘贴下面的提示词。

| 截图 | 是什么 |
|---|---|
| `v08-three.png` | 正常：成都三天，选中第 1 天，只画这一天的线 |
| `v08-seven.png` | 七天：布局不变，其他天的点变淡 |
| `v08-places.png` | 没说天数：只有点，没有线 |
| `v08-empty.png` | 空：还没有城市 |
| `v08-fail.png` | 失败：这一句没查到，成都行程不变 |
| `v010-weather.png` | 只问天气：不出地图，只给答案 |

截图都是示意，Stitch 只改外观，不改结构。生成后把各状态的截图或导出的 HTML 发回来。

## 提示词（直接复制）

```text
Redesign this travel planning web app. Keep the structure from the screenshots exactly; only improve visual design.

Language: all UI text in Simplified Chinese.

Layout (desktop 1366 wide):
- Left column about 58% width: the detailed itinerary text. This is the primary content.
- Right column about 42% width: a street-level electronic map (like Amap / Google Maps light style). The map supports the text; it must not dominate.
- A single input bar at the bottom for follow-up edits ("改成七天", "换成丽江").
- A small "开发者" link in the header; no sidebar of logs.
- On narrow screens (390 wide): text first, map below with reduced height.

Itinerary text must be detailed, grouped as: Day -> time slot (上午/下午/晚上) -> place name -> what to do, how to get there (walk / metro / taxi with minutes), and a short tip. Example for Day 1 in Chengdu: 上午 熊猫基地, 看熊猫，建议 8 点前到；地铁 3 号线到熊猫大道站，步行 10 分钟。下午 宽窄巷子 ...

Map rules (do not change):
- Every place of the whole trip is a marker on the map.
- Only the selected day's route is drawn as a line, in order. Other days' markers are faded.
- Day tabs "第 1 天 ... 第 N 天" switch the selected day; 7 days must fit without changing layout.
- Clicking a marker highlights the matching row in the text.
- If the user has not given a number of days, show markers only, no route line.

States to design (one screen each):
1. Normal: 成都 3 days, day 1 selected.
2. Seven days: same layout, 7 day tabs.
3. No days given: markers only.
4. Empty: no city yet, friendly prompt with 3 suggested cities.
5. Failed lookup: the last question "丽江今天天气" failed; show a clear but calm inline notice "这次没查到", keep the Chengdu itinerary and map unchanged.
6. Weather-only question: no map; just a compact weather answer card, and a one-line reminder of the current trip.

Visual direction: bright, daytime, travel feeling; clean and modern; generous whitespace; readable Chinese typography; one accent color plus distinct but soft day colors. Avoid: dark brown or parchment (it looked like a legal system), cartoon footprints, Harry Potter Marauder's Map style, heavy gradients, admin-dashboard cards.
```

## 生成之后

- 每个状态一张图，或者导出 HTML。
- 如果 Stitch 把地图放大到压过文字、把线画成全部天数、或失败时清空了行程，不用改，发回来时说一声，我按上面的规则改回来。
