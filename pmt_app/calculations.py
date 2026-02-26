import database
import pandas as pd
import streamlit as st
import logging
from datetime import datetime, timedelta

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@st.cache_data(ttl=600)
def get_project_metrics(project_id):
    """
    Calculates all metrics for a single project using an optimized single-query approach where possible.
    """
    try:
        # Optimized query to get counts and sums in ONE go
        summary_query = '''
            SELECT 
                p.*,
                (SELECT SUM(amount) FROM expenditure_log WHERE project_id = p.project_id) as total_spent,
                (SELECT SUM(budgeted_cost) FROM baseline_schedule WHERE project_id = p.project_id) as total_planned,
                (SELECT SUM(budgeted_cost) FROM baseline_schedule WHERE project_id = p.project_id AND status = 'Complete') as completed_budget,
                (SELECT COUNT(*) FROM baseline_schedule WHERE project_id = p.project_id) as total_activities,
                (SELECT COUNT(*) FROM baseline_schedule WHERE project_id = p.project_id AND status = 'Complete') as completed_activities,
                (SELECT COUNT(*) FROM baseline_schedule WHERE project_id = p.project_id AND status = 'Active') as active_activities,
                (SELECT COUNT(*) FROM baseline_schedule WHERE project_id = p.project_id AND status != 'Complete' AND planned_finish < CURRENT_DATE) as overdue_activities
            FROM projects p
            WHERE p.project_id = %s
        '''
        project_df = database.get_df(summary_query, (project_id,))
        if project_df is None or project_df.empty:
            return None

        project = project_df.iloc[0]
        
        total_budget = float(project["total_budget"]) if pd.notna(project["total_budget"]) else 0.0
        total_spent = float(project["total_spent"]) if pd.notna(project["total_spent"]) else 0.0
        total_planned = float(project["total_planned"]) if pd.notna(project["total_planned"]) else 0.0
        completed_budget = float(project["completed_budget"]) if pd.notna(project["completed_budget"]) else 0.0
        
        remaining = total_budget - total_spent
        pct_complete = (completed_budget / total_planned * 100) if total_planned > 0 else 0.0
        earned_value = completed_budget
        
        forecast = total_spent + (total_budget - earned_value)
        cpi = (earned_value / total_spent) if total_spent > 0 else 1.0
        
        budget_health = "Green"
        if forecast > total_budget * 1.05 and total_budget > 0:
            budget_health = "Red"
        elif forecast > total_budget and total_budget > 0:
            budget_health = "Yellow"
        
        schedule_health = "Green" if project['overdue_activities'] == 0 else "Red"
        
        budget_used_pct = (total_spent / total_budget * 100) if total_budget > 0 else 0.0

        return {
            "project_id": project_id,
            "project_name": str(project["project_name"]),
            "project_number": str(project["project_number"]),
            "total_budget": total_budget,
            "total_spent": total_spent,
            "remaining": remaining,
            "pct_complete": min(pct_complete, 100.0),
            "budget_used_pct": budget_used_pct,
            "forecast": forecast,
            "budget_health": budget_health,
            "schedule_health": schedule_health,
            "actual_status": str(project.get("status", "Planning")),
            "cpi": cpi,
            "total_activities": int(project['total_activities']),
            "completed_activities": int(project['completed_activities']),
            "active_activities": int(project['active_activities']),
            "project_start_date": str(project["start_date"]) if pd.notna(project["start_date"]) else None,
            "project_end_date": str(project["target_end_date"]) if pd.notna(project["target_end_date"]) else None,
            "cost_variance": earned_value - total_spent,
            "variance_at_completion": total_budget - forecast
        }
    except Exception as e:
        logger.error(f"Error calculating metrics for project {project_id}: {e}")
        return None
    except Exception as e:
        logger.error(f"Error calculating metrics for project {project_id}: {e}")
        return None


def get_monthly_spending_trend(project_id):
    """
    Returns monthly spending data for a project.
    """
    try:
        df = database.get_df(
            """
            SELECT TO_CHAR(spend_date, 'YYYY-MM') as month, 
                   SUM(amount) as total_spent
            FROM expenditure_log 
            WHERE project_id = %s
            GROUP BY TO_CHAR(spend_date, 'YYYY-MM')
            ORDER BY month
        """,
            (project_id,),
        )
        return (
            df
            if df is not None and not df.empty
            else pd.DataFrame(columns=["month", "total_spent"])
        )
    except Exception as e:
        logger.error(f"Error getting monthly spending for project {project_id}: {e}")
        return pd.DataFrame(columns=["month", "total_spent"])


