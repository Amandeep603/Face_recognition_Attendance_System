import os
import glob
import pandas as pd
from datetime import datetime, timedelta
import config

class AnalyticsEngine:
    """
    Computes statistical metrics, trend aggregations, punctuality rankings,
    and storage health analytics across attendance logs and system modules.
    """

    def __init__(self, attendance_manager, unknown_manager=None, anti_spoofing=None):
        self.attendance_manager = attendance_manager
        self.unknown_manager = unknown_manager
        self.anti_spoofing = anti_spoofing

    def get_summary_metrics(self):
        """Returns high-level KPI cards metrics for today."""
        registered_students = self.attendance_manager.get_registered_students()
        total_students = len(registered_students)
        today_records = self.attendance_manager.get_today_records()
        present_today = len(today_records)
        absent_today = max(0, total_students - present_today)
        attendance_pct = round((present_today / total_students * 100.0), 1) if total_students > 0 else 0.0

        # Calculate 7-day average
        past_7_days = self._get_past_dates(7)
        past_7_counts = []
        for d in past_7_days:
            csv_path = self.attendance_manager._get_csv_path(d)
            if os.path.exists(csv_path):
                try:
                    df = pd.read_csv(csv_path)
                    past_7_counts.append(len(df))
                except Exception:
                    past_7_counts.append(0)
            else:
                past_7_counts.append(0)

        avg_attendance_7d = round(sum(past_7_counts) / len(past_7_counts), 1) if past_7_counts else 0.0

        unknown_today = self.unknown_manager.get_unknown_count_today() if self.unknown_manager else 0
        spoofs_blocked = self.anti_spoofing.spoof_attempts_count if self.anti_spoofing else 0

        # Punctuality & chronic absentees
        rankings = self.get_student_rankings()

        return {
            "total_students": total_students,
            "present_today": present_today,
            "absent_today": absent_today,
            "attendance_percentage": attendance_pct,
            "avg_attendance_7d": avg_attendance_7d,
            "unknown_faces_today": unknown_today,
            "spoofs_blocked": spoofs_blocked,
            "most_punctual": rankings.get("most_punctual", "N/A"),
            "frequently_absent_count": len(rankings.get("chronic_absentees", [])),
            "storage": self.get_storage_breakdown()
        }

    def get_trends_data(self, days=7):
        """Returns date-wise attendance counts for Chart.js line/bar charts."""
        dates = self._get_past_dates(days)
        labels = []
        counts = []
        percentages = []

        total_students = len(self.attendance_manager.get_registered_students())

        for d in dates:
            labels.append(datetime.strptime(d, "%Y-%m-%d").strftime("%b %d"))
            csv_path = self.attendance_manager._get_csv_path(d)
            cnt = 0
            if os.path.exists(csv_path):
                try:
                    df = pd.read_csv(csv_path)
                    cnt = len(df)
                except Exception:
                    cnt = 0
            counts.append(cnt)
            pct = round((cnt / total_students * 100.0), 1) if total_students > 0 else 0.0
            percentages.append(pct)

        return {
            "labels": labels,
            "dates": dates,
            "counts": counts,
            "percentages": percentages
        }

    def get_hourly_distribution(self):
        """Computes check-in distribution across hours of the day (e.g. 08:00 to 18:00)."""
        today_records = self.attendance_manager.get_today_records()
        hourly_map = {f"{h:02d}:00": 0 for h in range(7, 20)} # 7 AM to 7 PM

        for rec in today_records:
            t_str = rec.get("time", "")
            if t_str and ":" in t_str:
                hour = t_str.split(":")[0]
                hour_key = f"{int(hour):02d}:00"
                if hour_key in hourly_map:
                    hourly_map[hour_key] += 1

        return {
            "labels": list(hourly_map.keys()),
            "counts": list(hourly_map.values())
        }

    def get_student_rankings(self):
        """Calculates student-wise attendance percentages, punctuality, and chronic absentees."""
        registered_students = self.attendance_manager.get_registered_students()
        student_names = [s["name"] for s in registered_students]
        
        past_30_dates = self._get_past_dates(30)
        attendance_days = 0
        student_presence_map = {name: {"days": 0, "checkin_times": []} for name in student_names}

        for d in past_30_dates:
            csv_path = self.attendance_manager._get_csv_path(d)
            if os.path.exists(csv_path):
                attendance_days += 1
                try:
                    df = pd.read_csv(csv_path)
                    for _, row in df.iterrows():
                        name = str(row.get("Name", "")).strip()
                        if name in student_presence_map:
                            student_presence_map[name]["days"] += 1
                            t_str = str(row.get("Time", ""))
                            if t_str:
                                student_presence_map[name]["checkin_times"].append(t_str)
                except Exception:
                    pass

        if attendance_days == 0:
            attendance_days = 1

        student_summaries = []
        earliest_avg = None
        most_punctual = "N/A"
        chronic_absentees = []

        for name, data in student_presence_map.items():
            days_present = data["days"]
            pct = round((days_present / attendance_days) * 100.0, 1)
            
            # Calculate average check-in seconds if available
            avg_seconds = 0
            if data["checkin_times"]:
                seconds_list = []
                for t in data["checkin_times"]:
                    parts = t.split(":")
                    if len(parts) >= 2:
                        seconds_list.append(int(parts[0]) * 3600 + int(parts[1]) * 60)
                if seconds_list:
                    avg_seconds = sum(seconds_list) / len(seconds_list)
                    if earliest_avg is None or avg_seconds < earliest_avg:
                        earliest_avg = avg_seconds
                        most_punctual = name

            if pct < 75.0:
                chronic_absentees.append({
                    "name": name,
                    "attendance_pct": pct,
                    "days_present": days_present,
                    "total_days": attendance_days
                })

            student_summaries.append({
                "name": name,
                "days_present": days_present,
                "total_days": attendance_days,
                "attendance_percentage": pct,
                "status": "Regular" if pct >= 75.0 else "At Risk"
            })

        # Sort summaries by attendance percentage descending
        student_summaries.sort(key=lambda x: x["attendance_percentage"], reverse=True)

        return {
            "most_punctual": most_punctual,
            "chronic_absentees": chronic_absentees,
            "student_summaries": student_summaries
        }

    def get_storage_breakdown(self):
        """Calculates storage footprint across datasets in MB."""
        def get_dir_size_mb(path):
            if not os.path.exists(path):
                return 0.0
            total_bytes = sum(os.path.getsize(os.path.join(dirpath, f)) 
                              for dirpath, _, filenames in os.walk(path) 
                              for f in filenames)
            return round(total_bytes / (1024 * 1024), 2)

        return {
            "known_faces_mb": get_dir_size_mb(config.KNOWN_FACES_DIR),
            "attendance_logs_mb": get_dir_size_mb(config.ATTENDANCE_DIR),
            "unknown_faces_mb": get_dir_size_mb(config.UNKNOWN_FACES_DIR),
            "reports_mb": get_dir_size_mb(config.REPORTS_DIR),
            "total_mb": round(
                get_dir_size_mb(config.KNOWN_FACES_DIR) +
                get_dir_size_mb(config.ATTENDANCE_DIR) +
                get_dir_size_mb(config.UNKNOWN_FACES_DIR) +
                get_dir_size_mb(config.REPORTS_DIR), 2
            )
        }

    def _get_past_dates(self, count):
        """Returns list of last N date strings in YYYY-MM-DD format ending with today."""
        today = datetime.now()
        dates = [(today - timedelta(days=i)).strftime("%Y-%m-%d") for i in range(count - 1, -1, -1)]
        return dates
