"""Worker tao cau hoi on tap theo cac mon hoc user dang hoc trong ky.

File nay chi tap trung vao phan worker, khong can thay doi cac module khac.

Muc tieu:
1) Doc lich hoc + tien do on tap cua sinh vien trong ky.
2) Lay khung bai giang theo tuan cho tung mon.
3) Tao cau hoi trac nghiem bam sat noi dung da hoc den tuan hien tai.
4) Phan bo deu giua cac mon trong tuan (khong uu tien mon nao).
5) Luu lich su thong bao da gui de tranh lap lai.
6) Ho tro frequency va quiet-hours de tranh lam phien nguoi dung.

Luu y:
- Worker duoc thiet ke de chay duoc doc lap (script mode) de review nhanh.
- Kien truc chia nho theo repository + service de de thay the/noi rong sau nay.
"""

from __future__ import annotations

import hashlib
import json
import logging
import random
import sqlite3
from dataclasses import asdict, dataclass
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Cac model du lieu noi bo
# ---------------------------------------------------------------------------
@dataclass
class WorkerConfig:
	"""Cau hinh chay worker.

	Attributes:
		max_notifications_per_run:
			So luong thong bao toi da cho 1 lan chay worker.
		default_questions_per_course:
			So cau hoi mac dinh cho moi mon khi da duoc chon trong vong phan bo deu.
		random_seed:
			Seed de giu output on dinh khi review.
		default_frequency_per_day:
			Neu user chua cai dat preference, day la tan suat mac dinh.
		default_quiet_start:
			Gio bat dau khung gio im lang (HH:MM).
		default_quiet_end:
			Gio ket thuc khung gio im lang (HH:MM).
	"""

	max_notifications_per_run: int = 12
	default_questions_per_course: int = 1
	random_seed: int = 42
	default_frequency_per_day: int = 2
	default_quiet_start: str = "22:00"
	default_quiet_end: str = "07:00"


@dataclass
class NotificationPreference:
	"""Preference thong bao theo sinh vien."""

	enabled: bool
	frequency_per_day: int
	quiet_hours_start: str
	quiet_hours_end: str
	timezone_offset_minutes: int


@dataclass
class ReviewQuestion:
	"""Noi dung cau hoi trac nghiem gui qua notification."""

	question_text: str
	options: list[str]
	correct_option_index: int
	explanation: str
	source_note: str


@dataclass
class NotificationRecord:
	"""Ban ghi luu vao bang review_notifications_history."""

	student_id: str
	semester_id: str
	course_id: str
	week_no: int
	topic_key: str
	question_payload_json: str
	sent_at: str
	delivery_status: str = "queued"


# ---------------------------------------------------------------------------
# SQL schema phuc vu rieng cho worker
# ---------------------------------------------------------------------------
WORKER_SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS course_lecture_frames (
	frame_id INTEGER PRIMARY KEY AUTOINCREMENT,
	curriculum_id VARCHAR(20) NOT NULL,
	course_id VARCHAR(20) NOT NULL,
	week_no INT NOT NULL,
	lecture_title NVARCHAR(255) NOT NULL,
	topic_outline TEXT,
	expected_progress_pct DECIMAL(5,2),
	created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
	updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
	UNIQUE (curriculum_id, course_id, week_no),
	FOREIGN KEY (curriculum_id) REFERENCES Curriculums(curriculum_id),
	FOREIGN KEY (course_id) REFERENCES Courses(course_id)
);

CREATE TABLE IF NOT EXISTS student_semester_study_schedule (
	schedule_id INTEGER PRIMARY KEY AUTOINCREMENT,
	student_id VARCHAR(20) NOT NULL,
	semester_id VARCHAR(10) NOT NULL,
	course_id VARCHAR(20) NOT NULL,
	week_no INT NOT NULL,
	planned_study_minutes INT DEFAULT 0,
	actual_study_minutes INT DEFAULT 0,
	review_progress_pct DECIMAL(5,2) DEFAULT 0,
	last_reviewed_at TIMESTAMP,
	created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
	updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
	UNIQUE (student_id, semester_id, course_id, week_no),
	FOREIGN KEY (student_id) REFERENCES Students(student_id),
	FOREIGN KEY (semester_id) REFERENCES Semesters(semester_id),
	FOREIGN KEY (course_id) REFERENCES Courses(course_id)
);