def get_category_spending(project_id):
    """
    Returns spending by category for a project.
    """
    try:
        df = database.get_df(
            """
            SELECT category, SUM(amount) as total
            FROM expenditure_log 
            WHERE project_id = %s
            GROUP BY category
            ORDER BY total DESC
        """,
            (project_id,),
        )
        return (
            df
            if df is not None and not df.empty
            else pd.DataFrame(columns=["category", "total"])
        )
    except Exception as e:
        logger.error(f"Error getting category spending for project {project_id}: {e}")
        return pd.DataFrame(columns=["category", "total"])


@st.cache_data(ttl=600)
def get_portfolio_metrics(pm_id=None, user_id=None):
    """
    Fetches all projects and their associated metrics in a single, optimized query.
    This is the fastest way to load the Executive Dashboard.
    """
    try:
        # One giant query to get everything for everyone
        # Removed PG-specific casting for SQLite compatibility
        query = '''
            WITH project_list AS (
                SELECT p.* 
                FROM projects p
                WHERE (%s IS NULL OR p.pm_user_id = %s)
                   OR (%s IS NULL OR EXISTS (SELECT 1 FROM project_assignments pa WHERE pa.project_id = p.project_id AND pa.user_id = %s))
                   OR (%s IS NULL OR EXISTS (SELECT 1 FROM baseline_schedule bs WHERE bs.project_id = p.project_id AND bs.responsible_user_id = %s))
            )
            SELECT 
                pl.*,
                COALESCE((SELECT SUM(amount) FROM expenditure_log WHERE project_id = pl.project_id), 0) as total_spent,
                COALESCE((SELECT SUM(budgeted_cost) FROM baseline_schedule WHERE project_id = pl.project_id), 0) as total_planned,
                COALESCE((SELECT SUM(budgeted_cost) FROM baseline_schedule WHERE project_id = pl.project_id AND status = 'Complete'), 0) as completed_budget,
                (SELECT COUNT(*) FROM baseline_schedule WHERE project_id = pl.project_id) as total_activities,
                (SELECT COUNT(*) FROM baseline_schedule WHERE project_id = pl.project_id AND status = 'Complete') as completed_activities,
                (SELECT COUNT(*) FROM baseline_schedule WHERE project_id = pl.project_id AND status = 'Active') as active_activities,
                (SELECT COUNT(*) FROM baseline_schedule WHERE project_id = pl.project_id AND status != 'Complete' AND planned_finish < CURRENT_DATE) as overdue_activities
            FROM project_list pl
        '''
        df = database.get_df(query, (pm_id, pm_id, user_id, user_id, user_id, user_id))
        
        if df.empty:
            return []

        results = []
        for _, project in df.iterrows():
            total_budget = float(project["total_budget"]) if pd.notna(project["total_budget"]) else 0.0
            total_spent = float(project["total_spent"]) if pd.notna(project["total_spent"]) else 0.0
            total_planned = float(project["total_planned"]) if pd.notna(project["total_planned"]) else 0.0
            completed_budget = float(project["completed_budget"]) if pd.notna(project["completed_budget"]) else 0.0
            
            pct_complete = (completed_budget / total_planned * 100) if total_planned > 0 else 0.0
            forecast = total_spent + (total_budget - completed_budget)
            
            budget_health = "Green"
            if forecast > total_budget * 1.05 and total_budget > 0:
                budget_health = "Red"
            elif forecast > total_budget and total_budget > 0:
                budget_health = "Yellow"

            results.append({
                "project_id": project["project_id"],
                "project_name": str(project["project_name"]),
                "project_number": str(project["project_number"]),
                "client": project.get("client", "N/A"),
                "total_budget": total_budget,
                "total_spent": total_spent,
                "pct_complete": min(pct_complete, 100.0),
                "budget_used_pct": (total_spent / total_budget * 100) if total_budget > 0 else 0.0,
                "budget_health": budget_health,
                "schedule_health": "Green" if project['overdue_activities'] == 0 else "Red"
            })
        return results
    except Exception as e:
        logger.error(f"Error in get_portfolio_metrics: {e}")
        return []

