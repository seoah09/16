
import re
from itertools import combinations
from collections import Counter

import pandas as pd
import streamlit as st
import plotly.express as px


# --------------------------------------------------
# 기본 설정
# --------------------------------------------------
st.set_page_config(
    page_title="급식 규칙 찾기",
    page_icon="🍱",
    layout="wide"
)

st.title("🍱 급식 규칙 찾기")
st.caption("송탄고 중식 메뉴 연관규칙 분석")

CSV_URL = (
    "https://raw.githubusercontent.com/it-teacher-go/"
    "data-share-/main/songtan_meals_184.csv"
)


# --------------------------------------------------
# 데이터 불러오기 및 전처리
# --------------------------------------------------
@st.cache_data
def load_data():
    df = pd.read_csv(
        CSV_URL,
        encoding="utf-8",
        dtype=str
    )

    df = df[["날짜", "식사", "메뉴"]].dropna(
        subset=["메뉴"]
    )

    def clean_menu(name):
        name = str(name).strip()

        # 괄호 및 괄호 안의 내용 제거
        while True:
            cleaned = re.sub(
                r"\([^()]*\)|（[^（）]*）",
                "",
                name
            )

            if cleaned == name:
                break

            name = cleaned

        return name.strip()

    baskets = []

    for menu_string in df["메뉴"]:
        menus = {
            clean_menu(menu)
            for menu in menu_string.split("|")
            if clean_menu(menu)
        }

        menus.discard("")
        baskets.append(menus)

    return df, baskets


# --------------------------------------------------
# 연관규칙 분석
# --------------------------------------------------
@st.cache_data
def analyze(baskets):

    total_days = len(baskets)

    # 메뉴별 등장 횟수
    item_count = Counter()

    # 메뉴 쌍별 동시 등장 횟수
    pair_count = Counter()

    for basket in baskets:

        item_count.update(basket)

        for a, b in combinations(sorted(basket), 2):
            pair_count[(a, b)] += 1

    total_pairs = len(pair_count)

    rules = []

    for (a, b), count in pair_count.items():

        support = count / total_days

        # A -> B
        confidence_ab = count / item_count[a]
        lift_ab = confidence_ab / (
            item_count[b] / total_days
        )

        rules.append({
            "조건": a,
            "결과": b,
            "동시": count,
            "지지도": support,
            "신뢰도": confidence_ab,
            "향상도": lift_ab
        })

        # B -> A
        confidence_ba = count / item_count[b]
        lift_ba = confidence_ba / (
            item_count[a] / total_days
        )

        rules.append({
            "조건": b,
            "결과": a,
            "동시": count,
            "지지도": support,
            "신뢰도": confidence_ba,
            "향상도": lift_ba
        })

    rules_df = pd.DataFrame(rules)

    menus = sorted(item_count.keys())

    return (
        rules_df,
        menus,
        total_days,
        len(menus),
        total_pairs,
        item_count,
        pair_count
    )


# --------------------------------------------------
# 데이터 분석 실행
# --------------------------------------------------
try:

    (
        rules_df,
        menus,
        total_days,
        menu_count,
        pair_total,
        item_count,
        pair_count
    ) = analyze(load_data()[1])

except Exception as e:

    st.error(
        f"데이터를 불러오는 중 오류가 발생했습니다: {e}"
    )

    st.stop()


# --------------------------------------------------
# 요약 정보
# --------------------------------------------------
st.subheader("📊 분석 요약")

col1, col2, col3 = st.columns(3)

col1.metric(
    "급식 일수",
    f"{total_days:,}일"
)

col2.metric(
    "메뉴 종류 수",
    f"{menu_count:,}개"
)

col3.metric(
    "함께 나온 메뉴 쌍",
    f"{pair_total:,}쌍"
)

st.divider()


# --------------------------------------------------
# 검색 및 정렬 설정
# --------------------------------------------------
st.subheader("🔎 연관규칙 검색")

col1, col2 = st.columns([2, 1])

with col1:

    selected_menu = st.selectbox(
        "좁혀 보기 (연관규칙 메뉴 선택)",
        options=["전체 메뉴"] + menus,
        index=0
    )