CREATE TABLE IF NOT EXISTS review_notifications_history (
	notification_id INTEGER PRIMARY KEY AUTOINCREMENT,
	student_id VARCHAR(20) NOT NULL,
	semester_id VARCHAR(10) NOT NULL,
	course_id VARCHAR(20) NOT NULL,
	week_no INT NOT NULL,
	topic_key VARCHAR(128) NOT NULL,
	question_payload_json TEXT NOT NULL,
	sent_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
	delivery_status VARCHAR(20) DEFAULT 'queued',
	answered_option INT,
	answered_at TIMESTAMP,
	created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
	FOREIGN KEY (student_id) REFERENCES Students(student_id),
	FOREIGN KEY (semester_id) REFERENCES Semesters(semester_id),
	FOREIGN KEY (course_id) REFERENCES Courses(course_id)
);

-- Bang preference phuc vu frequency + quiet-hours.
CREATE TABLE IF NOT EXISTS student_notification_preferences (
	student_id VARCHAR(20) PRIMARY KEY,
	enabled BOOLEAN DEFAULT TRUE,
	frequency_per_day INT DEFAULT 2,
	quiet_hours_start VARCHAR(5) DEFAULT '22:00',
	quiet_hours_end VARCHAR(5) DEFAULT '07:00',
	timezone_offset_minutes INT DEFAULT 0,
	updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
	FOREIGN KEY (student_id) REFERENCES Students(student_id)
);

CREATE INDEX IF NOT EXISTS idx_review_notifications_student_sent_at
ON review_notifications_history (student_id, sent_at);

CREATE INDEX IF NOT EXISTS idx_review_notifications_student_semester_week
ON review_notifications_history (student_id, semester_id, week_no);