@st.cache_data(ttl=600)
def get_all_projects_summary():
    """
    Returns a summary dataframe for all projects.
    """
    try:
        projects = database.get_projects()
        if projects is None or projects.empty:
            return pd.DataFrame()

        summary = []
        for _, p in projects.iterrows():
            metrics = get_project_metrics(p["project_id"])
            if metrics:
                summary.append(metrics)

        return pd.DataFrame(summary)
    except Exception as e:
        logger.error(f"Error generating projects summary: {e}")
        return pd.DataFrame()


@st.cache_data(ttl=600)
def get_burndown_data(project_id):
    """
    Builds three series for a Cost Burndown Chart:
      - ideal:  straight-line remaining budget from start_date to target_end_date
      - actual: cumulative remaining budget based on real expenditure dates
      - forecast: linear projection of actual spending into the future

    Returns a dict with keys:
      'ideal_df'     – pd.DataFrame(columns=['date', 'remaining'])
      'actual_df'    – pd.DataFrame(columns=['date', 'remaining'])
      'forecast_df'  – pd.DataFrame(columns=['date', 'remaining'])   (empty if not enough data)
      'total_budget' – float
      'start_date'   – pd.Timestamp | None
      'end_date'     – pd.Timestamp | None
      'today'        – pd.Timestamp
      'status'       – 'On Track' | 'At Risk' | 'Over Budget' | 'No Data'
    """
    try:
        project_df = database.get_df(
            "SELECT total_budget, start_date, target_end_date FROM projects WHERE project_id = %s",
            (project_id,),
        )
        if project_df is None or project_df.empty:
            return None

        row = project_df.iloc[0]
        total_budget = float(row["total_budget"]) if pd.notna(row["total_budget"]) else 0.0
        start_date = pd.to_datetime(row["start_date"]) if pd.notna(row["start_date"]) else None
        end_date = pd.to_datetime(row["target_end_date"]) if pd.notna(row["target_end_date"]) else None
        today = pd.Timestamp.now().normalize()  # midnight today

        # ── 1. Ideal burndown (perfect straight line) ───────────────────────────
        if start_date and end_date and total_budget > 0:
            duration_days = max((end_date - start_date).days, 1)
            date_range = pd.date_range(start=start_date, end=end_date, freq="D")
            remaining_ideal = [
                total_budget - total_budget * (i / duration_days)
                for i in range(len(date_range))
            ]
            ideal_df = pd.DataFrame({"date": date_range, "remaining": remaining_ideal})
        else:
            ideal_df = pd.DataFrame(columns=["date", "remaining"])

        # ── 2. Actual cumulative spending → remaining budget ────────────────────
        exp_df = database.get_df(
            """
            SELECT spend_date, SUM(amount) as daily_spend
            FROM expenditure_log
            WHERE project_id = %s
            GROUP BY spend_date
            ORDER BY spend_date
            """,
            (project_id,),
        )

        if exp_df is not None and not exp_df.empty:
            exp_df["spend_date"] = pd.to_datetime(exp_df["spend_date"])
            exp_df = exp_df.sort_values("spend_date")
            exp_df["cumulative_spend"] = exp_df["daily_spend"].cumsum()
            exp_df["remaining"] = total_budget - exp_df["cumulative_spend"]

            # Anchor the first actual point at day-0 (full budget)
            anchor_date = start_date if start_date and start_date <= exp_df["spend_date"].iloc[0] else exp_df["spend_date"].iloc[0]
            anchor = pd.DataFrame({"date": [anchor_date], "remaining": [total_budget]})
            actual_df = pd.concat(
                [anchor, exp_df[["spend_date", "remaining"]].rename(columns={"spend_date": "date"})],
                ignore_index=True,
            )
        else:
            actual_df = pd.DataFrame(columns=["date", "remaining"])

        # ── 3. Forecast line (extend actual trend to end_date) ──────────────────
        forecast_df = pd.DataFrame(columns=["date", "remaining"])
        if not actual_df.empty and end_date and len(actual_df) >= 2:
            last_date = actual_df["date"].iloc[-1]
            last_remaining = actual_df["remaining"].iloc[-1]

            # Burn rate = total spent / days elapsed
            days_elapsed = max((last_date - actual_df["date"].iloc[0]).days, 1)
            total_spent = total_budget - last_remaining
            daily_burn = total_spent / days_elapsed

            if daily_burn > 0 and last_date < end_date:
                forecast_range = pd.date_range(start=last_date, end=end_date, freq="D")
                forecast_remaining = [
                    max(last_remaining - daily_burn * i, 0)
                    for i in range(len(forecast_range))
                ]
                forecast_df = pd.DataFrame({"date": forecast_range, "remaining": forecast_remaining})

        # ── 4. Status signal ────────────────────────────────────────────────────
        status = "No Data"
        if not actual_df.empty and not ideal_df.empty:
            # Find the ideal remaining at today's date
            ideal_today = ideal_df[ideal_df["date"] <= today]
            actual_today_val = actual_df["remaining"].iloc[-1]
            if not ideal_today.empty:
                ideal_today_val = ideal_today["remaining"].iloc[-1]
                diff_pct = (actual_today_val - ideal_today_val) / total_budget * 100
                if actual_today_val < 0:
                    status = "Over Budget"
                elif diff_pct < -10:   # actual spent more than ideal by >10% of budget
                    status = "At Risk"
                else:
                    status = "On Track"

        return {
            "ideal_df": ideal_df,
            "actual_df": actual_df,
            "forecast_df": forecast_df,
            "total_budget": total_budget,
            "start_date": start_date,
            "end_date": end_date,
            "today": today,
            "status": status,
        }

    except Exception as e:
        logger.error(f"Error building burndown data for project {project_id}: {e}")
        return None

