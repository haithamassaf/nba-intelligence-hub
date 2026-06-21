"""Plotly chart helpers (radar, grouped bars, cap-space bars)."""

import plotly.graph_objects as go

_RED = "#e45756"
_BLUE = "#4c78a8"
_TRANSPARENT = "rgba(0,0,0,0)"


def _f(v):
    try:
        return float(v)
    except (TypeError, ValueError):
        return 0.0


def radar(name1: str, name2: str, axes: list[tuple[str, object, object]]):
    """axes: (label, v1, v2), higher is better. Each axis is normalized to the
    larger of the two players, so the chart reads as relative strength."""
    labels = [a[0] for a in axes]
    n1, n2 = [], []
    for _, a, b in axes:
        a, b = _f(a), _f(b)
        m = max(a, b)
        n1.append(a / m * 100 if m > 0 else 0)
        n2.append(b / m * 100 if m > 0 else 0)
    fig = go.Figure()
    fig.add_trace(go.Scatterpolar(r=n1 + [n1[0]], theta=labels + [labels[0]], fill="toself", name=name1, line_color=_RED))
    fig.add_trace(go.Scatterpolar(r=n2 + [n2[0]], theta=labels + [labels[0]], fill="toself", name=name2, line_color=_BLUE))
    fig.update_layout(
        polar=dict(radialaxis=dict(visible=True, showticklabels=False, range=[0, 100])),
        showlegend=True, height=400, margin=dict(l=40, r=40, t=30, b=30),
        paper_bgcolor=_TRANSPARENT, legend=dict(orientation="h", y=-0.1),
    )
    return fig


def grouped_bars(name1: str, name2: str, items: list[tuple[str, object, object]]):
    labels = [i[0] for i in items]
    fig = go.Figure()
    fig.add_trace(go.Bar(x=labels, y=[_f(i[1]) for i in items], name=name1, marker_color=_RED))
    fig.add_trace(go.Bar(x=labels, y=[_f(i[2]) for i in items], name=name2, marker_color=_BLUE))
    fig.update_layout(
        barmode="group", height=380, margin=dict(l=20, r=20, t=30, b=60),
        paper_bgcolor=_TRANSPARENT, plot_bgcolor=_TRANSPARENT,
        legend=dict(orientation="h", y=-0.2),
    )
    return fig


def cap_space_chart(teams: list[tuple[str, object, object]]):
    """teams: (name, space_before, space_after)."""
    names = [t[0] for t in teams]
    fig = go.Figure()
    fig.add_trace(go.Bar(x=names, y=[_f(t[1]) for t in teams], name="Before", marker_color="#9aa0a6"))
    fig.add_trace(go.Bar(x=names, y=[_f(t[2]) for t in teams], name="After", marker_color="#54a24b"))
    fig.update_layout(
        barmode="group", height=320, margin=dict(l=20, r=20, t=30, b=30),
        paper_bgcolor=_TRANSPARENT, plot_bgcolor=_TRANSPARENT,
        yaxis_title="Cap space ($M)", legend=dict(orientation="h", y=-0.2),
    )
    return fig