with col2:

    sort_option = st.selectbox(
        "정렬 기준",
        options=[
            "향상도 순",
            "신뢰도 순",
            "동시 순"
        ],
        index=0
    )


# --------------------------------------------------
# 최소 동시 일수 슬라이더
# --------------------------------------------------
min_count = st.slider(
    "최소 동시 일수",
    min_value=1,
    max_value=10,
    value=1,
    step=1,
    help="선택한 일수 이상 함께 나온 메뉴 규칙만 표시합니다."
)


# --------------------------------------------------
# 메뉴 필터링
# --------------------------------------------------
filtered_df = rules_df.copy()

# 선택한 메뉴가 조건 또는 결과에 포함된 규칙
if selected_menu != "전체 메뉴":

    filtered_df = filtered_df[
        (filtered_df["조건"] == selected_menu)
        | (filtered_df["결과"] == selected_menu)
    ].copy()


# 최소 동시 일수 적용
filtered_df = filtered_df[
    filtered_df["동시"] >= min_count
].copy()


# --------------------------------------------------
# 정렬
# --------------------------------------------------
sort_columns = {
    "향상도 순": "향상도",
    "신뢰도 순": "신뢰도",
    "동시 순": "동시"
}

sort_column = sort_columns[sort_option]

filtered_df = filtered_df.sort_values(
    by=[sort_column, "신뢰도", "동시"],
    ascending=[False, False, False]
).reset_index(drop=True)


# --------------------------------------------------
# 연관규칙 표
# --------------------------------------------------
st.subheader("📋 연관규칙 목록")

st.write(
    f"현재 조건에 해당하는 규칙: **{len(filtered_df):,}개**"
)

if selected_menu == "전체 메뉴":

    st.caption(
        f"최소 동시 일수 {min_count}일 이상인 규칙"
    )

else:

    st.caption(
        f"'{selected_menu}'이 포함되고 "
        f"최소 {min_count}일 이상 함께 나온 규칙"
    )


if filtered_df.empty:

    st.info("조건에 해당하는 연관규칙이 없습니다.")

else:

    display_df = filtered_df.copy()

    display_df["지지도"] = display_df["지지도"].map(
        lambda x: f"{x:.2%}"
    )

    display_df["신뢰도"] = display_df["신뢰도"].map(
        lambda x: f"{x:.2%}"
    )

    display_df["향상도"] = display_df["향상도"].map(
        lambda x: f"{x:.3f}"
    )

    display_df["동시"] = display_df["동시"].astype(int)

    st.dataframe(
        display_df[
            [
                "조건",
                "결과",
                "동시",
                "지지도",
                "신뢰도",
                "향상도"
            ]
        ],
        use_container_width=True,
        hide_index=True,
        height=500
    )


# --------------------------------------------------
# 향상도 상위 10개 그래프
# --------------------------------------------------
st.divider()

st.subheader("📈 향상도 상위 10개 규칙")

if filtered_df.empty:

    st.info("그래프로 표시할 데이터가 없습니다.")

else:

    top10 = (
        filtered_df
        .sort_values(
            by=["향상도", "신뢰도", "동시"],
            ascending=[False, False, False]
        )
        .head(10)
        .copy()
    )

    chart_df = top10.sort_values(
        "향상도",
        ascending=True
    ).copy()

    chart_df["규칙"] = (
        chart_df["조건"] + " → " + chart_df["결과"]
    )

    fig = px.bar(
        chart_df,
        x="향상도",
        y="규칙",
        orientation="h",
        text="향상도",
        labels={
            "향상도": "향상도 (Lift)",
            "규칙": "연관규칙"
        },
        title="향상도 상위 10개 메뉴 연관규칙"
    )

    fig.update_traces(
        texttemplate="%{x:.3f}",
        textposition="outside",
        marker_color="#4C78A8",
        cliponaxis=False
    )

    fig.update_layout(
        height=500,
        xaxis_title="향상도",
        yaxis_title="메뉴 규칙",
        showlegend=False,
        margin=dict(
            l=20,
            r=80,
            t=60,
            b=40
        )
    )

    st.plotly_chart(
        fig,
        use_container_width=True
    )