CREATE INDEX IF NOT EXISTS idx_study_schedule_student_semester_week
ON student_semester_study_schedule (student_id, semester_id, week_no);
"""


# ---------------------------------------------------------------------------
# Database access layer
# ---------------------------------------------------------------------------
class WorkerRepository:
	"""Repository chua toan bo SQL ma worker can dung.

	Tach rieng lop nay giup:
	- Unit test de hon (mock repository)
	- Tranh tron logic SQL vao business flow
	"""

	def __init__(self, db_path: str | Path):
		self.db_path = str(db_path)

	def _connect(self) -> sqlite3.Connection:
		conn = sqlite3.connect(self.db_path)
		conn.row_factory = sqlite3.Row
		conn.execute("PRAGMA foreign_keys = ON")
		return conn

	def ensure_schema(self) -> None:
		"""Tao cac bang worker neu chua co."""
		with self._connect() as conn:
			conn.executescript(WORKER_SCHEMA_SQL)
			conn.commit()

	def get_student_curriculum(self, student_id: str) -> str | None:
		query = "SELECT curriculum_id FROM Students WHERE student_id = ?"
		with self._connect() as conn:
			row = conn.execute(query, (student_id,)).fetchone()
		return str(row["curriculum_id"]) if row else None

	def get_notification_preference(self, student_id: str) -> dict[str, Any] | None:
		"""Lay preference thong bao cua sinh vien."""
		query = """
			SELECT enabled,
			       frequency_per_day,
			       quiet_hours_start,
			       quiet_hours_end,
			       timezone_offset_minutes
			FROM student_notification_preferences
			WHERE student_id = ?
		"""
		with self._connect() as conn:
			row = conn.execute(query, (student_id,)).fetchone()
		return dict(row) if row else None

	def upsert_notification_preference(self, student_id: str, pref: NotificationPreference) -> None:
		"""Luu/cap nhat preference cho student."""
		query = """
			INSERT INTO student_notification_preferences (
				student_id,
				enabled,
				frequency_per_day,
				quiet_hours_start,
				quiet_hours_end,
				timezone_offset_minutes,
				updated_at
			) VALUES (?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
			ON CONFLICT(student_id) DO UPDATE SET
				enabled = excluded.enabled,
				frequency_per_day = excluded.frequency_per_day,
				quiet_hours_start = excluded.quiet_hours_start,
				quiet_hours_end = excluded.quiet_hours_end,
				timezone_offset_minutes = excluded.timezone_offset_minutes,
				updated_at = CURRENT_TIMESTAMP
		"""
		with self._connect() as conn:
			conn.execute(
				query,
				(
					student_id,
					1 if pref.enabled else 0,
					pref.frequency_per_day,
					pref.quiet_hours_start,
					pref.quiet_hours_end,
					pref.timezone_offset_minutes,
				),
			)
			conn.commit()

	def count_notifications_in_window(self, student_id: str, window_start_utc: str, window_end_utc: str) -> int:
		"""Dem so notification da gui trong 1 cua so thoi gian UTC."""
		query = """
			SELECT COUNT(*) AS total
			FROM review_notifications_history
			WHERE student_id = ?
			  AND sent_at >= ?
			  AND sent_at < ?
		"""
		with self._connect() as conn:
			row = conn.execute(query, (student_id, window_start_utc, window_end_utc)).fetchone()
		return int(row["total"]) if row else 0

	def get_study_schedule_rows(self, student_id: str, semester_id: str, week_no: int) -> list[dict[str, Any]]:
		"""Lay danh sach mon co lich hoc cua student trong tuan."""
		query = """
			SELECT sss.course_id,
			       c.course_name,
			       sss.week_no,
			       COALESCE(sss.review_progress_pct, 0) AS review_progress_pct,
			       COALESCE(sss.planned_study_minutes, 0) AS planned_study_minutes,
			       COALESCE(sss.actual_study_minutes, 0) AS actual_study_minutes
			FROM student_semester_study_schedule sss
			JOIN Courses c ON c.course_id = sss.course_id
			WHERE sss.student_id = ?
			  AND sss.semester_id = ?
			  AND sss.week_no = ?
			ORDER BY sss.course_id
		"""
		with self._connect() as conn:
			rows = conn.execute(query, (student_id, semester_id, week_no)).fetchall()
		return [dict(r) for r in rows]

	def get_lecture_frame(self, curriculum_id: str, course_id: str, week_no: int) -> dict[str, Any] | None:
		"""Lay khung bai giang cua mon hoc theo tuan hien tai."""
		query = """
			SELECT course_id, week_no, lecture_title, topic_outline,
			       COALESCE(expected_progress_pct, 0) AS expected_progress_pct
			FROM course_lecture_frames
			WHERE curriculum_id = ? AND course_id = ? AND week_no = ?
		"""
		with self._connect() as conn:
			row = conn.execute(query, (curriculum_id, course_id, week_no)).fetchone()
		return dict(row) if row else None

	def has_notification_for_topic(
		self,
		student_id: str,
		semester_id: str,
		course_id: str,
		week_no: int,
		topic_key: str,
	) -> bool:
		"""Kiem tra da gui notification cho topic nay trong tuan chua."""
		query = """
			SELECT 1
			FROM review_notifications_history
			WHERE student_id = ?
			  AND semester_id = ?
			  AND course_id = ?
			  AND week_no = ?
			  AND topic_key = ?
			LIMIT 1
		"""
		with self._connect() as conn:
			row = conn.execute(
				query,
				(student_id, semester_id, course_id, week_no, topic_key),
			).fetchone()
		return row is not None

	def insert_notification(self, record: NotificationRecord) -> int:
		"""Luu 1 notification vao lich su va tra ve notification_id."""
		query = """
			INSERT INTO review_notifications_history (
				student_id,
				semester_id,
				course_id,
				week_no,
				topic_key,
				question_payload_json,
				sent_at,
				delivery_status
			) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
		"""
		with self._connect() as conn:
			cur = conn.execute(
				query,
				(
					record.student_id,
					record.semester_id,
					record.course_id,
					record.week_no,
					record.topic_key,
					record.question_payload_json,
					record.sent_at,
					record.delivery_status,
				),
			)
			conn.commit()
			return int(cur.lastrowid)


# ---------------------------------------------------------------------------
# Worker core logic
# ---------------------------------------------------------------------------
class ReviewWorker:
	"""Worker tao cau hoi on tap va ghi lich su notification.

	Nguyen tac business quan trong:
	- Khong uu tien mon nao; phan bo deu cac mon trong tuan.
	- Bam sat khung bai giang (course_lecture_frames) theo week_no.
	- Khong tao trung notification cho cung topic trong cung tuan.
	- Ton trong frequency + quiet-hours cua user.
	"""

	def __init__(self, repository: WorkerRepository, config: WorkerConfig | None = None):
		self.repository = repository
		self.config = config or WorkerConfig()
		self.random = random.Random(self.config.random_seed)

	def set_notification_preference(self, student_id: str, preference: NotificationPreference) -> None:
		"""Public helper de cap nhat preference cho student."""
		self.repository.ensure_schema()
		self.repository.upsert_notification_preference(student_id, preference)

	def run_weekly_review(
		self,
		student_id: str,
		semester_id: str,
		week_no: int,
		now_utc: datetime | None = None,
	) -> dict[str, Any]:
		"""Chay worker cho 1 student trong 1 tuan.

		Returns:
			Bao cao tong hop de review nhanh ket qua chay.
		"""
		self.repository.ensure_schema()
		now = now_utc or datetime.utcnow()

		curriculum_id = self.repository.get_student_curriculum(student_id)
		if not curriculum_id:
			return {
				"student_id": student_id,
				"semester_id": semester_id,
				"week_no": week_no,
				"sent": 0,
				"status": "student_not_found",
			}

		pref = self._resolve_preference(student_id)
		if not pref.enabled:
			return {
				"student_id": student_id,
				"semester_id": semester_id,
				"week_no": week_no,
				"sent": 0,
				"status": "notifications_disabled",
				"preference": asdict(pref),
			}

		local_now = now + timedelta(minutes=pref.timezone_offset_minutes)
		if self._is_within_quiet_hours(local_now, pref.quiet_hours_start, pref.quiet_hours_end):
			return {
				"student_id": student_id,
				"semester_id": semester_id,
				"week_no": week_no,
				"sent": 0,
				"status": "quiet_hours_active",
				"local_now": local_now.isoformat(timespec="seconds"),
				"preference": asdict(pref),
			}

		window_start_utc, window_end_utc = self._daily_window_utc(local_now, pref.timezone_offset_minutes)
		sent_today = self.repository.count_notifications_in_window(
			student_id=student_id,
			window_start_utc=window_start_utc,
			window_end_utc=window_end_utc,
		)
		remaining_daily_budget = max(0, pref.frequency_per_day - sent_today)
		if remaining_daily_budget <= 0:
			return {
				"student_id": student_id,
				"semester_id": semester_id,
				"week_no": week_no,
				"sent": 0,
				"status": "frequency_limit_reached",
				"sent_today": sent_today,
				"frequency_per_day": pref.frequency_per_day,
				"preference": asdict(pref),
			}

		schedule_rows = self.repository.get_study_schedule_rows(student_id, semester_id, week_no)
		if not schedule_rows:
			return {
				"student_id": student_id,
				"semester_id": semester_id,
				"week_no": week_no,
				"sent": 0,
				"status": "no_schedule_for_week",
				"preference": asdict(pref),
			}

		# Phan bo deu: duyet theo thu tu on dinh (course_id asc),
		# moi mon 1 cau truoc, sau do moi den vong tiep theo neu con ngan sach.
		planned_courses = [dict(r) for r in schedule_rows]
		sent_records: list[dict[str, Any]] = []
		max_n = min(max(1, self.config.max_notifications_per_run), remaining_daily_budget)
		q_per_course = max(1, self.config.default_questions_per_course)

		round_index = 0
		while len(sent_records) < max_n:
			made_progress_in_round = False
			for course in planned_courses:
				if len(sent_records) >= max_n:
					break
				# Trong vong thu N, moi mon duoc phep sinh toi da q_per_course cau.
				if round_index >= q_per_course:
					continue

				one = self._build_and_store_one_notification(
					student_id=student_id,
					semester_id=semester_id,
					week_no=week_no,
					curriculum_id=curriculum_id,
					course=course,
					now=now,
				)
				if one:
					sent_records.append(one)
					made_progress_in_round = True

			if not made_progress_in_round:
				# Khong sinh them duoc nua (vi trung topic hoac thieu frame)
				break
			round_index += 1

		coverage_courses = sorted({r["course_id"] for r in sent_records})
		return {
			"student_id": student_id,
			"semester_id": semester_id,
			"week_no": week_no,
			"status": "ok",
			"scheduled_courses": len(planned_courses),
			"covered_courses": len(coverage_courses),
			"covered_course_ids": coverage_courses,
			"sent": len(sent_records),
			"notifications": sent_records,
			"sent_today": sent_today + len(sent_records),
			"frequency_per_day": pref.frequency_per_day,
			"preference": asdict(pref),
		}

	def _resolve_preference(self, student_id: str) -> NotificationPreference:
		"""Lay preference DB neu co, neu khong co thi dung default config."""
		raw = self.repository.get_notification_preference(student_id)
		if not raw:
			return NotificationPreference(
				enabled=True,
				frequency_per_day=self.config.default_frequency_per_day,
				quiet_hours_start=self.config.default_quiet_start,
				quiet_hours_end=self.config.default_quiet_end,
				timezone_offset_minutes=0,
			)

		return NotificationPreference(
			enabled=bool(raw.get("enabled", 1)),
			frequency_per_day=max(0, int(raw.get("frequency_per_day", self.config.default_frequency_per_day) or 0)),
			quiet_hours_start=str(raw.get("quiet_hours_start") or self.config.default_quiet_start),
			quiet_hours_end=str(raw.get("quiet_hours_end") or self.config.default_quiet_end),
			timezone_offset_minutes=int(raw.get("timezone_offset_minutes", 0) or 0),
		)

	def _daily_window_utc(self, local_now: datetime, tz_offset_minutes: int) -> tuple[str, str]:
		"""Tinh cua so 1 ngay local, sau do quy doi ve UTC de query DB."""
		local_start = local_now.replace(hour=0, minute=0, second=0, microsecond=0)
		local_end = local_start + timedelta(days=1)
		utc_start = local_start - timedelta(minutes=tz_offset_minutes)
		utc_end = local_end - timedelta(minutes=tz_offset_minutes)
		return (
			utc_start.isoformat(timespec="seconds"),
			utc_end.isoformat(timespec="seconds"),
		)

	def _is_within_quiet_hours(self, local_now: datetime, quiet_start: str, quiet_end: str) -> bool:
		"""Kiem tra local_now co nam trong quiet-hours hay khong.

		Ho tro ca 2 truong hop:
		- Khoang trong ngay, VD 12:00 -> 14:00.
		- Khoang qua dem, VD 22:00 -> 07:00.
		"""
		start_minutes = self._parse_hhmm_to_minutes(quiet_start)
		end_minutes = self._parse_hhmm_to_minutes(quiet_end)
		now_minutes = local_now.hour * 60 + local_now.minute

		if start_minutes == end_minutes:
			# Cung gio bat dau/ket thuc => khong chan thong bao.
			return False
		if start_minutes < end_minutes:
			return start_minutes <= now_minutes < end_minutes
		# Khoang qua dem
		return now_minutes >= start_minutes or now_minutes < end_minutes

	def _parse_hhmm_to_minutes(self, hhmm: str) -> int:
		"""Parse HH:MM, fallback an toan neu format loi."""
		try:
			hour_str, minute_str = hhmm.strip().split(":", 1)
			hour = max(0, min(23, int(hour_str)))
			minute = max(0, min(59, int(minute_str)))
			return hour * 60 + minute
		except Exception:
			# Fallback 00:00 neu du lieu xau.
			return 0

	def _build_and_store_one_notification(
		self,
		student_id: str,
		semester_id: str,
		week_no: int,
		curriculum_id: str,
		course: dict[str, Any],
		now: datetime,
	) -> dict[str, Any] | None:
		"""Sinh va luu 1 notification cho 1 mon trong tuan."""
		course_id = str(course["course_id"])
		course_name = str(course.get("course_name", course_id))

		frame = self.repository.get_lecture_frame(curriculum_id, course_id, week_no)
		if not frame:
			# Neu chua co frame cho tuan nay, bo qua mon (khong doan noi dung).
			logger.info("Skip %s: no lecture frame for week %s", course_id, week_no)
			return None

		topic_key = self._build_topic_key(
			curriculum_id=curriculum_id,
			course_id=course_id,
			week_no=week_no,
			lecture_title=str(frame.get("lecture_title", "")),
			topic_outline=str(frame.get("topic_outline", "")),
		)

		if self.repository.has_notification_for_topic(
			student_id=student_id,
			semester_id=semester_id,
			course_id=course_id,
			week_no=week_no,
			topic_key=topic_key,
		):
			# Da gui roi thi khong gui lap lai trong cung tuan.
			return None

		question = self._generate_review_question(
			course_name=course_name,
			lecture_title=str(frame.get("lecture_title", "")),
			topic_outline=str(frame.get("topic_outline", "")),
			expected_progress_pct=float(frame.get("expected_progress_pct", 0) or 0),
			review_progress_pct=float(course.get("review_progress_pct", 0) or 0),
		)

		payload = {
			"course_id": course_id,
			"course_name": course_name,
			"week_no": week_no,
			"lecture_title": frame.get("lecture_title"),
			"topic_outline": frame.get("topic_outline"),
			"question": asdict(question),
		}

		record = NotificationRecord(
			student_id=student_id,
			semester_id=semester_id,
			course_id=course_id,
			week_no=week_no,
			topic_key=topic_key,
			question_payload_json=json.dumps(payload, ensure_ascii=False),
			sent_at=now.isoformat(timespec="seconds"),
			delivery_status="queued",
		)
		notification_id = self.repository.insert_notification(record)

		return {
			"notification_id": notification_id,
			"course_id": course_id,
			"course_name": course_name,
			"week_no": week_no,
			"topic_key": topic_key,
		}

	def _build_topic_key(
		self,
		curriculum_id: str,
		course_id: str,
		week_no: int,
		lecture_title: str,
		topic_outline: str,
	) -> str:
		"""Tao key de chan gui trung topic trong tuan.

		Dung hash ngan gon de:
		- Co dinh (deterministic)
		- De index
		- Khong phu thuoc do dai title/outline
		"""
		raw = "|".join(
			[
				curriculum_id.strip().lower(),
				course_id.strip().lower(),
				str(week_no),
				lecture_title.strip().lower(),
				topic_outline.strip().lower(),
			]
		)
		return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:32]

	def _generate_review_question(
		self,
		course_name: str,
		lecture_title: str,
		topic_outline: str,
		expected_progress_pct: float,
		review_progress_pct: float,
	) -> ReviewQuestion:
		"""Sinh 1 cau hoi trac nghiem don gian bam sat frame bai giang.

		Hien tai dung template de co output on dinh, de review va test nhanh.
		Sau nay co the thay bang LLM/knowledge search ma khong doi contract output.
		"""
		clean_title = lecture_title.strip() or f"Noi dung {course_name}"
		clean_outline = topic_outline.strip() or clean_title

		# Chon focus text theo muc do tre tien do on tap cua user.
		gap = max(0.0, expected_progress_pct - review_progress_pct)
		focus_note = (
			"Noi dung can on lai vi tien do on tap dang thap hon khung bai giang."
			if gap >= 15
			else "Noi dung on tap dinh ky de giu nhip hoc deu dan."
		)

		question_text = (
			f"Trong mon {course_name}, voi bai '{clean_title}', "
			"phat bieu nao dung nhat ve muc tieu on tap tuan nay?"
		)

		options = [
			f"Tap trung tong hop y chinh cua: {clean_outline[:90]}",
			"Bo qua noi dung da hoc, chi hoc chuong moi hoan toan.",
			"Chi hoc thuoc dap an mau ma khong can hieu khai niem.",
			"Dung on tap tuan nay de chuyen sang mon khac.",
		]

		return ReviewQuestion(
			question_text=question_text,
			options=options,
			correct_option_index=0,
			explanation=(
				"Phuong an 1 phu hop vi bam sat noi dung da hoc trong tuan "
				"va giup cung co kien thuc theo tien do. "
				f"{focus_note}"
			),
			source_note=f"frame:{clean_title}",
		)


def run_worker_once(
	db_path: str | Path,
	student_id: str,
	semester_id: str,
	week_no: int,
	config: WorkerConfig | None = None,
	now_utc: datetime | None = None,
) -> dict[str, Any]:
	"""Entry point tien dung cho script/test.

	Ham nay giup team goi nhanh worker ma khong can khoi tao object thu cong.
	"""
	repo = WorkerRepository(db_path=db_path)
	worker = ReviewWorker(repository=repo, config=config)
	return worker.run_weekly_review(
		student_id=student_id,
		semester_id=semester_id,
		week_no=week_no,
		now_utc=now_utc,
	)


if __name__ == "__main__":
	logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

	# Vi du chay tay de smoke-test:
	# python -m src.agent.worker
	# Ban co the doi gia tri duoi day cho dung du lieu demo.
	DB_PATH = Path("data") / "academic.db"
	result = run_worker_once(
		db_path=DB_PATH,
		student_id="S001",
		semester_id="20241",
		week_no=1,
	)
	print(json.dumps(result, ensure_ascii=False, indent=2))