def get_network_diagram_data(project_id):
    """
    Calculates the Critical Path and dependency metrics for the network diagram.
    Uses the Baseline Schedule dates to derive durations and dependencies.
    """
    try:
        activities_df = database.get_df('''
            SELECT bs.activity_id, bs.activity_name, bs.planned_start, bs.planned_finish, 
                   bs.depends_on, bs.status, u.full_name as responsible_name
            FROM baseline_schedule bs
            LEFT JOIN users u ON bs.responsible_user_id = u.user_id
            WHERE bs.project_id = %s
        ''', (project_id,))

        if activities_df.empty:
            return None

        # Prepare data structures
        activities = activities_df.to_dict('records')
        nodes = {a['activity_id']: a for a in activities}
        
        # Calculate durations
        for aid in nodes:
            start = pd.to_datetime(nodes[aid]['planned_start'])
            finish = pd.to_datetime(nodes[aid]['planned_finish'])
            nodes[aid]['duration'] = max((finish - start).days, 1)
            nodes[aid]['successors'] = []
            nodes[aid]['predecessors'] = [nodes[aid]['depends_on']] if nodes[aid]['depends_on'] else []

        # Map successors
        for aid in nodes:
            dep = nodes[aid]['depends_on']
            if dep in nodes:
                nodes[dep]['successors'].append(aid)

        # 1. Forward Pass (ES, EF)
        def forward_pass():
            visited = set()
            def visit(aid):
                if aid in visited: return
                nodes[aid]['es'] = 0
                for pred_id in nodes[aid]['predecessors']:
                    if pred_id in nodes:
                        visit(pred_id)
                        nodes[aid]['es'] = max(nodes[aid]['es'], nodes[pred_id]['ef'])
                nodes[aid]['ef'] = nodes[aid]['es'] + nodes[aid]['duration']
                visited.add(aid)

            for aid in nodes:
                visit(aid)

        forward_pass()

        # Project Finish Time
        project_finish = max(n['ef'] for n in nodes.values()) if nodes else 0

        # 2. Backward Pass (LS, LF)
        def backward_pass():
            visited = set()
            def visit(aid):
                if aid in visited: return
                nodes[aid]['lf'] = project_finish
                for succ_id in nodes[aid]['successors']:
                    visit(succ_id)
                    nodes[aid]['lf'] = min(nodes[aid]['lf'], nodes[succ_id]['ls'])
                nodes[aid]['ls'] = nodes[aid]['lf'] - nodes[aid]['duration']
                visited.add(aid)

            for aid in nodes:
                visit(aid)

        backward_pass()

        # 3. Calculate Float and Critical Path
        critical_path = []
        for aid in nodes:
            nodes[aid]['float'] = nodes[aid]['ls'] - nodes[aid]['es']
            nodes[aid]['is_critical'] = (nodes[aid]['float'] <= 0)
            if nodes[aid]['is_critical']:
                critical_path.append(aid)
            
            # Additional metric: "Most dependent on" (successor count)
            nodes[aid]['successor_count'] = len(nodes[aid]['successors'])

        return {
            "nodes": nodes,
            "project_finish": project_finish,
            "critical_path_ids": critical_path
        }
    except Exception as e:
        logger.error(f"Error calculating network diagram data: {e}")
        return None
