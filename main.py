
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
    df = pd.read_csv(CSV_URL, encoding="utf-8", dtype=str)

    df = df[["날짜", "식사", "메뉴"]].dropna(subset=["메뉴"])

    # 괄호 및 괄호 안의 내용 제거
    def clean_menu(name):
        name = str(name).strip()

        # 중첩 괄호도 제거될 때까지 반복
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

        # 빈 메뉴 제외
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

    # 같은 날 등장한 메뉴 쌍의 횟수
    pair_count = Counter()

    for basket in baskets:
        item_count.update(basket)

        # 하루 식단에서 메뉴 쌍 추출
        for a, b in combinations(sorted(basket), 2):
            pair_count[(a, b)] += 1

    total_pairs = len(pair_count)

    rules = []

    for (a, b), count in pair_count.items():

        support = count / total_days

        # A -> B
        confidence_ab = count / item_count[a]
        lift_ab = confidence_ab / (item_count[b] / total_days)

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
        lift_ba = confidence_ba / (item_count[a] / total_days)

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

    return rules_df, menus, total_days, len(menus), total_pairs


# --------------------------------------------------
# 데이터 분석 실행
# --------------------------------------------------
try:
    df, baskets = load_data()

    rules_df, menus, total_days, menu_count, pair_total = (
        analyze(baskets)
    )

except Exception as e:
    st.error(f"데이터를 불러오는 중 오류가 발생했습니다: {e}")
    st.stop()


# --------------------------------------------------
# 요약 정보
# --------------------------------------------------
st.subheader("📊 분석 요약")

col1, col2, col3 = st.columns(3)

col1.metric("급식 일수", f"{total_days:,}일")
col2.metric("메뉴 종류 수", f"{menu_count:,}개")
col3.metric("함께 나온 메뉴 쌍", f"{pair_total:,}쌍")

st.divider()


# --------------------------------------------------
# 검색 및 정렬 설정
# --------------------------------------------------
st.subheader("🔎 연관규칙 검색")

col1, col2 = st.columns([2, 1])

with col1:
    selected_menu = st.selectbox(
        "메뉴 선택",
        options=["전체 메뉴"] + menus,
        index=0
    )

with col2:
    sort_option = st.selectbox(
        "정렬 기준",
        options=["향상도 순", "신뢰도 순", "동시 순"],
        index=0
    )


# --------------------------------------------------
# 메뉴 필터링
# --------------------------------------------------
filtered_df = rules_df.copy()

if selected_menu != "전체 메뉴":
    filtered_df = filtered_df[
        (filtered_df["조건"] == selected_menu)
        | (filtered_df["결과"] == selected_menu)
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

st.caption(
    f"검색 결과: {len(filtered_df):,}개 규칙 "
    f"({len(filtered_df) // 2:,}개 메뉴 쌍에 해당하는 규칙)"
    if selected_menu == "전체 메뉴"
    else f"'{selected_menu}'이 포함된 규칙: {len(filtered_df):,}개"
)

if filtered_df.empty:
    st.info("조건에 해당하는 연관규칙이 없습니다.")

else:
    display_df = filtered_df.copy()

    # 화면 표시 형식
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
            ["조건", "결과", "동시", "지지도", "신뢰도", "향상도"]
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

    # 그래프는 가장 큰 값이 위쪽에 위치하도록 정렬
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
        margin=dict(l=20, r=80, t=60, b=40)
    )

    st.plotly_chart(
        fig,
        use_container_width=True
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

    - 향상도 > 1 : 함께 등장하는 경향이 양의 관계
    - 향상도 = 1 : 서로 독립적인 관계
    - 향상도 < 1 : 함께 등장하는 경향이 음의 관계

    **참고:** 한 쌍의 두 방향 규칙은 지지도와 동시 횟수는 같지만,
    신뢰도와 향상도는 서로 다를 수 있습니다.
    """)
