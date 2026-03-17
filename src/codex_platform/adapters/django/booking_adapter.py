"""
codex_platform.adapters.django.booking_adapter
=============================================
Universal Django adapter for the booking engine.

Does NOT contain imports from specific project features.
Works with any models implementing the booking interface.

Requires: pip install codex-tools[django]
"""

import zoneinfo
from datetime import date, datetime, timedelta
from typing import Any

from django.core.cache import cache
from django.utils import timezone

from codex_platform.booking.dto import (
    BookingEngineRequest,
    EngineResult,
    MasterAvailability,
    ServiceRequest,
)
from codex_platform.booking.modes import BookingMode
from codex_platform.calculator import SlotCalculator


class DjangoAvailabilityAdapter:
    """
    Universal bridge between Django ORM and the booking engine.

    All models are passed upon initialization, making the adapter
    suitable for use in any project.
    """

    def __init__(
        self,
        master_model: type[Any],
        appointment_model: type[Any],
        service_model: type[Any],
        day_off_model: type[Any],
        booking_settings_model: type[Any],
        site_settings_model: type[Any],
        step_minutes: int = 30,
        appointment_status_filter: list[str] | None = None,
    ) -> None:
        """
        Args:
            master_model: Master model class.
            appointment_model: Appointment model class.
            service_model: Service model class.
            day_off_model: Day Off model class.
            booking_settings_model: Booking Settings model class.
            site_settings_model: Global Site Settings model class.
            step_minutes: Time grid step size.
            appointment_status_filter: List of statuses considered "busy".
                                       If None, the default ones (PENDING, CONFIRMED) are used.
        """
        self.master_model = master_model
        self.appointment_model = appointment_model
        self.service_model = service_model
        self.day_off_model = day_off_model
        self.booking_settings_model = booking_settings_model
        self.site_settings_model = site_settings_model

        self.step_minutes = step_minutes
        self._calc = SlotCalculator(step_minutes)

        # If the filter is not passed, try to guess (for backward compatibility)
        # But it is better to pass it explicitly.
        if appointment_status_filter:
            self.appointment_status_filter = appointment_status_filter
        else:
            # Fallback to defaults if model has these constants
            self.appointment_status_filter = [
                getattr(appointment_model, "STATUS_PENDING", "pending"),
                getattr(appointment_model, "STATUS_CONFIRMED", "confirmed"),
            ]
            # Optionally add RESCHEDULE_PROPOSED if it exists
            if hasattr(appointment_model, "STATUS_RESCHEDULE_PROPOSED"):
                self.appointment_status_filter.append(appointment_model.STATUS_RESCHEDULE_PROPOSED)

        # Cache settings inside the instance
        self._booking_settings = None
        self._site_settings = None

    def build_engine_request(
        self,
        service_ids: list[int],
        target_date: date,
        mode: BookingMode = BookingMode.SINGLE_DAY,
        locked_master_id: int | None = None,
        master_selections: dict[str, str] | None = None,
    ) -> BookingEngineRequest:
        """Builds an engine request using the passed models."""
        services = self.service_model.objects.filter(id__in=service_ids).select_related("category")
        service_map = {s.id: s for s in services}

        weekday = target_date.weekday()
        service_requests = []

        for idx, svc_id in enumerate(service_ids):
            service = service_map.get(svc_id)
            if not service:
                continue

            if locked_master_id:
                possible_ids = [str(locked_master_id)]
            elif master_selections and str(idx) in master_selections:
                m_id = master_selections[str(idx)]
                if m_id == "any":
                    masters = self.master_model.objects.filter(
                        categories=service.category, status=self.master_model.STATUS_ACTIVE
                    )
                    possible_ids = [str(m.pk) for m in masters if weekday in (m.work_days or [])]
                else:
                    possible_ids = [str(m_id)]
            else:
                masters = self.master_model.objects.filter(
                    categories=service.category,
                    status=self.master_model.STATUS_ACTIVE,
                )
                possible_ids = [str(m.pk) for m in masters if weekday in (m.work_days or [])]

            if not possible_ids:
                continue

            gap = getattr(service, "min_gap_after_minutes", 0) or 0

            service_requests.append(
                ServiceRequest(
                    service_id=str(svc_id),
                    duration_minutes=service.duration,
                    min_gap_after_minutes=gap,
                    possible_master_ids=possible_ids,
                )
            )

        return BookingEngineRequest(
            service_requests=service_requests,
            booking_date=target_date,
            mode=mode,
        )

    def build_masters_availability(
        self,
        master_ids: list[int],
        target_date: date,
        cache_ttl: int = 0,
        exclude_appointment_ids: list[int] | None = None,
    ) -> dict[str, MasterAvailability]:
        """
        Calculates availability using the passed models.

        Args:
            master_ids: List of master IDs.
            target_date: Target date.
            cache_ttl: Cache TTL.
            exclude_appointment_ids: List of appointment IDs to ignore
                                     (used when rescheduling).
        """
        cache_key = None
        if cache_ttl > 0 and not exclude_appointment_ids:
            sorted_ids = ",".join(str(i) for i in sorted(master_ids))
            cache_key = f"booking_avail:{target_date}:{sorted_ids}"
            cached = cache.get(cache_key)
            if cached is not None:
                return cached

        settings = self._get_booking_settings()
        result: dict[str, MasterAvailability] = {}

        day_off_ids = set(
            self.day_off_model.objects.filter(master_id__in=master_ids, date=target_date).values_list(
                "master_id", flat=True
            )
        )

        # Filter appointments (using self.appointment_status_filter)
        appt_filter = {
            "master_id__in": master_ids,
            "datetime_start__date": target_date,
            "status__in": self.appointment_status_filter,
        }

        appointments_qs = self.appointment_model.objects.filter(**appt_filter)

        # Exclude appointments if needed (to accurately reschedule to the same time)
        if exclude_appointment_ids:
            appointments_qs = appointments_qs.exclude(id__in=exclude_appointment_ids)

        appointments = appointments_qs.order_by("datetime_start")

        busy_by_master: dict[int, list[tuple[datetime, datetime]]] = {mid: [] for mid in master_ids}
        for app in appointments:
            # Clear seconds and microseconds for clean calculations
            # Ensure we work with UTC or consistent timezone
            s = app.datetime_start.astimezone(timezone.utc).replace(second=0, microsecond=0)
            e = s + timedelta(minutes=app.duration_minutes)
            busy_by_master[app.master_id].append((s, e))

        masters = self.master_model.objects.filter(pk__in=master_ids)

        for master in masters:
            if master.pk in day_off_ids:
                continue

            # Get working hours in UTC, respecting master's timezone
            working_hours_utc = self.get_master_working_hours(master, target_date)
            if not working_hours_utc:
                continue

            work_start_dt, work_end_dt = working_hours_utc

            # Get break interval in UTC
            break_interval = self.get_break_interval(master, target_date)
            buffer = self.get_buffer_minutes(master, settings)

            free_windows = self._calc.merge_free_windows(
                work_start=work_start_dt,
                work_end=work_end_dt,
                busy_intervals=busy_by_master.get(master.pk, []),
                break_interval=break_interval,
                buffer_minutes=buffer,
                min_duration_minutes=self.step_minutes,  # Filter out useless garbage windows
            )

            result[str(master.pk)] = MasterAvailability(
                master_id=str(master.pk),
                free_windows=free_windows,
                buffer_between_minutes=buffer,
            )

        if cache_ttl > 0 and cache_key:
            cache.set(cache_key, result, timeout=cache_ttl)

        return result

    def build_availability_batch(
        self,
        master_ids: list[int],
        start_date: date,
        end_date: date,
    ) -> dict[date, dict[str, MasterAvailability]]:
        """
        Retrieves availability data for a date range in a single batch query.
        Returns: {date: {master_id: MasterAvailability}}
        """
        # 1. Batch query for appointments
        appointments = self.appointment_model.objects.filter(
            master_id__in=master_ids,
            datetime_start__date__range=(start_date, end_date),
            status__in=self.appointment_status_filter,
        ).order_by("datetime_start")

        # Group appointments by date and master in memory
        # Structure: {date: {master_id: [(start, end)]}}
        data_by_day: dict[date, dict[int, list[tuple[datetime, datetime]]]] = {}

        for app in appointments:
            # Use local date for grouping, but keep times in UTC
            # Note: app.datetime_start.date() depends on DB timezone or Django timezone.
            # Ideally we should use the master's timezone to determine "the day",
            # but for batching we assume the query date matches.
            day = app.datetime_start.astimezone(timezone.get_current_timezone()).date()

            # Fallback: if the appointment falls on previous/next day in local time vs UTC,
            # we might need to be careful. But for now, let's trust Django's date lookup.
            # Actually, app.datetime_start__date__range uses the DB's timezone logic.
            # Let's use the date from the object as Django sees it.
            day = app.datetime_start.date()

            if day < start_date or day > end_date:
                continue

            day_data = data_by_day.setdefault(day, {})
            master_slots = day_data.setdefault(app.master_id, [])

            s = app.datetime_start.astimezone(timezone.utc).replace(second=0, microsecond=0)
            e = s + timedelta(minutes=app.duration_minutes)
            master_slots.append((s, e))

        # 2. Batch query for days off
        days_off = self.day_off_model.objects.filter(
            master_id__in=master_ids,
            date__range=(start_date, end_date),
        ).values_list("master_id", "date")

        day_off_set = set(days_off)  # (master_id, date)

        # 3. Build result
        full_result: dict[date, dict[str, MasterAvailability]] = {}
        masters = list(self.master_model.objects.filter(pk__in=master_ids))
        settings = self._get_booking_settings()

        current_date = start_date
        while current_date <= end_date:
            day_availability = {}
            for master in masters:
                # Check day off
                if (master.pk, current_date) in day_off_set:
                    continue

                # Get working hours (UTC, timezone aware)
                working_hours = self.get_master_working_hours(master, current_date)
                if not working_hours:
                    continue

                work_start_dt, work_end_dt = working_hours
                buffer = self.get_buffer_minutes(master, settings)

                # Get busy slots for this day
                busy_slots = data_by_day.get(current_date, {}).get(master.pk, [])

                # Get break interval (UTC)
                break_interval = self.get_break_interval(master, current_date)

                free_windows = self._calc.merge_free_windows(
                    work_start=work_start_dt,
                    work_end=work_end_dt,
                    busy_intervals=busy_slots,
                    break_interval=break_interval,
                    buffer_minutes=buffer,
                    min_duration_minutes=self.step_minutes,
                )

                day_availability[str(master.pk)] = MasterAvailability(
                    master_id=str(master.pk),
                    free_windows=free_windows,
                    buffer_between_minutes=buffer,
                )

            full_result[current_date] = day_availability
            current_date += timedelta(days=1)

        return full_result

    def lock_masters(self, master_ids: list[int]) -> None:
        """
        Locks master rows in the DB for atomic availability check.
        Must be called within transaction.atomic().
        Uses list() to force the execution of the query.
        """
        if not master_ids:
            return
        # Sorting IDs is important to prevent deadlocks
        sorted_ids = sorted(master_ids)
        list(self.master_model.objects.select_for_update().filter(pk__in=sorted_ids))

    def result_to_slots_map(self, result: EngineResult) -> dict[str, bool]:
        times = result.get_unique_start_times()
        return {t: True for t in times}

    # ---------------------------------------------------------------------------
    # Field accessors — override in subclass to use different model field names
    # ---------------------------------------------------------------------------

    def get_work_start(self, master):
        """Return the master's individual work start time, or None to use global settings."""
        return getattr(master, "work_start", None)

    def get_work_end(self, master):
        """Return the master's individual work end time, or None to use global settings."""
        return getattr(master, "work_end", None)

    def get_break_start(self, master):
        """Return the master's break start time, or None if no break."""
        return getattr(master, "break_start", None)

    def get_break_end(self, master):
        """Return the master's break end time, or None if no break."""
        return getattr(master, "break_end", None)

    def get_master_timezone(self, master) -> str:
        """
        Return the IANA timezone string for the master.

        Falls back to ``site_settings.timezone``, then ``"UTC"``.
        Override to source the timezone from a different field or location.
        """
        tz = getattr(master, "timezone", None)
        if tz:
            return tz
        site = self._get_site_settings()
        return getattr(site, "timezone", None) or "UTC"

    def get_buffer_minutes(self, master, settings) -> int:
        """Return buffer between clients in minutes. Falls back to global settings."""
        individual = getattr(master, "buffer_between_minutes", None)
        if individual is not None:
            return individual
        return settings.default_buffer_between_minutes

    # ---------------------------------------------------------------------------
    # Derived availability helpers — override for custom scheduling logic
    # ---------------------------------------------------------------------------

    def get_master_working_hours(self, master, target_date: date) -> tuple[datetime, datetime] | None:
        """
        Determines the working hours of the master, respecting their timezone.
        Returns tuple (start, end) in UTC.
        """
        weekday = target_date.weekday()
        if master.work_days and weekday not in master.work_days:
            return None

        # 1. Get timezone
        tz_name = self.get_master_timezone(master)
        try:
            tz = zoneinfo.ZoneInfo(tz_name)
        except Exception:
            tz = zoneinfo.ZoneInfo("UTC")

        # 2. Get raw times
        start_t = self.get_work_start(master)
        end_t = self.get_work_end(master)

        if not (start_t and end_t):
            site = self._get_site_settings()
            if weekday < 5:
                start_t, end_t = site.work_start_weekdays, site.work_end_weekdays
            elif weekday == 5:
                start_t, end_t = site.work_start_saturday, site.work_end_saturday

        if not start_t or not end_t:
            return None

        # 3. Combine with timezone (DST aware) and convert to UTC
        work_start_dt = datetime.combine(target_date, start_t, tzinfo=tz)
        work_end_dt = datetime.combine(target_date, end_t, tzinfo=tz)

        return (work_start_dt.astimezone(timezone.utc), work_end_dt.astimezone(timezone.utc))

    def get_break_interval(self, master, target_date: date) -> tuple[datetime, datetime] | None:
        """Determines the master's break interval in UTC."""
        break_start = self.get_break_start(master)
        break_end = self.get_break_end(master)

        if break_start and break_end:
            tz_name = self.get_master_timezone(master)
            try:
                tz = zoneinfo.ZoneInfo(tz_name)
            except Exception:
                tz = zoneinfo.ZoneInfo("UTC")

            bs = datetime.combine(target_date, break_start, tzinfo=tz)
            be = datetime.combine(target_date, break_end, tzinfo=tz)

            return (bs.astimezone(timezone.utc), be.astimezone(timezone.utc))

        return None

    def _get_booking_settings(self):
        if self._booking_settings is None:
            self._booking_settings = self.booking_settings_model.load()
        return self._booking_settings

    def _get_site_settings(self):
        if self._site_settings is None:
            self._site_settings = self.site_settings_model.load()
        return self._site_settings
