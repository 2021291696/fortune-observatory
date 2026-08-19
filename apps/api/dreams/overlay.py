from ai_explainer import AiFact


def overlay_facts(
    *,
    day_pillar: str,
    decadal_name: str,
    decadal_range: tuple[int, int],
    yearly_pillar: str,
) -> list[AiFact]:
    return [
        AiFact(id="dream-day", text=f"当日流日为{day_pillar}"),
        AiFact(id="dream-limit", text=f"当前大限行{decadal_name}宫（{decadal_range[0]}-{decadal_range[1]}岁）"),
        AiFact(id="dream-year", text=f"当前流年柱为{yearly_pillar}"),
    ]
