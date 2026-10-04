"""progress.py - tasks, daily log, streak, adaptive plan, charts, weekly summary, PDF export."""
import streamlit as st
from matplotlib.figure import Figure

from core import ai, config, stats
from core import database as db
from core.report import build_progress_pdf
from ui.common import current_mood, show_ai_error, today


def _toggle_task(uid: int, task_id: int):
    db.set_task_done(uid, task_id, st.session_state[f"task_{task_id}"])


def _log_today(uid: int, intensity: str):
    points = config.INTENSITY_POINTS.get(intensity, 10)
    if db.log_today(uid, today(), points):
        st.session_state["flash"] = f"Logged! +{points} Aura points."
    else:
        st.session_state["flash"] = "You already logged today. Come back tomorrow!"


def _shrink(user: dict, roadmap: dict, open_tasks, reason: str):
    try:
        with st.spinner("Re-planning..."):
            new_tasks = ai.simplify_tasks([t["description"] for t in open_tasks], reason, user)
        db.replace_open_tasks(user["id"], roadmap["id"], new_tasks)
        st.rerun()
    except ai.AIError as exc:
        show_ai_error(exc)


def _chart(series):
    fig = Figure(figsize=(10, 3.5))
    ax = fig.subplots()
    fig.patch.set_facecolor("#0e1117")
    ax.set_facecolor("#0e1117")
    dates = [row[0] for row in series]
    percent = [row[2] for row in series]
    ax.fill_between(dates, percent, color="#00d4ff", alpha=0.2)
    ax.plot(dates, percent, color="#00d4ff", marker="o", markersize=3)
    ax.set_ylim(0, 105)
    ax.set_ylabel("7-day consistency (%)", color="white")
    ax.tick_params(colors="white")
    for spine in ax.spines.values():
        spine.set_color("#444")
    fig.autofmt_xdate()
    st.pyplot(fig)


def render(user: dict):
    uid, now = user["id"], today()
    st.title("Progress")

    flash = st.session_state.pop("flash", None)
    if flash:
        st.success(flash)
        if flash.startswith("Logged"):
            st.balloons()

    roadmap = db.get_active_roadmap(uid)
    logged = db.logged_days(uid)
    streak = stats.current_streak(logged, now)
    series = stats.daily_series(logged, now, window=30)
    created = user["created_at"].date() if user.get("created_at") else now

    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Consistency (7 days)", f"{series[-1][2]}%")
    m2.metric("Streak (days)", streak)
    m3.metric("Level", stats.aura_level(len(logged)))
    m4.metric("Aura points", user["aura_points"])

    st.subheader("Active tasks")
    if not roadmap:
        st.info("No tasks yet. Build a goal on the Architect page.")
        task_rows = []
    else:
        st.caption(f"Goal: {roadmap['title']}")
        task_rows = db.get_tasks(uid, roadmap["id"])
        open_tasks = [t for t in task_rows if not t["is_done"]]
        missed = stats.days_since_activity(logged, created, now)

        if open_tasks and missed >= config.MISSED_DAYS_TRIGGER:
            st.warning(f"You have not logged progress for {missed} days. Life gets busy. "
                       "Want a lighter plan to restart gently?")
            if st.button("Make my plan lighter"):
                _shrink(user, roadmap, open_tasks, f"learner missed {missed} days")
        elif open_tasks and current_mood() in ("Drained", "Low"):
            st.warning(f"You feel {current_mood()} today. Tiny wins still count.")
            if st.button("Simplify my tasks into 5-minute wins"):
                _shrink(user, roadmap, open_tasks, f"learner feels {current_mood()} today")

        for task in task_rows:
            st.checkbox(task["description"], value=bool(task["is_done"]), key=f"task_{task['id']}",
                        on_change=_toggle_task, args=(uid, task["id"]))
        if not task_rows:
            st.info("This goal has no tasks.")

    st.divider()
    already = now in set(logged)
    st.button("Log today's success" if not already else "Today is logged",
              disabled=already, on_click=_log_today, args=(uid, user["intensity"]))

    st.divider()
    st.subheader("Performance analytics (last 30 days)")
    _chart(series)

    st.subheader("Weekly AI review")
    if st.button("Write my weekly review"):
        done = sum(1 for t in task_rows if t["is_done"])
        try:
            with st.spinner("Writing..."):
                st.session_state["weekly_summary"] = ai.weekly_summary(
                    db.weekly_stats(uid, now), roadmap["title"] if roadmap else "none",
                    done, len(task_rows), streak, user)
        except ai.AIError as exc:
            show_ai_error(exc)
    if st.session_state.get("weekly_summary"):
        st.markdown(st.session_state["weekly_summary"])

    st.subheader("Export")
    pdf = build_progress_pdf(user["nickname"] or user["username"], roadmap["title"] if roadmap else "",
                             user["level"], user["aura_points"], streak, task_rows, series, now)
    st.download_button("Download progress report (PDF)", data=pdf,
                       file_name="aura_progress_report.pdf", mime="application/pdf")
