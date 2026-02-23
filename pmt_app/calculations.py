import database
import pandas as pd
import logging
from datetime import datetime, timedelta

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def get_project_metrics(project_id):
    """
    Calculates all metrics for a single project.
    Ensures safe data access with explicit checks for empty results.
    """
    try:
        project_df = database.get_df(
            "SELECT * FROM projects WHERE project_id = ?", (project_id,)
        )
        if project_df is None or project_df.empty:
            logger.warning(f"Project with ID {project_id} not found.")
            return None

        project = project_df.iloc[0]

        baseline = database.get_df(
            "SELECT * FROM baseline_schedule WHERE project_id = ?", (project_id,)
        )
        expenditures = database.get_df(
            "SELECT * FROM expenditure_log WHERE project_id = ?", (project_id,)
        )

        logs = database.get_df(
            """
            SELECT al.*, bs.activity_name, bs.budgeted_cost 
            FROM activity_log al 
            JOIN baseline_schedule bs ON al.activity_id = bs.activity_id 
            WHERE bs.project_id = ?
        """,
            (project_id,),
        )

        total_budget = (
            float(project["total_budget"]) if pd.notna(project["total_budget"]) else 0.0
        )
        total_spent = 0.0
        if expenditures is not None and not expenditures.empty:
            total_spent = float(expenditures["amount"].sum())

        remaining = total_budget - total_spent

        pct_complete = 0.0
        earned_value = 0.0
        total_planned = baseline["budgeted_cost"].sum() if not baseline.empty else 0.0

        if not baseline.empty:
            if total_planned > 0:
                completed_budget = baseline[baseline["status"] == "Complete"]["budgeted_cost"].sum()
                pct_complete = (completed_budget / total_planned) * 100
                earned_value = completed_budget
            else:
                # Fallback for zero-budget projects: use activity counts
                total_count = len(baseline)
                completed_count = len(baseline[baseline["status"] == "Complete"])
                pct_complete = (completed_count / total_count * 100) if total_count > 0 else 0.0
                earned_value = 0.0 # No monetary earned value

        forecast = total_spent + (total_budget - earned_value)

        cpi = (earned_value / total_spent) if total_spent > 0 else 1.0

        budget_health = "Green"
        if forecast > total_budget * 1.05 and total_budget > 0:
            budget_health = "Red"
        elif forecast > total_budget and total_budget > 0:
            budget_health = "Yellow"
        elif cpi < 0.85 and total_spent > 0:
            budget_health = "Red"
        elif cpi < 0.95 and total_spent > 0:
            budget_health = "Yellow"

        schedule_health = "Green"
        if not baseline.empty:
            baseline["planned_finish"] = pd.to_datetime(baseline["planned_finish"])
            today = pd.Timestamp.now()
            overdue = baseline[
                (baseline["planned_finish"] < today)
                & (baseline["status"] != "Complete")
            ]
            if not overdue.empty:
                schedule_health = "Red"

        budget_used_pct = (
            (total_spent / total_budget * 100) if total_budget > 0 else 0.0
        )

        # NEW METRICS
        # 1. Burn Rate (spending per day)
        burn_rate = 0.0
        days_elapsed = 0
        if expenditures is not None and not expenditures.empty:
            expenditures["spend_date"] = pd.to_datetime(expenditures["spend_date"])
            if not expenditures.empty:
                first_spend = expenditures["spend_date"].min()
                last_spend = expenditures["spend_date"].max()
                days_elapsed = max((last_spend - first_spend).days, 1)
                burn_rate = total_spent / days_elapsed if days_elapsed > 0 else 0.0

        # 2. Days Remaining
        days_remaining = 0
        project_end_date = None
        if pd.notna(project["target_end_date"]):
            project_end_date = pd.to_datetime(project["target_end_date"])
            days_remaining = max((project_end_date - pd.Timestamp.now()).days, 0)

        # 3. Cost Variance (CV = EV - AC)
        cost_variance = earned_value - total_spent

        # 4. Schedule Variance (SV = EV - PV) - simplified
        planned_value = 0.0
        if not baseline.empty:
            baseline["planned_finish"] = pd.to_datetime(baseline["planned_finish"])
            today = pd.Timestamp.now()
            # PV = sum of budgeted costs for activities that should be complete by now
            planned_value = baseline[baseline["planned_finish"] <= today][
                "budgeted_cost"
            ].sum()
        schedule_variance = earned_value - planned_value

        # 5. SPI (Schedule Performance Index)
        spi = (earned_value / planned_value) if planned_value > 0 else 1.0

        # 6. Variance at Completion (VAC = BAC - EAC)
        variance_at_completion = total_budget - forecast

        # 7. Estimate to Complete (ETC)
        etc = forecast - total_spent if forecast > total_spent else 0

        # 8. Activity counts
        total_activities = len(baseline) if not baseline.empty else 0
        completed_activities = (
            len(baseline[baseline["status"] == "Complete"]) if not baseline.empty else 0
        )
        active_activities = (
            len(baseline[baseline["status"] == "Active"]) if not baseline.empty else 0
        )

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
            # New metrics
            "burn_rate": burn_rate,
            "days_remaining": days_remaining,
            "cost_variance": cost_variance,
            "schedule_variance": schedule_variance,
            "cpi": cpi,
            "spi": spi,
            "variance_at_completion": variance_at_completion,
            "estimate_to_complete": etc,
            "total_activities": total_activities,
            "completed_activities": completed_activities,
            "active_activities": active_activities,
            "project_start_date": str(project["start_date"])
            if pd.notna(project["start_date"])
            else None,
            "project_end_date": str(project["target_end_date"])
            if pd.notna(project["target_end_date"])
            else None,
        }
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
            SELECT strftime('%Y-%m', spend_date) as month, 
                   SUM(amount) as total_spent
            FROM expenditure_log 
            WHERE project_id = ?
            GROUP BY strftime('%Y-%m', spend_date)
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
            WHERE project_id = ?
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
            "SELECT total_budget, start_date, target_end_date FROM projects WHERE project_id = ?",
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
            WHERE project_id = ?
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