# --------------------------------------------------
# 함께 나온 적 없는 짝
# --------------------------------------------------
st.divider()

st.subheader("🚫 함께 나온 적 없는 짝")

st.write(
    "선택한 메뉴와 한 번도 같은 날 나오지 않았지만, "
    "혼자서는 10일 이상 등장한 메뉴를 찾습니다."
)

# 연관규칙 검색과 별개의 메뉴 선택
selected_menu_for_absence = st.selectbox(
    "함께 나온 적 없는 짝을 찾을 메뉴",
    options=menus,
    key="absence_menu"
)

if selected_menu_for_absence:

    # 선택 메뉴가 등장한 날짜 수
    selected_count = item_count[selected_menu_for_absence]

    # 선택 메뉴와 한 번도 함께 나온 적 없는 메뉴 찾기
    never_together = []

    for other_menu in menus:

        # 자기 자신은 제외
        if other_menu == selected_menu_for_absence:
            continue

        # 두 메뉴가 함께 나온 적이 없는 경우
        pair = tuple(
            sorted([
                selected_menu_for_absence,
                other_menu
            ])
        )

        together_count = pair_count.get(pair, 0)

        # 혼자서 10일 이상 등장한 메뉴만 포함
        other_count = item_count[other_menu]

        if together_count == 0 and other_count >= 10:

            never_together.append({
                "메뉴": other_menu,
                "등장 일수": other_count,
                "선택 메뉴와 동시 등장": together_count
            })

    # 등장 일수 많은 순으로 정렬
    absent_df = pd.DataFrame(never_together)

    st.info(
        f"선택 메뉴 '{selected_menu_for_absence}'의 등장 일수: "
        f"**{selected_count:,}일**"
    )

    if absent_df.empty:

        st.warning(
            "조건에 해당하는 메뉴가 없습니다."
        )

    else:

        absent_df = absent_df.sort_values(
            by=["등장 일수", "메뉴"],
            ascending=[False, True]
        ).reset_index(drop=True)

        st.write(
            f"함께 나온 적 없는 메뉴: "
            f"**{len(absent_df):,}개**"
        )

        st.dataframe(
            absent_df[
                [
                    "메뉴",
                    "등장 일수",
                    "선택 메뉴와 동시 등장"
                ]
            ],
            use_container_width=True,
            hide_index=True
        )


# --------------------------------------------------
# 분석 방법 안내
# --------------------------------------------------
with st.expander("📖 분석 지표 설명"):

    st.markdown("""
    **1. 동시**

    두 메뉴가 같은 날 함께 등장한 횟수입니다.

    **2. 지지도 (Support)**

    전체 급식 일수 중 두 메뉴가 함께 나온 날의 비율입니다.

    `동시 등장 횟수 / 전체 급식 일수`

    **3. 신뢰도 (Confidence)**

    조건 메뉴가 나온 날 중 결과 메뉴도 함께 나온 비율입니다.

    `두 메뉴 동시 등장 횟수 / 조건 메뉴 등장 횟수`

    **4. 향상도 (Lift)**

    두 메뉴의 동시 등장 관계가 독립적이라고 가정했을 때보다
    얼마나 더 자주 함께 등장하는지 나타냅니다.

    `신뢰도 / 결과 메뉴의 등장 비율`

    - 향상도 > 1 : 양의 연관 관계
    - 향상도 = 1 : 독립적인 관계
    - 향상도 < 1 : 음의 연관 관계

    **5. 함께 나온 적 없는 짝**

    선택한 메뉴와 동시 등장 횟수가 0회인 메뉴 중
    개별 등장 횟수가 10일 이상인 메뉴를 보여 줍니다.

    등장 일수가 많은 순으로 정렬합니다.

    **참고:** 한 쌍의 두 방향 규칙은 지지도와 동시 횟수는 같지만,
    신뢰도와 향상도는 서로 다를 수 있습니다.
    """)
